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
    try:
        with open("mock_apis/customers.json", "r") as f:
            for c in json.load(f):
                if c["phone"] == phone:
                    return c
    except Exception:
        pass
    return None


# ─── Nodes ───────────────────────────────────────────────────────────────────────
def registration_chat_node(state: dict):
    print("--- REGISTRATION AGENT: CHATTING ---")
    from config import get_extraction_llm
    llm = get_extraction_llm()

    phone = state.get("customer_data", {}).get("phone")
    otp_verified = state.get("is_authenticated", False)
    name = state.get("customer_data", {}).get("name")

    sys_prompt = "You are Arjun, a friendly FinServe Assistant. Keep responses short (2-3 sentences max). "
    if not phone:
        sys_prompt += "Welcome requested customer warmly. Ask for their 10-digit mobile number to help them with loans, CIBIL tips, or KYC."
    elif phone and not otp_verified:
        sys_prompt += f"An OTP has been sent to {phone}. Ask them to enter the 6-digit code from their SMS."
    elif otp_verified and not name:
        sys_prompt += "OTP verified! Since you're new here, may I have your full name to set up your profile?"
    else:
        sys_prompt += "Great! You're all set. How can I assist you further today?"

    messages = [SystemMessage(content=sys_prompt)] + state["messages"]
    response = llm.invoke(messages)
    
    # Ensure Dev OTP is never lost due to message rendering overrides
    dev_otp = state.get("customer_data", {}).get("dev_otp")
    if dev_otp:
        response.content += f"\n\n📱 **(Dev Mode OTP: {dev_otp})**"
        
    return {"messages": [response]}


def registration_extraction_node(state: dict):
    """Robust extractor using regex + simple LLM fallback (no fragile tool-calls)."""
    print("--- REGISTRATION AGENT: EXTRACTION ---")
    log = list(state.get("action_log") or [])
    log.append("🔍 Running Registration Extraction Node")
    
    if state.get("is_authenticated") and state.get("customer_data", {}).get("name"):
        log.append("⏭️ Already authenticated — skipping extraction")
        return {"action_log": log}

    user_msg = ""
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break

    if not user_msg or len(user_msg.strip()) < 2:
        return {}

    # 1. Regex shortcuts (FAST & FREE)
    phone_match = re.search(r"\b(\d{10})\b", user_msg)
    otp_match = re.search(r"\b(\d{6})\b", user_msg)
    
    # 2. LLM Fallback (Manual Parsing to avoid OpenAI 400 errors)
    extracted_name = None
    if not phone_match and not otp_match:
        # Only call LLM if message is long or looks like a name
        if len(user_msg.split()) > 1 and state.get("is_authenticated"):
            try:
                llm = get_extraction_llm()
                prompt = f"Extract the FULL NAME from this message if present, otherwise return 'NONE':\n\nMESSAGE: {user_msg}\n\nNAME:"
                res = llm.invoke([HumanMessage(content=prompt)])
                ans = res.content.strip().replace("'", "").replace("\"", "")
                if ans != "NONE" and len(ans) > 2:
                    extracted_name = ans
            except Exception as e:
                print(f"  ⚠️ LLM Name Extraction failed: {e}")

    # Results
    phone = phone_match.group(1) if phone_match else None
    user_otp = otp_match.group(1) if otp_match else None
    
    updates = {}
    customer_data = state.get("customer_data", {}).copy()
    is_auth = state.get("is_authenticated", False)

    # Phase 1: Got phone
    if phone and not customer_data.get("phone") and not is_auth:
        clean_phone = normalize_phone(phone)
        log.append(f"📱 Phone number detected: {clean_phone}")
        log.append("🔐 Triggering OTP via SMS gateway")
        res = send_otp(clean_phone)
        customer_data["phone"] = clean_phone
        updates["otp_sent"] = res["sent"]
        if res["sent"]:
            otp_val = res.get('otp', 'N/A')
            log.append(f"✅ OTP sent successfully")
            customer_data["dev_otp"] = otp_val # Keep it here to inject into chat later
            msg = f"📱 OTP sent to {clean_phone}. (Dev OTP: `{otp_val}`)" 
            updates["messages"] = [AIMessage(content=msg)]
        else:
            log.append("❌ OTP delivery failed")
            updates["messages"] = [AIMessage(content=f"❌ {res['message']}")]

    # Phase 2: Got OTP
    elif user_otp and customer_data.get("phone") and not is_auth:
        log.append(f"🔑 OTP code received — verifying")
        res = verify_otp(customer_data["phone"], user_otp)
        if res["verified"]:
            updates["is_authenticated"] = True
            if "dev_otp" in customer_data:
                del customer_data["dev_otp"]
            log.append("✅ OTP verified successfully")
            log.append("🗃️ Looking up customer in CRM database")
            db = pull_customer_from_db(customer_data["phone"])
            if db:
                customer_data.update({
                    "name": db["name"], "phone": db["phone"], "salary": db["salary"], "credit_score": db["credit_score"]
                })
                log.append(f"👤 Existing customer found: {db['name']}")
                log.append(f"📊 Credit score loaded: {db['credit_score']}")
                msg = f"✅ Welcome back, **{db['name']}**! I've loaded your profile (Credit Score: {db['credit_score']}). How can I help?"
                updates["messages"] = [AIMessage(content=msg)]
            else:
                log.append("🆕 New customer — creating fresh profile")
                updates["messages"] = [AIMessage(content="✅ OTP Verified! You're new here. What's your full name?")]
        else:
            log.append("❌ OTP verification failed — incorrect code")
            updates["messages"] = [AIMessage(content=f"❌ {res['message']}")]

    # Phase 3: Got Name
    elif is_auth and not customer_data.get("name") and extracted_name:
        log.append(f"📝 Name extracted: {extracted_name}")
        log.append("✅ New customer profile created")
        customer_data["name"] = extracted_name
        msg = f"✅ Perfect, **{extracted_name}**! Your profile is ready. Do you need a loan, financial advice, or KYC help?"
        updates["messages"] = [AIMessage(content=msg)]

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
