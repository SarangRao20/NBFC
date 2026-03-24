"""Sales Agent — Financial Advisor first, then Loan Sales mode.

Two modes:
1. Advisor Mode (when customer is logged in): proactively surface credit info, loans, tips, investments.  
2. Loan Sales Mode (anonymous or post-advisory): help user pick loan product and confirm terms.
"""

import json
import re
from typing import Optional

from config import get_master_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from mock_apis.loan_products import LOAN_PRODUCTS
from agents.session_manager import SessionManager
from api.core.websockets import manager

# ─── Keyword-based apply intent (NO LLM call) ────────────────────────────────
APPLY_KEYWORDS = {
    "yes", "apply", "proceed", "go ahead", "go", "sure", "let's do it",
    "lets do it", "yep", "yeah", "yup", "haan", "haan ji", "ok", "okay",
    "confirm", "book", "start", "i want to apply", "want to apply", "apply now",
    "chalte hain", "karo", "proceed karo", "han", "bilkul", "absolutely",
    "definitely", "of course", "sounds good", "let's go", "lets go"
}

YES_WORDS = {"yes", "y", "ok", "okay", "sure", "proceed", "confirm", "go ahead", "done", "haan", "han"}
NO_WORDS = {"no", "n", "change", "edit", "not now", "cancel", "stop"}

def detect_apply_intent(text: str) -> bool:
    """Returns True if user clearly wants to apply for a loan. Zero LLM cost."""
    cleaned = text.strip().lower()
    if cleaned in APPLY_KEYWORDS:
        return True
    if len(cleaned) < 60:
        return any(kw in cleaned for kw in APPLY_KEYWORDS)
    return False


def _parse_amount_inr(text: str) -> Optional[float]:
    t = (text or "").lower().replace(",", "").strip()
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(lakh|lac)", t)
    if lakh_match:
        return float(lakh_match.group(1)) * 100000
    k_match = re.search(r"(\d+(?:\.\d+)?)\s*(k|thousand)", t)
    if k_match:
        return float(k_match.group(1)) * 1000
    rs_match = re.search(r"(?:rs\.?|inr|rupees?)?\s*(\d{4,9}(?:\.\d+)?)", t)
    if rs_match:
        return float(rs_match.group(1))
    return None


def _parse_tenure_months(text: str) -> Optional[int]:
    t = (text or "").lower().strip()
    m = re.search(r"(\d{1,3})\s*(months?|mos?)", t)
    if m:
        return int(m.group(1))
    y = re.search(r"(\d{1,2})\s*(years?|yrs?)", t)
    if y:
        return int(y.group(1)) * 12
    only_num = re.fullmatch(r"\d{1,3}", t)
    if only_num:
        n = int(only_num.group(0))
        if 6 <= n <= 120:
            return n
    return None


def _calc_emi(principal: float, rate_pa: float, tenure: int) -> float:
    if principal <= 0 or tenure <= 0:
        return 0.0
    r = (rate_pa / 12) / 100
    if r == 0:
        return round(principal / tenure, 2)
    emi = principal * r * ((1 + r) ** tenure) / (((1 + r) ** tenure) - 1)
    return round(emi, 2)


SALES_CLOSER_PROMPT = """You are Arjun, a Senior Loan Specialist and Financial Advisor at FinServe.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR PERSONALITY & TONE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **EMPATHETIC PARTNER**: You aren't just selling a loan; you're helping a human achieve a goal (e.g., home, business, education). 
- **CONVERSATIONAL, NOT TRANSACTIONAL**: Avoid jumping straight to "Tenure" or "Amount". Ask about their day, their business, or their vision first.
- **FOR RETURNING USERS**: Acknowledge their history. If they've paid off a loan, congratulate them! If they haven't spoken to you in a while, ask how they've been.
- **NO JARGON**: Use plain language. Instead of "DTI Ratio", say "monthly obligations". Instead of "Principal", say "amount you need".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## CONVERSATIONAL PROTOCOL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **ACKNOWLEDGE & CATCH UP**: For returning users, ALWAYS spend at least one turn catching up or acknowledging past success (e.g., "Welcome back! I saw you just finished your last loan, that's a huge milestone!").
2. **DISCOVER THE 'WHY'**: Before asking technical details (tenure, type), understand the *purpose*. Why 1 lakh? What's the dream?
3. **NATURAL PROGRESSION**: Only move to technical terms when the user feels heard and guided.
4. **ONE QUESTION**: Always end with exactly one natural question.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## JSON CAPTURE (Silent)
When the user shares technical details OR you reach agreement, include this at the end:
```json
{ 
  "loan_purpose": "...", 
  "loan_type": "fixed/reducing", 
  "loan_amount": 0, 
  "tenure": 12, 
  "confirmed": false,
  "options": ["...", "..."]
}
```
Set `confirmed: true` ONLY when the user says "Yes", "Confirm", or "Proceed" after seeing final terms.
"""




