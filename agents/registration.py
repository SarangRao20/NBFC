"""Registration Agent — OTP-based Login + CRM Lookup for returning users."""

import os
import sys
import json
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from mock_apis.otp_service import send_otp, verify_otp
from config import get_extraction_llm
from agents.session_manager import SessionManager


# ─── Pydantic Schema (Keep for documentation, but we'll parse manually) ─────────
class RegistrationData(BaseModel):
    phone: str | None = None
    user_otp: str | None = None
    name: str | None = None


# ─── State ───────────────────────────────────────────────────────────────────────
class RegistrationState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    phone: str | None
    otp_sent: bool
    otp_verified: bool
    customer_profile: dict | None


def normalize_phone(phone: str) -> str:
    """Normalize phone to 10-digit format, handle various formats."""
    phone = str(phone).strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]
    # Extract only digits, take last 10
    digits_only = "".join(filter(str.isdigit, phone))[-10:]
    return digits_only if len(digits_only) == 10 else None


def is_valid_email(email: str) -> bool:
    """Validate email format strictly."""
    if not email or "@" not in email:
        return False
    parts = email.split("@")
    if len(parts) != 2:
        return False
    local, domain = parts
    # Domain must have at least one dot
    if "." not in domain or domain.count(".") > 2:
        return False
    # Domain parts must be non-empty
    domain_parts = domain.split(".")
    return all(part for part in domain_parts) and len(domain_parts[-1]) >= 2


def extract_salary(text: str) -> int | None:
    """Extract salary handling commas, k suffix, and lac/lakh."""
    # First check for lac/lakh patterns
    lac_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lac|lakh|lacs|lakhs)\b', text, re.I)
    if lac_match:
        return int(float(lac_match.group(1)) * 100000)
    
    # Then check for regular patterns with salary keywords
    match = re.search(r'(?:salary|income|earn|Rs\.?|₹)?\s*([\d,k]+)', text, re.I)
    if not match:
        return None
    salary_str = match.group(1).replace(",", "").lower()
    try:
        if salary_str.endswith("k"):
            return int(float(salary_str[:-1]) * 1000)
        return int(salary_str)
    except:
        return None


def _mask_sensitive_display(pan: str | None, aadhaar: str | None) -> str:
    """Generate masked PII confirmation message for display only.
    
    Args:
        pan: Full PAN number (will be masked to last 4)
        aadhaar: Full Aadhaar number (will be masked to last 4)
    
    Returns:
        Formatted message with masked values
    """
    parts = []
    if pan and len(pan) >= 4:
        parts.append(f"🔐 PAN ending in ****{pan[-4:]} securely recorded")
    if aadhaar and len(aadhaar) >= 4:
        parts.append(f"🔐 Aadhaar ending in ****{aadhaar[-4:]} securely recorded")
    return "\n".join(parts)


async def lookup_customer_by_phone(phone: str) -> dict | None:
    """Lookup existing customer by phone in CRM/MongoDB."""
    try:
        from db.database import users_collection
        # Search for user with matching phone
        user = users_collection.find_one({"phone": phone})
        if user:
            print(f"👤 [CRM LOOKUP] Found user by phone: {phone}")
            return {
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "phone": user.get("phone", ""),
                "city": user.get("city", ""),
                "salary": user.get("salary", 0),
                "dob": user.get("dob", ""),
                "credit_score": user.get("credit_score", 650),
                "pre_approved_limit": user.get("pre_approved_limit", 100000),
                "existing_emi_total": user.get("existing_emi_total", 0),
                "is_existing_customer": True
            }
    except Exception as e:
        print(f"⚠️ [CRM LOOKUP] Error looking up by phone: {e}")
    return None


async def lookup_customer_by_email(email: str) -> dict | None:
    """Lookup existing customer by email in CRM/MongoDB."""
    try:
        from db.database import users_collection
        # Search for user with matching email
        user = users_collection.find_one({"email": email.lower()})
        if user:
            print(f"👤 [CRM LOOKUP] Found user by email: {email}")
            return {
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "phone": user.get("phone", ""),
                "city": user.get("city", ""),
                "salary": user.get("salary", 0),
                "dob": user.get("dob", ""),
                "credit_score": user.get("credit_score", 650),
                "pre_approved_limit": user.get("pre_approved_limit", 100000),
                "existing_emi_total": user.get("existing_emi_total", 0),
                "is_existing_customer": True
            }
    except Exception as e:
        print(f"⚠️ [CRM LOOKUP] Error looking up by email: {e}")
    return None


