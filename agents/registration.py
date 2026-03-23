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
    phone = str(phone).strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]
    return "".join(filter(str.isdigit, phone))[-10:]


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


def pull_customer_from_db(phone: str) -> dict | None:
    phone = normalize_phone(phone)
    customer = None
    
    # 1. Check core CRM (customers.json)
    try:
        with open("mock_apis/customers.json", "r") as f:
            for c in json.load(f):
                if normalize_phone(c["phone"]) == phone:
                    customer = c
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
            # Create a shell customer from past loans if not in CRM
            customer = {"name": "Valued Customer", "phone": phone}
            
        customer["past_loans"] = past_loans
        customer["past_records"] = f"Returning customer with {len(past_loans)} previous records."
        return customer

        
    return None


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
- Group related fields together:
  - Email + City
  - DOB + Salary
  - PAN + Aadhaar
- Do NOT ask all fields at once

---

2. SMART CONTEXT USAGE
- If user is returning:
  - Greet by name
  - Acknowledge existing data is already available
- NEVER ask for fields already present in Known Profile Data

---

3. DATA CAPTURE RULES

Extract ONLY from user input:
- email
- city
- salary (convert to integer)
- dob (convert to YYYY-MM-DD)
- pan_number
- aadhaar_number

If a field is not provided → return null

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

When ALL required fields are collected:

- Inform user:
  "Your profile is now complete."

- Reveal:
  Pre-approved limit ₹{pre_approved_limit}

- Transition:
  Ask user if they want to proceed to loan exploration

Example:
"You now have a pre-approved limit of ₹{pre_approved_limit}. Shall I connect you with our Loan Specialist?"

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
{
  "newly_collected_data": {
    "email": "<string or null>",
    "city": "<string or null>",
    "salary": <integer or null>,
    "dob": "<YYYY-MM-DD or null>",
    "pan_number": "<raw unmasked value or null>",
    "aadhaar_number": "<raw unmasked value or null>"
  },
  "missing_fields_remaining": <integer>,
  "profile_complete": <true | false>
}

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
    """Generates the chat response for Phase 0 based on current progress."""
    print("🗣️ [REGISTRATION AGENT] Generating response...")
    from langchain_core.messages import SystemMessage, AIMessage
    from config import get_master_llm
    
    llm = get_master_llm()
    phase = state.get("current_phase", "registration")
    otp_verified = state.get("is_authenticated", False)
    updates = {}

    # Check for missing profile fields
    required_fields = ["name", "email", "city", "salary", "dob", "occupation"]
    missing = [f for f in required_fields if not state.get("customer_data", {}).get(f)]

    
    # Format missing fields for the prompt
    missing_fields_str = ", ".join(missing) if missing else "NONE (All complete)"
    
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
    
    # Only show Dev OTP during the verification phase
    if not otp_verified:
        dev_otp = state.get("customer_data", {}).get("dev_otp")
        if dev_otp:
            response.content += f"\n\n📱 **(Dev Mode OTP: {dev_otp})**"
    
    # Check if profile complete and append JSON schema
    is_complete = len(missing) == 0 and otp_verified
    if is_complete:
        # Add pre-approved limit revelation if not already shown
        pre_limit = state.get("customer_data", {}).get("pre_approved_limit", 0)
        if "Pre-Approved Limit" not in response.content:
            response.content += f"\n\n**Pre-Approved Limit:** ₹{pre_limit:,}"
            response.content += f"\nYou're ready to explore our loan products!"
        
        # Append JSON schema
        json_output = {
            "newly_collected_data": {},
            "missing_fields_remaining": 0,
            "profile_complete": True
        }
        response.content += f"\n\n```json\n{json.dumps(json_output, indent=2)}\n```"
        updates["profile_complete"] = True
        
    updates.update({"messages": [response], "current_phase": phase})
    return updates