def _build_products_info() -> str:
    lines = []
    for key, p in LOAN_PRODUCTS.items():
        lines.append(
            f"**{p['name']}** ({key})\n"
            f"  Amount Range: ₹{p['min_amount']:,} – ₹{p['max_amount']:,} | "
            f"Base Rate: {p['base_rate']}% p.a."
        )
    return "\n".join(lines)


def _build_customer_context(customer: dict) -> str:
    if not customer:
        return "No customer profile loaded — user is ANONYMOUS."

    name = customer.get("name", "Customer")
    score = customer.get("credit_score") or customer.get("score", "N/A")
    limit = customer.get("pre_approved_limit") or customer.get("limit", 0)
    salary = customer.get("salary", 0)
    emi_total = customer.get("existing_emi_total", 0)
    loans = customer.get("current_loans", [])
    city = customer.get("city", "")
    
    # Enhanced Memory & Natural Greeting
    past_records = customer.get("past_records") or "No previous recorded interactions."
    drop_offs = customer.get("drop_off_history") or "None recorded."
    intent = customer.get("intent", "Checking options")
    
    # Check for returning customer status
    is_returning = not customer.get("is_new_customer", True)
    greeting_hint = ""
    if is_returning:
        greeting_hint = f"Note: This is a RETURNING customer. Start with 'Welcome back, {name}!' and acknowledge their history naturally."

    return (
        f"Customer Name: {name} | City: {city}\n"
        f"Monthly Salary: ₹{salary:,}/month\n"
        f"CIBIL / Credit Score: {score}\n"
        f"Pre-Approved Loan Limit: ₹{limit:,}\n"
        f"Existing Monthly EMI Burden: ₹{emi_total:,}/month\n"
        f"Active Loans: {', '.join(loans) if loans else 'None'}\n"
        f"Past Interactions/Sanctions: {past_records}\n"
        f"Previous Drop-off Points: {drop_offs}\n"
        f"Current Session Intent: {intent}\n"
        f"{greeting_hint}"
    )


def _extract_json_from_response(text: str) -> Optional[dict]:
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except Exception:
            pass
    return None