def pull_customer_from_db(phone: str) -> dict | None:
    """Pull customer from CRM, set defaults for new users."""
    phone = normalize_phone(phone)
    if not phone:
        return None
    
    customer = None
    
    # 1. Check core CRM (customers.json)
    try:
        with open("mock_apis/customers.json", "r") as f:
            for c in json.load(f):
                if normalize_phone(c["phone"]) == phone:
                    customer = c.copy()
                    customer["is_new_customer"] = False
                    break
    except Exception:
        pass
    
    # 2. Check historical loan applications for this phone number
    past_loans = []
    try:
        if os.path.exists("mock_db.json"):
            with open("mock_db.json", "r") as f:
                db_data = json.load(f)
                
                # Check explicit loan_applications
                loans = db_data.get("loan_applications", {})
                for l_id, loan in loans.items():
                    l_phone = normalize_phone(str(loan.get("phone", "")))
                    if l_phone == phone:
                        past_loans.append({
                            "amount": loan.get("amount", 0),
                            "type": loan.get("loan_type", "Personal"),
                            "date": loan.get("created_at", "N/A"),
                            "status": loan.get("status", "Approved")
                        })
                
                # Also check sessions for completed/sanctioned loans
                sessions = db_data.get("sessions", {})
                for s_id, sess in sessions.items():
                    s_phone = normalize_phone(str(sess.get("customer_data", {}).get("phone", "")))
                    if s_phone == phone:
                        terms = sess.get("loan_terms", {})
                        if terms.get("principal") and sess.get("is_authenticated"):
                            # Avoid duplicates from loan_applications
                            loan_info = {
                                "amount": terms.get("principal", 0),
                                "type": terms.get("loan_type", "Personal"),
                                "date": sess.get("created_at", "N/A"),
                                "status": "Sanctioned" if sess.get("sanction_pdf") else "Draft"
                            }
                            if loan_info not in past_loans:
                                past_loans.append(loan_info)
    except Exception as e:
        print(f"⚠️ History lookup error: {e}")
        pass
        
    if customer or past_loans:
        if not customer:
            # Create a shell customer from past loans if not in CRM (returning customer)
            customer = {"name": "Valued Customer", "phone": phone, "is_new_customer": False}
        else:
            customer["is_new_customer"] = False
        
        # Set defaults from CRM or use fallback
        if "existing_emi_total" not in customer or customer.get("existing_emi_total") is None:
            customer["existing_emi_total"] = 0
        if "credit_score" not in customer or customer.get("credit_score") <= 0:
            customer["credit_score"] = 750  # Returning customer baseline
            customer["score_source"] = "crm_returning"
        else:
            customer["score_source"] = "cibil"
        
        customer["past_loans"] = past_loans
        customer["past_records"] = f"Returning customer with {len(past_loans)} previous records."
        return customer
    
    # NEW CUSTOMER: return minimal shell with defaults
    return {
        "name": "",
        "phone": phone,
        "email": "",
        "city": "",
        "salary": 0,
        "dob": "",
        "is_new_customer": True,
        "credit_score": 650,           # ✅ Default for new users
        "score_source": "system_default",
        "existing_emi_total": 0,        # ✅ Default for new users
        "pre_approved_limit": 100000,   # Default for new users
        "past_loans": [],
        "past_records": "New customer"
    }