async def registration_extraction_node(state: dict):
    """Robust extractor using regex + simple LLM fallback (no fragile tool-calls)."""
    print("--- REGISTRATION AGENT: EXTRACTION ---")
    log = list(state.get("action_log") or [])
    log.append("🔍 Running Registration Extraction Node")
    
    if state.get("is_authenticated") and state.get("customer_data", {}).get("name"):
        log.append("⏭️ Already authenticated — skipping extraction")
        return {"action_log": log, "current_phase": "intent_discovery"}

    user_msg = ""
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break

    if not user_msg or len(user_msg.strip()) < 2:
        return {}

    # 1. Regex shortcuts (FAST & FREE)
    phone_match = re.search(r"\b(\d{10})\b", user_msg)
    otp_match   = re.search(r"\b(\d{6})\b", user_msg)
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", user_msg)
    salary_match = re.search(r"(?:salary|income|earn|Rs\.?|₹)\s*(\d+k?|\d{4,7})", user_msg, re.I)
    
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
    email = email_match.group(0) if email_match else llm_extracted.get("email")
    
    updates = {}
    customer_data = state.get("customer_data", {}).copy()
    is_auth = state.get("is_authenticated", False)

    # Phase 1: Got phone
    if phone and not customer_data.get("phone") and not is_auth:
        clean_phone = normalize_phone(phone)
        log.append(f"📱 Phone number detected: {clean_phone}")
        log.append("🔐 Triggering OTP via SMS gateway")
        
        # Use auth_service for consistent logic
        from api.services.auth_service import auth_service
        res = await auth_service.send_otp(clean_phone, "customer@example.com") # Temp email placeholder
        
        customer_data["phone"] = clean_phone
        updates["otp_sent"] = res.get("success", False)
        if res.get("success"):
            otp_val = res.get('dev_otp', 'SENT')
            log.append(f"✅ OTP sent successfully")
            customer_data["dev_otp"] = otp_val 
            msg = f"📱 OTP sent to {clean_phone}."
            if otp_val != 'SENT': msg += f" (Dev OTP: `{otp_val}`)"
            updates["messages"] = [AIMessage(content=msg)]
        else:
            log.append("❌ OTP delivery failed")
            updates["messages"] = [AIMessage(content=f"❌ {res.get('message', 'Failed to send OTP')}")]

    # Phase 2: Got OTP
    elif user_otp and customer_data.get("phone") and not is_auth:
        log.append(f"🔑 OTP code received — verifying")
        from api.services.auth_service import auth_service
        res = await auth_service.verify_otp(customer_data["phone"], user_otp)
        
        if res["success"]:
            updates["is_authenticated"] = True
            if "dev_otp" in customer_data:
                del customer_data["dev_otp"]
                log.append("🧹 Cleaned sensitive development data")
            log.append("✅ OTP verified successfully")

            log.append("🗃️ Looking up customer in CRM database")
            db = pull_customer_from_db(customer_data["phone"])
            if db:
                customer_data.update(db)
                log.append(f"👤 Existing customer found: {db['name']}")
                msg = f"✅ Welcome back, **{db['name']}**! I've loaded your profile. How can I help you today?"
                updates["messages"] = [AIMessage(content=msg)]
                # Trigger profile check next turn via supervisor
            else:
                log.append("🆕 New customer — creating fresh profile")
                updates["messages"] = [AIMessage(content="✅ OTP Verified! You're new here. What's your full name?")]
        else:
            log.append("❌ OTP verification failed — incorrect code")
            updates["messages"] = [AIMessage(content=f"❌ {res['message']}")]

    # Phase 3: Profile Enrichment
    elif is_auth:
        # Merge LLM extractions into customer_data
        enriched = False
        masked_msg = ""
        
        for k, v in llm_extracted.items():
            if v and not customer_data.get(k):
                customer_data[k] = v
                log.append(f"📝 Profile update: {k} = {v}")
                enriched = True
        
        # Email extraction
        if email and not customer_data.get("email"):
            customer_data["email"] = email
            log.append(f"📧 Email extracted: {email}")
            enriched = True
        
        # PAN & Aadhaar masking (store full, display masked)
        pan = llm_extracted.get("pan_number")
        aadhaar = llm_extracted.get("aadhaar_number")
        if pan or aadhaar:
            if pan and not customer_data.get("pan_number"):
                customer_data["pan_number"] = pan
                enriched = True
            if aadhaar and not customer_data.get("aadhaar_number"):
                customer_data["aadhaar_number"] = aadhaar
                enriched = True
            
            # Generate masked display message
            masked_msg = "\n\n" + _mask_sensitive_display(pan, aadhaar)
            log.append("✅ Sensitive data masked for display (stored securely)")
            
        if enriched:
            # Sync to DB
            try:
                from db.database import users_collection
                await users_collection.update_one(
                    {"phone": customer_data["phone"]},
                    {"$set": {k: v for k, v in customer_data.items() if k in ["name", "email", "city", "salary", "existing_emi_total", "credit_score", "pan_number", "aadhaar_number", "dob"]}},
                    upsert=True
                )
            except Exception as e:
                print(f"  ⚠️ DB Update failed: {e}")
        
        # Check if profile is now complete
        required_fields = ["name", "email", "city", "salary", "dob"]
        missing = [f for f in required_fields if not customer_data.get(f)]
        profile_complete = len(missing) == 0
        
        # Generate pre-approved limit reveal message if profile complete
        if profile_complete:
            pre_limit = customer_data.get("pre_approved_limit", 0)
            handoff_msg = (
                f"✅ **Your profile is now complete!**\n\n"
                f"**Pre-Approved Limit:** ₹{pre_limit:,}\n\n"
                f"You're now ready to explore our loan products. "
                f"Shall I connect you with our Loan Specialist?"
            )
            
            if masked_msg:
                handoff_msg = masked_msg + "\n\n" + handoff_msg
            
            updates["messages"] = [AIMessage(content=handoff_msg)]
            updates["profile_complete"] = True
            log.append(f"🎉 Profile complete! Pre-approved limit: ₹{pre_limit:,}")
        elif masked_msg:
            # Just show the masked message if not complete yet
            updates["messages"] = [AIMessage(content=masked_msg)]
        
        # Build JSON schema output (always append)
        json_output = {
            "newly_collected_data": {
                "email": llm_extracted.get("email"),
                "city": llm_extracted.get("city"),
                "salary": llm_extracted.get("salary"),
                "dob": llm_extracted.get("dob"),
                "pan_number": llm_extracted.get("pan_number"),
                "aadhaar_number": llm_extracted.get("aadhaar_number")
            },
            "missing_fields_remaining": len(missing),
            "profile_complete": profile_complete
        }
        
        # Append JSON to response if we had a message
        if "messages" in updates:
            updates["messages"][0].content += f"\n\n```json\n{json.dumps(json_output, indent=2)}\n```"
        else:
            # Create a message just for the JSON if enriched
            if enriched:
                updates["messages"] = [AIMessage(content=f"```json\n{json.dumps(json_output, indent=2)}\n```")]

    updates["customer_data"] = customer_data
    updates["action_log"] = log
    return updates


# ─── Router ──────────────────────────────────────────────────────────────────────
def route_registration(state: dict):
    if state.get("is_authenticated") and state.get("customer_data", {}).get("name"):
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
