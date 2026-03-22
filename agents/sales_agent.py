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


# ─── System prompt ─────────────────────────────────────────────────────────────
ADVISOR_SYSTEM_PROMPT = """You are Arjun, a Senior Financial Advisor and Relationship Manager at FinServe NBFC.

Your Goal: Help the customer find the BEST financial solution. Do NOT just sell a loan.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR WORKFLOW — AGENTIC STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### STEP 1: UNDERSTAND THE NEED (Mandatory)
When the user asks for a loan, you MUST first ask "Why do you need this loan?". 
Listen for reasons like:
- Personal/Medical/Wedding (Personal Loan)
- Education/Fees (Student Loan)
- Business expansion (Business Loan)
- Home renovation (Home Loan)

### STEP 2: PROVIDE ADVICE
Based on their reason AND their profile (credit score/salary), recommend a specific product.
- If credit score is low, explain how that affects their rate.
- Suggest alternatives (like a Gold Loan) if their credit score is a barrier.

### STEP 3: CAPTURE TERMS
Once the product is agreed upon, discuss Amount and Tenure.
- **CRITICAL POLICY**: Our maximum exposure is capped at **2× the Pre-Approved Limit**.
- If a user asks for more than 2× their limit, you MUST warn them that it will likely be rejected or require exceptional manual review.
- Suggest a "Sweet Spot" amount (equal to or less than their Pre-Approved Limit) for faster approval.

ONLY when the user explicitly says "Confirm" or "Apply now" with the specific terms, output the JSON block.

### JSON OUTPUT (Mandatory when confirmed)
When details are FINALIZED and the user says 'Yes' to the offer, end your reply with EXACTLY this JSON:
```json
{{ "loan_type": "<personal/education/business/home>", "loan_amount": <number>, "tenure": <months>, "interest_rate": <rate_number>, "confirmed": true }}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## BEHAVIORAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Be conversational. Use phrases like "I understand", "That makes sense", "Here's what I suggest".
- Use ₹ symbol with comma formatting.
- Reference the customer's specific numbers (salary, credit score, pre-approved limit) directly in your response.
- If they are a returning customer, greet them by name.
- **NEVER** promise 100% approval if the amount exceeds 2× the limit.
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
        SystemMessage(content=ADVISOR_SYSTEM_PROMPT),
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
    
    # ── Strip raw JSON block from user-visible reply ──────────────────────
    # The JSON is for internal extraction only — users should see clean prose
    visible_reply = _re.sub(r"```json\s*\{.*?\}\s*```", "", res["reply"], flags=_re.DOTALL).strip()
    
    # If the agent confirmed a loan, append a clean confirmation line
    extracted = res.get("extracted")
    if extracted and extracted.get("confirmed"):
        amount = extracted.get("loan_amount", 0)
        tenure = extracted.get("tenure", 0)
        rate   = extracted.get("interest_rate", 0)
        log.append(f"✅ Loan terms captured: ₹{amount:,.0f} @ {rate}%")
        visible_reply = (
            visible_reply
            + f"\n\n✅ **Loan offer locked in!** ₹{amount:,.0f} @ {rate}% for {tenure} months. "
            "Shall we proceed with document verification?"
        )
    
    updates = {"messages": [AIMessage(content=visible_reply)], "action_log": log, "current_phase": "loan_application"}
    
    if extracted and extracted.get("confirmed"):
        print(f"  → Loan Captured: {extracted}")
        updates["loan_terms"] = {
            "principal": float(extracted.get("loan_amount", 0)),
            "rate":      float(extracted.get("interest_rate", 12.0)),
            "tenure":    int(extracted.get("tenure", 24)),
            "loan_type": extracted.get("loan_type", "personal"),
        }
        updates["intent"] = "loan_confirmed"
        updates["current_phase"] = "emi_computation"
    
    return updates