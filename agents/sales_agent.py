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


SALES_CLOSER_PROMPT = """You are Arjun, the Senior Loan Specialist at FinServe NBFC. Your primary objective is to help the customer select the right loan product and finalize the terms (Amount & Tenure) for their application.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR CORE RESPONSIBILITIES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **Product Selection**: Help the user pick between Personal, Education, Business, or Home loans.
2. **Limit Enforcement**: Our hard policy is **MAX 2× Pre-Approved Limit**. If they ask for more, warn them it requires manual underwriting and might be rejected.
3. **Structured Capture**: Once the user agrees on Amount, Tenure, and Rate, you MUST generate the JSON block to record the lead.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 🚫 STRICT BOUNDARIES (ANTI-HALLUCINATION):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **NO WELLNESS ADVICE**: Do NOT give advice on ROI savings, debt-to-income ratios, or wealth management. If the user asks "Is this a good rate?" or "How can I save money?", say: "Our Financial Advisor can help you with wealth strategies once we've captured your loan preference."
- **NO ROI MATH**: Do NOT explain the internal logic of how rates are calculated. Use the base rates provided in the product catalog.
- **NO GUARANTEES**: Never "guarantee" approval. Say "based on your profile, this looks like a strong application."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## JSON OUTPUT (Mandatory)
When the user says 'Yes' or 'Apply' to specific terms (Amount, Tenure, Rate), you MUST end your reply with EXACTLY this JSON block on a NEW LINE:
```json
{{ "loan_type": "<personal/education/business/home>", "loan_amount": <number>, "tenure": <months>, "interest_rate": <rate_number>, "confirmed": true }}
```

**⚠️ IMPORTANT**: NEVER output only the JSON block. ALWAYS provide a friendly, professional confirmation message first.
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
    import re as _re
    print("🗣️ [SALES AGENT] Processing turn...")
    log = list(state.get("action_log") or [])
    log.append("💬 Generating response from Advisor Agent")
    from langchain_core.messages import HumanMessage, AIMessage
    
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

    res = await sales_chat_response(
        user_message=user_msg,
        chat_history=history[:-1] if history else [],
        customer=customer_context
    )
    
    # ── Robust JSON stripping ─────────────────────────────────────────────
    # We strip any block that looks like JSON to keep the chat clean.
    visible_reply = _re.sub(r"```json\s*\{.*?\}\s*```", "", res["reply"], flags=_re.DOTALL).strip()
    # Strip any lines that are just JSON-like (starting with { and ending with })
    visible_reply = _re.sub(r"\{[\s\n]*\".*?\}", "", visible_reply, flags=_re.DOTALL).strip()
    visible_reply = _re.sub(r"^\{.*?\}$", "", visible_reply, flags=_re.MULTILINE | _re.DOTALL).strip()
    
    # Fallback if reply was ONLY JSON or empty
    if not visible_reply or visible_reply.strip() in ["{}", "[]", "None"]:
        visible_reply = "I've processed your request. Does this look correct to you?"


    # If the agent confirmed a loan, append a clean confirmation line
    extracted = res.get("extracted")
    if extracted and extracted.get("loan_amount") and "offer" not in visible_reply.lower():
        amount = extracted.get("loan_amount", 0)
        tenure = extracted.get("tenure", 0)
        rate   = extracted.get("interest_rate", 0)
        log.append(f"✅ Loan terms captured: ₹{amount:,.0f} @ {rate}%")
        visible_reply = (
            visible_reply
            + f"\n\n✅ **Loan offer ready!** ₹{amount:,.0f} @ {rate}% for {tenure} months."
        )


    
    # ── Memory Enhancement: Detect what we just asked ──────────────────────
    pending = None
    if "why" in visible_reply.lower() and "need" in visible_reply.lower():
        pending = "loan_purpose"
    elif "how much" in visible_reply.lower() or "amount" in visible_reply.lower():
        pending = "loan_amount"
    elif "tenure" in visible_reply.lower() or "months" in visible_reply.lower():
        pending = "tenure"
    
    updates = {
        "messages": [AIMessage(content=visible_reply)], 
        "action_log": log, 
        "current_phase": "loan_application",
        "pending_question": pending
    }
    
    if extracted and (extracted.get("loan_amount") or extracted.get("confirmed")):
        print(f"  → Loan Captured/Proposed: {extracted}")
        updates["loan_terms"] = {
            "principal": float(extracted.get("loan_amount", 0)),
            "rate":      float(extracted.get("interest_rate", 12.0)),
            "tenure":    int(extracted.get("tenure", 24)),
            "loan_type": extracted.get("loan_type", "personal"),
        }
        updates["options"] = ["Yes", "No"] # Surfacing buttons for proposal or confirmation
        
        if extracted.get("confirmed"):
            updates["intent"] = "loan_confirmed"
            updates["current_phase"] = "emi_computation"
            updates["pending_question"] = None 

    return updates
