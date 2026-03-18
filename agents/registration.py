"""Registration Agent — OTP-based Login + CRM Lookup for returning users."""

import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from mock_apis.otp_service import send_otp, verify_otp
from config import get_extraction_llm


# ─── Pydantic Schema ────────────────────────────────────────────────────────────
class RegistrationData(BaseModel):
    """Extracted fields from the user's latest message."""
    phone: str | None = Field(default=None, description="10-digit phone number if explicitly provided.")
    user_otp: str | None = Field(default=None, description="6-digit OTP code if the user typed one.")
    name: str | None = Field(default=None, description="Full name if explicitly provided by a new user.")


# ─── State ───────────────────────────────────────────────────────────────────────
class RegistrationState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    phone: str | None
    otp_sent: bool
    otp_verified: bool
    customer_profile: dict | None


def normalize_phone(phone: str) -> str:
    """Strip +91, 91 prefix and spaces to get clean 10-digit number."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]
    return phone[-10:]  # Always return last 10 digits


# ─── CRM Lookup ──────────────────────────────────────────────────────────────────
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
def chat_node(state: RegistrationState):
    """Dynamic system-prompt chatbot that adapts based on registration progress."""
    print("--- REGISTRATION AGENT: CHATTING ---")
    llm = get_extraction_llm()

    sys_prompt = "You are a friendly NBFC Login Agent for FinServe. Keep responses short (2-3 sentences max). "
    if not state.get("phone"):
        sys_prompt += "Welcome the customer warmly and ask for their 10-digit mobile number to get started."
    elif state.get("phone") and not state.get("otp_verified"):
        sys_prompt += f"An OTP has been sent to {state['phone']}. Ask them to enter the 6-digit code they received via SMS."
    elif state.get("otp_verified") and not state.get("customer_profile", {}).get("name"):
        sys_prompt += "OTP verified! This is a new customer. Ask them for their full name to create their profile."
    else:
        sys_prompt += "Login is fully complete. Thank them warmly and tell them the Sales Agent will now assist them."

    messages = [{"role": "system", "content": sys_prompt}] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def extraction_node(state: RegistrationState):
    """Silently extracts phone/OTP/name and triggers backend actions."""
    print("--- REGISTRATION AGENT: EXTRACTION & BACKEND ---")
    llm = get_extraction_llm()
    data_extractor = llm.with_structured_output(RegistrationData)

    recent = [
        f"{'User' if isinstance(m, HumanMessage) else 'Agent'}: {m.content}"
        for m in state["messages"][-4:]
        if isinstance(m, (HumanMessage, AIMessage))
    ]

    extraction: RegistrationData = data_extractor.invoke([{
        "role": "user",
        "content": f"Extract phone, OTP code, or name from the latest message ONLY.\n\nChat:\n{chr(10).join(recent)}"
    }])

    updates = {}

    # Phase 1: Got phone → fire OTP
    if extraction.phone and not state.get("phone"):
        clean_phone = normalize_phone(extraction.phone)
        print(f"🔑 Sending OTP to {clean_phone}")
        res = send_otp(clean_phone)
        updates["phone"] = clean_phone
        updates["otp_sent"] = res["sent"]
        otp_display = f" (Dev OTP: {res.get('otp', 'N/A')})" if res["sent"] else ""
        updates["messages"] = [AIMessage(content=f"📱 {res['message']}{otp_display}")]

    # Phase 2: Got OTP → verify
    elif extraction.user_otp and state.get("phone") and not state.get("otp_verified"):
        print(f"🔑 Verifying OTP: {extraction.user_otp}")
        res = verify_otp(state["phone"], extraction.user_otp)
        if res["verified"]:
            updates["otp_verified"] = True
            db = pull_customer_from_db(state["phone"])
            if db:
                updates["customer_profile"] = db
                updates["messages"] = [AIMessage(
                    content=f"✅ OTP Verified! Welcome back, **{db['name']}**! 🎉\n"
                            f"📊 Your Profile: Credit Score **{db['credit_score']}** | "
                            f"Pre-approved Limit **₹{db['pre_approved_limit']:,}** | "
                            f"City: {db['city']}"
                )]
            else:
                updates["messages"] = [AIMessage(content="✅ OTP Verified! You're a new customer. What's your full name?")]
        else:
            updates["messages"] = [AIMessage(content=f"❌ {res['message']}")]

    # Phase 3: New user gave name → create profile
    elif state.get("otp_verified") and not state.get("customer_profile") and extraction.name:
        updates["customer_profile"] = {
            "name": extraction.name, "phone": state["phone"],
            "credit_score": 700, "pre_approved_limit": 100000, "salary": 30000,
            "city": "Unknown", "current_loans": [], "risk_flags": []
        }
        updates["messages"] = [AIMessage(content=f"✅ Profile created for **{extraction.name}**! Let's find you the perfect loan.")]

    return updates


# ─── Router ──────────────────────────────────────────────────────────────────────
def route_registration(state: RegistrationState):
    """Continue chatting until we have a verified profile."""
    if state.get("otp_verified") and state.get("customer_profile", {}).get("name"):
        return END
    return "chat"


# ─── Graph Builder ───────────────────────────────────────────────────────────────
def build_registration_agent():
    workflow = StateGraph(RegistrationState)
    workflow.add_node("chat", chat_node)
    workflow.add_node("extract_data", extraction_node)

    workflow.add_edge(START, "chat")
    workflow.add_edge("chat", "extract_data")
    workflow.add_conditional_edges("extract_data", route_registration, {END: END, "chat": "chat"})

    return workflow.compile()


if __name__ == "__main__":
    app = build_registration_agent()
    print("Registration Agent compiled successfully!")