REGISTRATION_AGENT_PROMPT = """You are the **Identity & Onboarding Specialist** at FinServe NBFC.

SYSTEM ROLE:
You are responsible for onboarding users, completing their profile for regulatory compliance, and preparing them for transition to the loan journey.

You operate in a **state-driven system (LangGraph)** and must:
- Collect missing profile data
- Validate and normalize inputs
- Maintain data privacy
- Output structured JSON for backend updates

You are NOT:
- A sales agent
- An underwriter
- A financial advisor

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRM DATA & SYSTEM STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Known Profile Data:
{crm_data_json}

Missing Mandatory Fields:
{missing_fields_list}

Pre-Approved Limit:
₹{pre_approved_limit}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CORE RESPONSIBILITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. MULTI-STEP ONBOARDING (PACING)
- Ask for MAXIMUM 1–2 fields per message
- Group related fields together (Email + City, DOB + Salary, PAN + Aadhaar)
- Progressive disclosure: basic info first (name, email), sensitive later (PAN, Aadhaar)
- Avoid overwhelming the user with multiple questions at once
- Example good flow: "What's your email?" → "Which city?" → "Your date of birth?" → "Monthly salary?"

---

2. SMART CONTEXT USAGE
- If user is returning:
  - Greet by name
  - Acknowledge existing data is already available
- NEVER ask for fields already present in Known Profile Data

---

3. DATA CAPTURE RULES

Extract from user input:
- email (validate: contains @ and ., lowercase it)
- city (capitalize first letter)
- salary (extract number, handle formats like "50,000" or "50k", convert to integer)
- dob (extract date, convert to YYYY-MM-DD format)
- pan_number (10 alphanumeric, uppercase)
- aadhaar_number (12 digits)

If a field is not provided → return null
If format is invalid → ask user to clarify ("I need a valid email with @")
Do NOT guess or infer missing values

---

4. DATA NORMALIZATION

- Salary → integer (remove commas, ₹)
- DOB → YYYY-MM-DD
- Email → lowercase
- PAN → uppercase
- Aadhaar → digits only (12 digits)

---

5. SECURE DATA MASKING (CRITICAL)

When user provides:
- PAN → display only last 4 characters
- Aadhaar → display only last 4 digits

Example:
"PAN ending in ****1234 has been securely recorded"

IMPORTANT:
- NEVER show full PAN or Aadhaar in response
- ALWAYS store full value in JSON

---

6. PROGRESS TRACKING

- Track remaining missing fields
- Update:
  - missing_fields_remaining (integer)
  - profile_complete (true/false)

---

7. FINAL HANDOFF (CRITICAL)

When ALL required fields are collected (name, email, phone, city, salary, dob):

1. Celebrate completion:
   "✅ Your profile is complete! You're all set."

2. Reveal pre-approved limit with context:
   "💰 Pre-Approved Limit: ₹{pre_approved_limit}
   This is the maximum we can approve for you based on your profile.
   You can request up to this amount."

3. Provide clear next step:
   "Ready to explore loan options? I'll connect you with our Loan Specialist to discuss your needs."

4. Offer action buttons:
   [✅ Explore Loans] [❓ Have Questions?]

Example:
"Perfect, {{name}}! Your profile is now complete. Your pre-approved limit is ₹{pre_approved_limit}. Shall we start exploring loan options?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT GUARDRAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DO NOT:
- Calculate EMI
- Discuss interest rates
- Offer loan recommendations
- Assume missing data
- Display sensitive data in full

ALWAYS:
- Respect data privacy
- Stay within onboarding scope
- Keep interaction simple and guided

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your response MUST have two parts:

1. Conversational message (first)
- Friendly, professional
- Short and clear
- Ask next required fields

2. JSON block (LAST line ONLY)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JSON OUTPUT CONTRACT (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```json
{{
  "newly_collected_data": {{
    "email": "<string or null>",
    "city": "<string or null>",
    "salary": <integer or null>,
    "dob": "<YYYY-MM-DD or null>",
    "pan_number": "<raw unmasked value or null>",
    "aadhaar_number": "<raw unmasked value or null>"
  }},
  "missing_fields_remaining": <integer>,
  "profile_complete": <true | false>
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL OUTPUT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

JSON MUST be valid
JSON MUST be last in response
NO text after JSON
Do NOT mask values inside JSON
Do NOT omit fields
Use null if not provided

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If user provides multiple fields at once → extract all
If user gives partial data → update only those fields
If invalid format:
Ask for correction
Do NOT store invalid values

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL BEHAVIOR SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are:

A structured onboarding assistant
A secure data collector
A compliance-focused system agent

You are NOT:

A chatbot for general queries
A decision maker
A financial advisor

Act with precision, clarity, and strict adherence to data privacy.
"""


