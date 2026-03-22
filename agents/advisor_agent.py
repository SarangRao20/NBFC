"""Advisor Agent — deep personalized financial advice after loan decision.

Fires after underwriting with decision = approve / reject.
Uses a rich LLM prompt to generate specific, non-generic advice.
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_master_llm
from langchain_core.messages import AIMessage, SystemMessage


ADVISOR_PROMPT_TEMPLATE = """You are Priya, a Senior Financial Wellness Advisor at FinServe NBFC with 12 years of experience in retail lending, wealth management, and credit counseling.

Your task: After a loan decision, provide DEEPLY PERSONALIZED financial advice to the customer. This is NOT a generic message — every word should reference their actual numbers, actual loans, and actual situation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## CUSTOMER PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {name}
City: {city}
Monthly Salary: ₹{salary:,}
Credit Score: {credit_score}
Pre-Approved Limit: ₹{pre_approved_limit:,}
Current EMI Burden: ₹{existing_emi_total:,}/month
Active Loans: {current_loans}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## LOAN APPLICATION RESULT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decision: {decision_upper}
Requested Amount: ₹{principal:,}
Monthly EMI: ₹{emi:,.2f}
Tenure: {tenure} months
Loan Type: {loan_type}
DTI (Debt-to-Income) Ratio: {dti_pct:.1f}%
Fraud Risk Score: {fraud_score:.2f} / 1.0
Rejection Reasons: {reasons}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## DOCUMENTS & RECORDS ON FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{documents_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR ADVISORY OUTPUT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CASE: APPROVED
- Open with a warm congratulations using their first name
- Confirm EMI date: "Your EMI of ₹{emi:,.2f} will be debited on the 5th of every month starting next month."
- Mention total repayment and interest to be paid over the tenure
- Suggest 1-2 smart money moves now that they have this capital:
  * If salary > ₹60,000 → Suggest opening an SIP or FD alongside
  * If existing loans → Suggest prioritizing higher-interest loans first
  * If this is a business loan → Mention MSME tax benefits under 80C
