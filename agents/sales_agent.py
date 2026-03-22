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

# ─── Keyword-based apply intent (NO LLM call) ────────────────────────────────
APPLY_KEYWORDS = {
    "yes", "apply", "proceed", "go ahead", "go", "sure", "let's do it",
    "lets do it", "yep", "yeah", "yup", "haan", "haan ji", "ok", "okay",
    "confirm", "book", "start", "i want to apply", "want to apply", "apply now",
    "chalte hain", "karo", "proceed karo", "han", "bilkul", "absolutely",
    "definitely", "of course", "sounds good", "let's go", "lets go"
}

def detect_apply_intent(text: str) -> bool:
    """Returns True if user clearly wants to apply for a loan. Zero LLM cost."""
    cleaned = text.strip().lower()
    if cleaned in APPLY_KEYWORDS:
        return True
    if len(cleaned) < 60:
        return any(kw in cleaned for kw in APPLY_KEYWORDS)
    return False


SALES_CLOSER_PROMPT = """You are Arjun, the Senior Lead Specialist at FinServe NBFC. Your mission is to help customers navigate their financial journey and find the perfect loan solution.

You are NOT just a salesperson; you are a Financial Discovery expert.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR CORE OBJECTIVES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **Financial Discovery**: Understand the *why* behind the loan. If it's for a family trip, talk about the memories. If for business, talk about growth.
2. **EMI Simulation**: Be proactive. Say things like: "For a ₹5 Lakh loan over 3 years, your EMI would be roughly ₹16,607. Does that fit your monthly budget?"
3. **What-If Scenarios**: Offer options. "If we increase the tenure to 48 months, the EMI drops to ₹13,000. Would you prefer lower monthly outgo?"
4. **Structured Capture**: Once the user agrees on terms, generate the JSON block.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 🚫 POLICY BOUNDARIES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **MAX LIMIT**: If requested amount > 2× Pre-Approved Limit, explain that this moves them into 'High-Value Underwriting' which takes 24 hours more.
- **NO GUARANTEES**: Use words like "High probability of approval" or "Strong profile fit".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## JSON OUTPUT (Mandatory)
When terms are agreed, output exactly this JSON block:
```json
{{ "loan_type": "personal/education/business/home", "loan_amount": <number>, "tenure": <months>, "interest_rate": <number>, "confirmed": true }}
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
    
    # Enhanced Memory
    past_records = customer.get("past_records", "No previous recorded interactions.")
    drop_offs = customer.get("drop_off_history", "None recorded.")
    intent = customer.get("intent", "Checking options")

    return (
        f"Customer Name: {name} | City: {city}\n"
        f"Monthly Salary: ₹{salary:,}/month\n"
        f"CIBIL / Credit Score: {score}\n"
        f"Pre-Approved Loan Limit: ₹{limit:,}\n"
        f"Existing Monthly EMI Burden: ₹{emi_total:,}/month\n"
        f"Active Loans: {', '.join(loans) if loans else 'None'}\n"
        f"Past Interactions/Sanctions: {past_records}\n"
        f"Previous Drop-off Points: {drop_offs}\n"
        f"Current Session Intent: {intent}"
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

    # Use the refined prompt
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
            "loan_type": extracted.get("loan_type", "personal"),
        }
        log.append(f"📊 Calculated Scenario: ₹{amount:,.0f} for {tenure} months")

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
            
            updates["messages"] = [AIMessage(content=json.dumps({
                "type": "emi_slider",
                "content": visible_reply + slider_msg
            }))]
            
            updates["intent"] = "loan"
            updates["current_phase"] = "kyc_verification"
            log.append("✅ Terms confirmed. Moving to KYC.")
        else:
            updates["messages"] = [AIMessage(content=visible_reply)]
    else:
        updates["messages"] = [AIMessage(content=visible_reply)]

    await manager.broadcast_thinking(session_id, "Arjun (Sales)", False)
    return updates