async def sales_chat_response(
    user_message: str,
    chat_history: list[dict],
    extra_context: str = "",
    customer: dict = None
) -> dict:
    """Process a single chat turn. customer dict enables advisor mode."""
    llm = get_master_llm()

    customer_context = _build_customer_context(customer or {})
    messages = [
        SystemMessage(content=SALES_CLOSER_PROMPT),
        SystemMessage(content=f"## CUSTOMER PROFILE\n{customer_context}"),

        SystemMessage(content=f"## LOAN PRODUCTS\n{_build_products_info()}")
    ]
    if extra_context.strip():
        messages.append(SystemMessage(content=f"## ADDITIONAL CONTEXT\n{extra_context.strip()}"))
    for msg in chat_history:
        role = HumanMessage if msg["role"] == "user" else AIMessage
        messages.append(role(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    response = await llm.ainvoke(messages)
    reply = response.content
    extracted = _extract_json_from_response(reply)

    return {"reply": reply, "extracted": extracted}


async def sales_agent_node(state: dict):
    """LangGraph node for Sales / Advisor interaction."""
    session_id = state.get("session_id", "default")
    await manager.broadcast_thinking(session_id, "Arjun (Sales)", True)

    import re as _re
    print("🗣️ [SALES AGENT] Processing turn...")
    
    print("🗣️ [SALES AGENT] Processing turn...")
    
    log = list(state.get("action_log") or [])
    log.append("📡 Initiating financial intent analysis...")
    
    history = []
    for m in state.get("messages", []):
        role = "user" if isinstance(m, HumanMessage) else "assistant"
        history.append({"role": role, "content": m.content})
    
    user_msg = ""
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break
            
    customer_context = state.get("customer_data", {}).copy()
    customer_context["intent"] = state.get("intent", "Checking options")

    # Handle OCR Friction / Guidance
    ocr_error = state.get("documents", {}).get("ocr_error", "")
    ocr_context = ""
    if ocr_error:
        ocr_context = f"\n\n## OCR FAILURE DETECTED\nThe last document upload failed with reason: '{ocr_error}'.\nPlease explain this gently to the user and suggest tips (e.g. better lighting, flat surface, no glare) instead of just saying 'Error'."

    existing_terms = state.get("loan_terms", {}) or {}
    principal = existing_terms.get("principal", 0) or 0
    tenure = existing_terms.get("tenure", 0) or 0
    rate_pa = float(existing_terms.get("rate", 12.0) or 12.0)
    pending_q = state.get("pending_question")
    user_clean = (user_msg or "").strip().lower()
    
    # ─── DETECT RE-NEGOTIATION (User asking for lower amount after rejection) ────
    decision = state.get("decision", "")
    is_renegotiating = decision in ("hard_reject", "soft_reject") and any(
        kw in user_clean for kw in ["lower", "less", "smaller", "different", "another", "reduce"]
    )
    
    if is_renegotiating:
        # Reset loan amount to re-collect from user
        principal = 0
        tenure = 0
        log.append("🔄 Re-assessment triggered. Adjusting application parameters for optimal fit.")
    
    # Accumulate updates
    final_updates = {
        "loan_terms": {
            **existing_terms,
            "principal": principal,
            "tenure": tenure,
            "rate": rate_pa,
            "loan_purpose": existing_terms.get("loan_purpose"), # Initialize with existing, will be updated
            "loan_type": existing_terms.get("loan_type", "personal") # Initialize with existing, will be updated
        },
        "customer_data": customer_context,
        "current_phase": "sales",
        "decision": "" if is_renegotiating else decision  # Clear decision when re-negotiating
    }

    # Always call LLM to ensure human conversation
    llm = get_master_llm()
    messages = [
        SystemMessage(content=SALES_CLOSER_PROMPT + (ocr_context if ocr_context else "")),
        SystemMessage(content=f"## CUSTOMER PROFILE\n{_build_customer_context(customer_context)}"),
        SystemMessage(content=f"## LOAN PRODUCTS\n{_build_products_info()}")
    ]
    
    # Add recent history for context
    for msg in history[-5:]: # Last 5 turns for focus
        role = HumanMessage if msg["role"] == "user" else AIMessage
        messages.append(role(content=msg["content"]))
    
    messages.append(HumanMessage(content=user_msg))
    
    log.append("🧠 Conversing with customer...")
    response = await llm.ainvoke(messages)
    reply = response.content
    extracted = _extract_json_from_response(reply)
    
    # Clean up the visible reply
    visible_reply = _re.sub(r"```json\s*\{.*?\}\s*```", "", reply, flags=_re.DOTALL).strip()
    
    updates = {
        "action_log": log,
        "current_phase": "sales",
        "decision": decision
    }
    
    if extracted:
        # Update loan terms if LLM extracted new values
        new_terms = {**existing_terms}
        if extracted.get("loan_amount"): new_terms["principal"] = float(extracted.get("loan_amount"))
        if extracted.get("tenure"): new_terms["tenure"] = int(extracted.get("tenure"))
        if extracted.get("loan_purpose"): new_terms["loan_purpose"] = extracted.get("loan_purpose")
        if extracted.get("loan_type"): new_terms["loan_type"] = extracted.get("loan_type")
        
        # Calculate EMI if we have principal and tenure
        if new_terms.get("principal") and new_terms.get("tenure"):
            rate = float(new_terms.get("rate", 12.0))
            new_terms["emi"] = _calc_emi(new_terms["principal"], rate, new_terms["tenure"])
        
        updates["loan_terms"] = new_terms
        updates["options"] = extracted.get("options", ["Apply now", "Tell me more", "Exit"])
        
        if extracted.get("confirmed") is True:
            updates["intent"] = "loan"
            updates["current_phase"] = "kyc_verification"
            updates["loan_confirmed"] = True
            log.append(f"✅ Terms confirmed: ₹{new_terms.get('principal'):,.0f} for {new_terms.get('tenure')} months.")
    else:
        updates["options"] = ["I'm interested", "Tell me more", "Exit"]

    updates["messages"] = [AIMessage(content=visible_reply)]

    await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
    
    # Ensure current_phase is set
    if "current_phase" not in updates:
        updates["current_phase"] = "sales"
    
    # Save session to MongoDB
    try:
        SessionManager.save_session(session_id, updates)
        print(f"💾 Session {session_id} saved to MongoDB")
    except Exception as e:
        print(f"⚠️ Failed to save session: {e}")
    
    return updates