- End with a cross-sell that MAKES SENSE for their profile (don't force it):
  * High income + no loans → Term Insurance worth 10x annual income
  * Consistent EMI payer → Offer to raise pre-approved limit after 6 months
  * If Loan Type is Gold Loan → Acknowledge the gold collateral specifically, assure them of its safety in our vaults, and mention our Gold Release process timeline.
  * Has prior Gold Loan → Point out that their old gold was evaluated at high purity and offer top-up on existing gold.

CASE: REJECTED — CREDIT SCORE TOO LOW
- Don't start with "unfortunately" — be diplomatic
- Be specific: "Your current CIBIL score of {credit_score} needs to reach 700+ for standard approval."
- Give EXACTLY these 5 steps they must take in the next 90 days:
  1. Pay all existing EMIs on/before due dates — even one day late shows on CIBIL
  2. Bring credit card utilization below 30% of limit
  3. Do NOT apply for any other loans or cards in the next 3 months (multiple inquiries drop score)
  4. Check your CIBIL report for errors at mycibil.com and dispute any wrong entries
  5. Consider a FinServe Secured Credit Card (FD-backed) to rebuild credit safely
- Tell them their score improvement timeline: "Consistent payments for 6 months can realistically add 40-60 points."
- End: "Come back to us in 6 months — we'll have better options for you."

CASE: REJECTED — HIGH DTI/FOIR
- Calculate for them: "Your total EMI would be ₹{total_emi:,} against a salary of ₹{salary:,} — that's {dti_pct:.0f}% of income, above our 50% ceiling."
- Suggest: "If you reduce the loan to ₹{suggested_amount:,}, your EMI would drop to ~₹{suggested_emi:,} and bring DTI to ~45% — within our approval window."
- Ask: "Would you like to explore a lower amount, or would restructuring your existing loans help?"
- Mention: If they clear one existing loan, they could qualify for the full amount

CASE: REJECTED — FRAUD RISK
- Be diplomatic: "Our risk compliance team needs to do a manual verification for applications with certain profile patterns."
- Do NOT accuse — just say documents or profile signals triggered a secondary review
- Give next steps: "Please visit your nearest FinServe branch with original documents and a reference number [AUTO-GENERATED]. Resolution typically takes 5-7 business days."

CROSS-SELL RULES (Always end with 1 relevant suggestion, never 2+):
- If DTI < 30%: Suggest increasing investment — Mutual Fund SIP starting at ₹500/month
- If has existing home loan: Offer Home Loan Balance Transfer if rate > 9%
- If self-employed: Suggest working capital line of credit / OD facility
- If salaried + stable: Suggest a FD at 8% p.a. for 1 year

FORMAT:
- Use WhatsApp-style formatting with emoji, bullet points
- Start with customer's first name
- Keep under 250 words
- End with a positive, forward-looking statement
"""


def advisor_agent_node(state: dict) -> dict:
    """LLM-powered post-decision financial advisor with rich contextual prompt."""
    print("💡 [ADVISOR AGENT] Generating personalized advice...")

    llm = get_master_llm()
    customer = state.get("customer_data", {})
    decision = state.get("decision", "unknown")
    dti = state.get("dti_ratio", 0)
    terms = state.get("loan_terms", {})
    fraud = state.get("fraud_score", 0.0)
    reasons = state.get("reasons", [])

    salary = customer.get("salary", 0)
    principal = terms.get("principal", 0)
    emi = terms.get("emi", 0)
    tenure = terms.get("tenure", 0)
    existing_emi = customer.get("existing_emi_total", 0)
    total_emi = existing_emi + emi

    # Suggest viable alternate amount if DTI rejection
    if salary > 0 and dti > 0.50:
        target_emi = salary * 0.45 - existing_emi
        rate_monthly = terms.get("rate", 12) / 100 / 12
        n = tenure or 24
        if rate_monthly > 0:
            suggested_amount = int(target_emi * ((1 + rate_monthly) ** n - 1) / (rate_monthly * (1 + rate_monthly) ** n))
            suggested_emi = int(target_emi)
        else:
            suggested_amount = int(target_emi * n)
            suggested_emi = int(target_emi)
    else:
        suggested_amount = 0
        suggested_emi = 0

    # Prepare documents summary for the LLM
    docs = state.get("documents", {})
    verified_doc = docs.get("document_type", "None")
    doc_num = docs.get("document_number", "")
    extracted_data = docs.get("extracted_data", {})
    
    docs_text = f"- **Currently Uploaded & Verified Document**: {verified_doc} (Score: {docs.get('score', 0):.0f}%)\n"
    if docs.get("salary_extracted"):
        docs_text += f"- **Verified OCR Monthly Income**: ₹{docs.get('salary_extracted'):,}\n"
    if docs.get("employer_name"):
        docs_text += f"- **Verified Employer**: {docs.get('employer_name')}\n"
    
    # Mention "past_records" and "drop_off_history" explicitly so user knows memory exists
    past_records = customer.get("past_records", "")
    drop_off = customer.get("drop_off_history", "")
    
    if past_records:
         docs_text += f"\n- **Past CRM Records / Interactions**: {past_records}\n"
    if drop_off:
         docs_text += f"- **Known Drop-off History**: {drop_off}\n"
    
    if not past_records and not drop_off:
         docs_text += "\n- **Past CRM Records**: New customer profile with no documented prior loan history."

    sys_prompt = ADVISOR_PROMPT_TEMPLATE.format(
        name=customer.get("name", "Customer"),
        city=customer.get("city", "N/A"),
        salary=salary,
        credit_score=customer.get("credit_score", "N/A"),
        pre_approved_limit=customer.get("pre_approved_limit", 0),
        existing_emi_total=existing_emi,
        current_loans=", ".join(customer.get("current_loans", [])) or "None",
        decision_upper=decision.upper(),
        principal=principal,
        emi=emi,
        tenure=tenure,
        loan_type=terms.get("loan_type", "Personal").capitalize(),
        dti_pct=dti * 100,
        fraud_score=fraud,
        reasons="; ".join(reasons) if reasons else "N/A",
        total_emi=total_emi,
        suggested_amount=suggested_amount,
        suggested_emi=suggested_emi,
        documents_summary=docs_text,
    )

    messages = [SystemMessage(content=sys_prompt)] + state.get("messages", [])
    response = llm.invoke(messages)
    return {"messages": [response]}
