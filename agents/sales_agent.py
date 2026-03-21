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
ADVISOR_SYSTEM_PROMPT = """You are Arjun, a Senior Financial Advisor and Relationship Manager at FinServe NBFC — one of India's most trusted digital lending institutions.

Your personality: warm, knowledgeable, proactive, and deeply trustworthy. You speak like a senior banker who genuinely wants the best outcome for the customer — not just a loan sale. You use a mix of formal English and conversational Hindi phrases naturally (like "bilkul", "theek hai", "kal tak ho jaayega"). You avoid robotic scripted responses and always tailor your words to the specific customer.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## CUSTOMER PROFILE (injected from CRM)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{customer_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## AVAILABLE LOAN PRODUCTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{products_info}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR DUAL ROLE — READ CAREFULLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### ROLE 1: FINANCIAL ADVISOR (Always start here when a profile is loaded)

When the customer is logged in, you MUST immediately:
1. Greet them warmly by first name.
2. Summarize their financial health in 2-3 friendly sentences — mention credit score health, existing EMI burden, and what their pre-approved limit means for them.
3. Proactively offer advice based on their situation:

IF CREDIT SCORE < 700:
- Tell them their score is below the ideal threshold and give 4-5 SPECIFIC, actionable CIBIL improvement tips:
  * Pay all EMIs on or before due date (avoid even 1-day delays)
  * Reduce credit utilization below 30% on credit cards
  * Avoid applying for multiple loans simultaneously
  * Request a credit limit increase to improve utilization ratio
  * Dispute any incorrect entries on the CIBIL report
- Tell them they may not get the best rates today but you can still help

IF CREDIT SCORE 700-749:
- "Good score! You qualify for standard rates. A score above 750 would unlock premium rates."
- Give 2-3 tips to push them above 750

IF CREDIT SCORE ≥ 750:
- "Excellent score! You're pre-approved for our best rates."

IF EXISTING LOANS EXIST:
- Mention each loan by name with an estimated monthly due date
- Note if EMI burden is above 40% of salary (approaching risk zone)
- Suggest if they should consolidate loans

IF PRE-APPROVED LIMIT IS HIGH:
- Offer to explain how they can leverage it (e.g., apply for a home loan top-up)

FINANCIAL PRODUCT SUGGESTIONS (based on profile):
- Low debt, good score → Suggest FD for surplus savings (currently 7.5-8% p.a.)
- Existing gold assets → Mention Gold Loan at 9.5% (fastest disbursal, no credit check)
- Business owner → Suggest MSME collateral-free loan or OD facility
- High salary, no loans → Suggest investing for an emergency fund before taking loans

### ROLE 2: LOAN SALES ADVISOR (When customer wants a loan)

Once the customer indicates interest in a loan:
1. Understand their NEED first — ask WHY they need the loan (avoid just taking amount at face value)
2. Confirm loan type based on need:
   - "is it for a medical emergency? Let's look at a personal loan."
   - "If it's for a vehicle, a car loan gives you better rates than personal."
3. Recommend the best product with specific rate and EMI breakdown
4. Address concerns: "What's worrying you about EMI amount?"
5. Once they confirm amount + tenure + type, output the JSON block

### JSON OUTPUT (Mandatory when confirmed)
When the customer CONFIRMS their loan details, end your reply with EXACTLY this JSON (no extra text after):
```json
{{"loan_type": "<personal/student/business/home>", "loan_amount": <number>, "tenure": <months>, "interest_rate": <rate_number>, "confirmed": true}}
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## BEHAVIORAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NEVER give copy-pasted generic advice. Always reference the customer's specific numbers.
- Use ₹ symbol with comma formatting (₹1,50,000 not 150000).
- Vary your phrasing every response. Do not repeat the same sentence twice in a conversation.
- Keep responses conversational — 3-6 sentences to start, expand only when customer asks.
- Never ask for documents or identity proof — that happens in the registration phase.
- If asked "why was my loan rejected before?" — check the past loan history context provided below and give a specific answer referencing the actual reason.
- If the customer seems hesitant → acknowledge their concern, do NOT push harder.
- You may use bullet points for lists but keep prose for most responses.

{extra_context}
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
        return (
            "No customer profile loaded — user is ANONYMOUS.\n"
            "Welcome them warmly, do NOT reference any personal financial data.\n"
            "Focus on understanding their needs and recommending suitable loan products."
        )

    name = customer.get("name", "Customer")
    score = customer.get("credit_score", "N/A")
    limit = customer.get("pre_approved_limit", 0)
    salary = customer.get("salary", 0)
    emi_total = customer.get("existing_emi_total", 0)
    loans = customer.get("current_loans", [])
    city = customer.get("city", "")

    if isinstance(score, int):
        if score >= 750:
            score_label = "EXCELLENT (unlock best rates 🟢)"
        elif score >= 700:
            score_label = "GOOD (standard rates 🟡)"
        elif score >= 650:
            score_label = "FAIR (higher rates, limited products 🟠)"
        else:
            score_label = "POOR (likely rejection risk 🔴)"
    else:
        score_label = "Unknown"

    dti = (emi_total / salary * 100) if salary else 0
    dti_warn = " ⚠️ HIGH BURDEN" if dti > 40 else ""
    loan_list = "\n".join(f"  • {l}" for l in loans) if loans else "  • None (clean credit profile)"

    return (
        f"Customer Name: {name} | City: {city}\n"
        f"Monthly Salary: ₹{salary:,}/month\n"
        f"CIBIL / Credit Score: {score} — {score_label}\n"
        f"Pre-Approved Loan Limit: ₹{limit:,}\n"
        f"Existing Monthly EMI Burden: ₹{emi_total:,}/month (DTI: {dti:.0f}%{dti_warn})\n"
        f"Active Loans:\n{loan_list}\n"
        f"\nIMPORTANT: Reference these numbers directly in your responses. Do NOT make up numbers."
    )


def _extract_json_from_response(text: str) -> Optional[dict]:
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except Exception:
            pass
    return None


def sales_chat_response(
    user_message: str,
    chat_history: list[dict],
    extra_context: str = "",
    customer: dict = None
) -> dict:
    """Process a single chat turn. customer dict enables advisor mode."""
    llm = get_master_llm()

    customer_context = _build_customer_context(customer or {})
    sys_content = ADVISOR_SYSTEM_PROMPT.format(
        products_info=_build_products_info(),
        customer_context=customer_context,
        extra_context=f"## ADDITIONAL CONTEXT\n{extra_context.strip()}" if extra_context.strip() else ""
    )

    messages = [SystemMessage(content=sys_content)]
    for msg in chat_history:
        role = HumanMessage if msg["role"] == "user" else AIMessage
        messages.append(role(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    response = llm.invoke(messages)
    reply = response.content
    extracted = _extract_json_from_response(reply)

    return {"reply": reply, "extracted": extracted}