# ─── Nodes ───────────────────────────────────────────────────────────────────────
async def registration_chat_node(state: dict):
    """Generates the chat response for onboarding based on current progress."""
    print("🗣️ [REGISTRATION AGENT] Generating response...")
    from langchain_core.messages import SystemMessage, AIMessage
    from config import get_master_llm
    
    llm = get_master_llm()
    updates = {}

    # Check for missing profile fields
    required_fields = ["name", "email", "city", "salary", "dob"]
    missing = [f for f in required_fields if not state.get("customer_data", {}).get(f)]
    
    # Format missing fields for the prompt
    missing_fields_str = ", ".join(missing) if missing else "None"
    
    sys_msg = SystemMessage(content=REGISTRATION_AGENT_PROMPT.format(
        missing_fields_str=missing_fields_str,
        crm_data_json=json.dumps(state.get("customer_data", {}), indent=2),
        missing_fields_list=missing_fields_str,
        pre_approved_limit=state.get("customer_data", {}).get("pre_approved_limit", 50000)
    ))
    
    # Include memory of what we last asked
    pending = state.get("pending_question", "")
    memory_msg = SystemMessage(content=f"Last question asked: {pending}") if pending else SystemMessage(content="No pending questions.")
    
    messages = [sys_msg, memory_msg] + state.get("messages", [])
    
    response = await llm.ainvoke(messages)
    
    # Check if profile complete (no missing required fields)
    is_complete = len(missing) == 0
    if is_complete:
        # Add pre-approved limit revelation if not already shown
        pre_limit = state.get("customer_data", {}).get("pre_approved_limit", 0)
        if "Pre-Approved Limit" not in response.content:
            response.content += f"\n\n**Pre-Approved Limit:** ₹{pre_limit:,}"
            response.content += f"\nYou're ready to explore our loan products!"
        
        updates["profile_complete"] = True
        # Store JSON data in state, not in chat message
        updates["collected_data"] = {
            "newly_collected_data": {},
            "missing_fields_remaining": 0,
            "profile_complete": True
        }
        
    updates.update({"messages": [response], "current_phase": "registration"})
    
    # Save session to MongoDB
    session_id = state.get("session_id", "default")
    try:
        SessionManager.save_session(session_id, updates)
        print(f"💾 Session {session_id} saved to MongoDB")
    except Exception as e:
        print(f"⚠️ Failed to save session: {e}")
    
    return updates




