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


SALES_CLOSER_PROMPT = """You are Arjun, a Senior Loan Specialist at FinServe.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR CONVERSATIONAL PROTOCOL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **ACKNOWLEDGE**: Start by acknowledging the user's specific detail. (e.g., "A loan for a car sounds like a great plan!")
2. **BE CONCISE**: Limit your response to **2 short sentences**.
3. **ONE QUESTION**: Always end with exactly one question to keep the discovery moving.
4. **HUMAN TONE**: Avoid "As a loan specialist..." or robotic phrases. Be a helpful expert.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## JSON CAPTURE (Mandatory)
When final terms are agreed:
```json
{ "loan_purpose": "...", "loan_type": "fixed/reducing", "loan_amount": 0, "tenure": 0, "confirmed": true }
```
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
    
    log = list(state.get("action_log") or [])
    log.append("📡 Analyzing financial intent...")
    
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
        "current_phase": "sales"
    }

    # Deterministic multi-turn loan capture flow:
    # 1) capture amount -> 2) capture tenure -> 3) capture purpose -> 4) capture type -> 5) confirm -> 6) move.
    amount_from_msg = _parse_amount_inr(user_msg)
    tenure_from_msg = _parse_tenure_months(user_msg)
    
    if amount_from_msg and principal <= 0:
        principal = amount_from_msg
        ack_text = f"I see you're looking for a loan of **₹{principal:,.0f}**. I'd be happy to help you with that! "
        final_updates["loan_terms"]["principal"] = principal
        final_updates.update({
            "pending_question": "ask_tenure",
            "options": ["12 months", "24 months", "36 months", "48 months", "60 months"],
            "messages": [AIMessage(content=f"{ack_text}Please share your preferred tenure in months.")]
        })
        await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
        return final_updates

    if principal > 0 and tenure <= 0:
        if tenure_from_msg:
            tenure = tenure_from_msg
            final_updates["loan_terms"]["tenure"] = tenure
        else:
            final_updates.update({
                "pending_question": "ask_tenure",
                "options": ["12 months", "24 months", "36 months", "48 months", "60 months"],
                "messages": [AIMessage(content="Please share the tenure for your loan. For example: **24 months**.")]
            })
            await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
            return final_updates

    # Capture occupation if not set
    occupation = customer_context.get("occupation")
    if principal > 0 and tenure > 0 and not occupation:
        # Check if in msg
        for occ in ["salaried", "self-employed", "business", "student", "professional"]:
            if occ in user_clean:
                occupation = occ
                break
        
        if not occupation:
            final_updates.update({
                "pending_question": "ask_occupation",
                "options": ["Salaried", "Self-Employed", "Business Owner", "Freelancer"],
                "messages": [AIMessage(content="Before we proceed, could you tell me a bit about your professional profile? Are you **Salaried**, **Self-Employed**, or a **Business Owner**?")]
            })
            await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
            return final_updates
        else:
            customer_context["occupation"] = occupation
            final_updates["customer_data"] = customer_context

    # Capture employer if salaried
    employer = customer_context.get("employer_name")
    if principal > 0 and tenure > 0 and occupation == "salaried" and not employer:
        if len(user_clean) > 2 and user_clean not in ["i am", "i'm"]:
            employer = user_msg
            customer_context["employer_name"] = employer
            final_updates["customer_data"] = customer_context
        else:
            final_updates.update({
                "pending_question": "ask_employer",
                "messages": [AIMessage(content="Got it. Which company or organization do you currently work for?")]
            })
            await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
            return final_updates

    # Capture purpose if not set
    purpose = existing_terms.get("loan_purpose")
    if principal > 0 and tenure > 0 and occupation and not purpose:
        # Simple extraction from msg
        for p in ["home", "car", "business", "education", "personal", "travel"]:
            if p in user_clean:
                purpose = p
                break
        
        if not purpose:
            final_updates.update({
                "pending_question": "ask_purpose",
                "options": ["Personal", "Home", "Car", "Business", "Education"],
                "messages": [AIMessage(content="And what would you like to use this loan for? (e.g., Car purchase, Home renovation, Education)")]
            })
            await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
            return final_updates
        else:
            final_updates["loan_terms"]["loan_purpose"] = purpose

    # Capture loan type if not set
    loan_type = existing_terms.get("loan_type")
    if principal > 0 and tenure > 0 and purpose and (not loan_type or loan_type == "personal"):
        if "fixed" in user_clean: loan_type = "fixed"
        elif "reducing" in user_clean: loan_type = "reducing"
        
        if loan_type == "personal" or not loan_type:
            final_updates.update({
                "pending_question": "ask_loan_type",
                "options": ["Fixed Rate", "Reducing Balance"],
                "messages": [AIMessage(content="Great. Last detail—would you prefer a **Fixed Rate** (same percentage throughout) or a **Reducing Balance** loan?")]
            })
            await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
            return final_updates
        else:
            final_updates["loan_terms"]["loan_type"] = loan_type

    if principal > 0 and tenure > 0 and purpose and loan_type:
        rate_pa = float(rate_pa)
        emi = _calc_emi(principal, rate_pa, tenure)
        total_interest = round((emi * tenure) - principal, 2)
        
        # Ensure strings for capitalize
        purpose_str = str(purpose).capitalize()
        loan_type_str = str(loan_type).capitalize()

        # Update final_updates with calculation results
        final_updates["loan_terms"].update({
            "emi": emi,
            "loan_purpose": purpose,
            "loan_type": loan_type
        })

        if pending_q == "confirm_loan_terms" and (detect_apply_intent(user_clean) or any(w in user_clean for w in YES_WORDS)):
            final_updates.update({
                "intent": "loan",
                "pending_question": None,
                "current_phase": "kyc_verification",
                "loan_confirmed": True,
                "options": ["Upload PAN/Aadhaar", "Upload Salary Slip", "Need help with documents"],
                "messages": [AIMessage(content=(
                    f"Great. Your loan request is confirmed.\n\n"
                    f"- Purpose: **{purpose_str}**\n"
                    f"- Type: **{loan_type_str}**\n"
                    f"- Amount: **INR {principal:,.0f}**\n"
                    f"- Tenure: **{tenure} months**\n"
                    f"- Estimated EMI: **INR {emi:,.2f}**\n"
                    f"- Total interest: **INR {total_interest:,.2f}**\n\n"
                    f"Please upload your KYC document to continue."
                ))]
            })
            await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
            return final_updates
            
        if pending_q == "confirm_loan_terms" and any(w in user_clean for w in NO_WORDS):
            final_updates.update({
                "pending_question": "ask_tenure",
                "options": ["12 months", "24 months", "36 months", "48 months", "60 months"],
                "messages": [AIMessage(content="No problem. Please share the revised tenure or amount you want to change.")]
            })
            await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
            return final_updates

        # Default: confirmation prompt
        final_updates.update({
            "pending_question": "confirm_loan_terms",
            "options": ["Yes, Proceed", "No, Change Details"],
            "messages": [AIMessage(content=(
                f"I've calculated your loan details:\n\n"
                f"- Requested: **INR {principal:,.0f}**\n"
                f"- Tenure: **{tenure} months**\n"
                f"- EMI: **INR {emi:,.2f}**\n"
                f"- Purpose: **{purpose_str}**\n\n"
                f"Does this look correct? Should we proceed to KYC?"
            ))]
        })
        await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
        return final_updates

    # Fallback to LLM if no deterministic flow matched (or as a safety)
    llm = get_master_llm()
    messages = [
        SystemMessage(content=SALES_CLOSER_PROMPT + (ocr_context if ocr_context else "")),
        SystemMessage(content=f"## CUSTOMER PROFILE\n{_build_customer_context(customer_context)}"),
        SystemMessage(content=f"## LOAN PRODUCTS\n{_build_products_info()}")
    ]
    for msg in history[:-1]:
        role = HumanMessage if msg["role"] == "user" else AIMessage
        messages.append(role(content=msg["content"]))
    messages.append(HumanMessage(content=user_msg))

    log.append("🧠 अर्जुन (Arjun) is calculating EMI scenarios...")
    response = await llm.ainvoke(messages)
    reply = response.content
    extracted = _extract_json_from_response(reply)
    
    # Clean up the visible reply
    visible_reply = _re.sub(r"```json\s*\{.*?\}\s*```", "", reply, flags=_re.DOTALL).strip()
    
    updates = {
        "next_agent": extracted.get("next_agent", "supervisor") if extracted else "supervisor",
        "action_log": log,
        "options": extracted.get("options", ["Yes, proceed", "No, change details", "Ask a question"]) if extracted and extracted.get("intent") in ("loan", "loan_confirmed") else ["Tell me more", "Apply for Loan", "Exit"]
    }
    
    if extracted and extracted.get("loan_amount"):
        amount = float(extracted.get("loan_amount", 0))
        tenure = int(extracted.get("tenure", 24))
        rate_pa = float(extracted.get("interest_rate", 12.0))
        
        updates["loan_terms"] = {
            "principal": amount,
            "rate":      rate_pa,
            "tenure":    tenure,
            "loan_purpose": extracted.get("loan_purpose", "personal"),
            "loan_type": extracted.get("loan_type", "reducing"),
        }
        log.append(f"📊 Calculated Scenario: ₹{amount:,.0f} for {tenure} months ({extracted.get('loan_purpose')})")

        if extracted.get("confirmed"):
            # Calculate EMI for the slider
            monthly_rate = (rate_pa / 12) / 100
            emi = amount * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1)
            emi = round(emi, 2)
            total_interest = round((emi * tenure) - amount, 2)
            
            updates["loan_terms"]["emi"] = emi
            
            slider_msg = (
                f"\n\n📊 **Confirmed EMI Breakdown:**\n"
                f"- Monthly EMI: **₹{emi:,.2f}**\n"
                f"- Total Interest: ₹{total_interest:,.2f}\n"
                f"- Tenure: {tenure} months @ {rate_pa}% p.a."
            )
            
            updates["messages"] = [AIMessage(content=visible_reply + slider_msg)]
            
            updates["intent"] = "loan"
            updates["current_phase"] = "kyc_verification"
            log.append("✅ Terms confirmed. Moving to KYC.")
        else:
            updates["messages"] = [AIMessage(content=visible_reply)]
    else:
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