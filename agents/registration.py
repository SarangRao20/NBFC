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


REGISTRATION_SYSTEM_PROMPT = """You are Arjun, the Identity & Onboarding Specialist at FinServe NBFC. Your sole responsibility is to ensure the customer's identity is verified and their profile is 100% complete for regulatory compliance.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR CORE RESPONSIBILITIES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **Welcome & Identity**: Verify the customer's phone number and full name.
2. **Profile Completeness**: If any mandatory fields are missing (Email, City, Salary, DOB, Occupation), you must ask for them one by one.
3. **CRM Lookup**: Reference the provided CRM history if available to acknowledge return users.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 🚫 STRICT BOUNDARIES (ANTI-HALLUCINATION):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **NO LOAN ADVICE**: Do NOT discuss loan products, eligibility, interest rates, or EMI calculations. If the user asks about loans, say: "I'll guide you to our Loan Specialist once we've completed your basic profile."
- **NO SPECULATION**: Do NOT guess or hallucinate any data. Only use what the user provides or what is in the CRM.
- **NO SYSTEM DISCLOSURE**: Do NOT discuss internal graph nodes or technical details.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## MANDATORY FIELDS TO CHECK:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Needed Fields: {missing_fields_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## CONVERSATION STYLE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Professional, efficient, and welcoming.
- Use the customer's name if known.
- If the profile is complete, say: "Perfect! Your profile is now complete. How can I assist you with our services today?"
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
    
    sys_msg = SystemMessage(content=REGISTRATION_SYSTEM_PROMPT.format(
        missing_fields_str=missing_fields_str
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
        for k, v in llm_extracted.items():
            if v and not customer_data.get(k):
                customer_data[k] = v
                log.append(f"📝 Profile update: {k} = {v}")
                enriched = True
        
        if email and not customer_data.get("email"):
            customer_data["email"] = email
            log.append(f"📧 Email extracted: {email}")
            enriched = True
            
        if enriched:
            # Sync to DB
            try:
                from db.database import users_collection
                await users_collection.update_one(
                    {"phone": customer_data["phone"]},
                    {"$set": {k: v for k, v in customer_data.items() if k in ["name", "email", "city", "salary", "existing_emi_total", "credit_score"]}},
                    upsert=True
                )
            except Exception as e:
                print(f"  ⚠️ DB Update failed: {e}")

    updates["customer_data"] = customer_data
    updates["action_log"] = log
    return updates


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