async def registration_extraction_node(state: dict):
    """Simplified extractor: Collect bare minimum to authenticate, then enrich."""
    print("--- REGISTRATION AGENT: EXTRACTION ---")
    log = list(state.get("action_log") or [])
    log.append("🔍 Running Registration Extraction Node")
    
    # Skip if profile is complete
    if state.get("profile_complete"):
        log.append("⏭️ Profile complete — moving to intent discovery")
        return {"action_log": log, "current_phase": "intent_discovery"}

    user_msg = ""
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break

    if not user_msg or len(user_msg.strip()) < 2:
        return {}

    # 1. ✅ FIXED REGEX SHORTCUTS - Handle various formats
    # Phone: Handle formats like "9876-543-210", "9876 543 210", "+91-9876543210"
    cleaned = user_msg.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    phone_match = re.search(r"(?:\+91)?(\d{10})", cleaned)
    
    otp_match = re.search(r"\b(\d{6})\b", user_msg)
    
    # ✅ FIXED EMAIL - Stricter validation
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", user_msg)
    
    # ✅ FIXED SALARY - Handle commas ("₹50,000" or "50,000")
    salary = extract_salary(user_msg)
    
    # 2. LLM Fallback for Name, City, and unstructured fields
    llm_extracted = {}
    pending = state.get("pending_question")
    
    # Only call LLM if message isn't a simple number/email
    if len(user_msg.split()) >= 1:
        try:
            llm = get_extraction_llm()
            prompt = f"""Extract profile data from this user message. 
            CONTEXT: The customer was specifically asked for their {pending if pending else 'name/info'}.
            MESSAGE: "{user_msg}"
            
            Return JSON only:
            {{
                "name": "Full name or null",
                "city": "City name or null",
                "salary": number or null,
                "email": "Email or null",
                "dob": "DD/MM/YYYY or null",
                "occupation": "Occupation or null",
                "existing_emi_total": number or null
            }}

            """
            res = await llm.ainvoke([HumanMessage(content=prompt)])
            # Simple cleanup to find JSON
            json_str = re.search(r"\{.*\}", res.content, re.DOTALL)
            if json_str:
                llm_ext = json.loads(json_str.group(0))
                llm_extracted = {k: v for k, v in llm_ext.items() if v is not None}
        except Exception as e:
            print(f"  ⚠️ LLM Extraction failed: {e}")

    # Results
    phone = phone_match.group(1) if phone_match else None
    user_otp = otp_match.group(1) if otp_match else None
    email = email_match.group(0).lower() if email_match and is_valid_email(email_match.group(0)) else llm_extracted.get("email")
    
    updates = {}
    customer_data = state.get("customer_data", {}).copy()

    # ✅ CAPTURE ALL AVAILABLE DATA FIRST
    # Capture phone if available
    if phone and not customer_data.get("phone"):
        normalized = normalize_phone(phone)
        if normalized:
            customer_data["phone"] = normalized
            log.append(f"☎️ Phone: {normalized}")
            # 🔍 CRM LOOKUP: Check if user exists in CRM
            crm_data = await lookup_customer_by_phone(normalized)
            if crm_data:
                log.append(f"👤 Found existing customer in CRM")
                # Merge CRM data (CRM takes precedence for existing fields)
                for key, value in crm_data.items():
                    if value and not customer_data.get(key):
                        customer_data[key] = value
                        log.append(f"  ↳ Loaded {key} from CRM")
    
    # Capture email if available
    if email and not customer_data.get("email"):
        if is_valid_email(email):
            customer_data["email"] = email.lower()
            log.append(f"📧 Email: {email}")
            # 🔍 CRM LOOKUP: Check if user exists in CRM by email
            crm_data = await lookup_customer_by_email(email.lower())
            if crm_data:
                log.append(f"👤 Found existing customer in CRM by email")
                # Merge CRM data (CRM takes precedence for existing fields)
                for key, value in crm_data.items():
                    if value and not customer_data.get(key):
                        customer_data[key] = value
                        log.append(f"  ↳ Loaded {key} from CRM")
        else:
            log.append(f"⚠️ Invalid email format: {email}")
    
    # Extract remaining fields via LLM
    # ✅ Do NOT extract existing_emi_total or occupation - they come from CRM/API
    for k, v in llm_extracted.items():
        if v and k not in ["existing_emi_total", "occupation", "salary"]:
            if not customer_data.get(k):
                customer_data[k] = v
                log.append(f"📝 {k.capitalize()}: {v}")
    
    # ✅ FIXED: Handle salary extraction with new function
    if salary and not customer_data.get("salary"):
        customer_data["salary"] = salary
        log.append(f"💰 Salary: ₹{salary:,}")
    
    # SET AUTHENTICATION: if we have contact info, user is authenticated
    has_contact = customer_data.get("phone") or customer_data.get("email")
    if has_contact and not state.get("is_authenticated"):
        updates["is_authenticated"] = True
        log.append("Contact info captured - profile enrichment enabled")
    
    # CHECK COMPLETION: all required fields present?
    # ✅ Do NOT require phone/existing_emi_total (they're in CRM)
    required = ["name", "email", "city", "salary", "dob"]
    missing = [f for f in required if not customer_data.get(f)]
    is_complete = len(missing) == 0
    
    if is_complete:
        log.append("Profile COMPLETE - all required fields collected")
        updates["profile_complete"] = True
    else:
        log.append(f"Profile incomplete - missing: {', '.join(missing)}")

    updates["customer_data"] = customer_data
    updates["action_log"] = log
    return updates


# ─── Router ──────────────────────────────────────────────────────────────────────
def route_registration(state: dict):
    """Exit registration when profile is complete."""
    if state.get("profile_complete"):
        return END
    return "chat"


# ─── Graph Builder ───────────────────────────────────────────────────────────────
def build_registration_agent():
    workflow = StateGraph(RegistrationState)
    workflow.add_node("chat", registration_chat_node)
    workflow.add_node("extract_data", registration_extraction_node)
    workflow.add_edge(START, "chat")
    workflow.add_edge("chat", "extract_data")
    workflow.add_conditional_edges("extract_data", route_registration, {END: END, "chat": "chat"})
    return workflow.compile()
