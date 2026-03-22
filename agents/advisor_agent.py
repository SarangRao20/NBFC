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
## PAST LOAN HISTORY (MEMORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{past_loans_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR ADVISORY OUTPUT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CASE: SIGNED & COMPLETED
- The user has just e-signed the sanction letter. 
- Acknowledge the signature: "Thank you for completing the e-sign process! Your loan is now officially sanctioned."
- Mention disbursement: "Our disbursement team has been notified. You can expect the funds in your account within {tenure_hours} hours."
- End with a professional greeting.

CASE: APPROVED (PENDING SIGNATURE)
- Open with a warm congratulations using their first name.
- Mention their past relationship if {past_loans_summary} is not empty (e.g., "Great to see you again! Your previous loan for ₹{last_loan_amt} was handled perfectly.")
- Confirm EMI date: "Your EMI of ₹{emi:,.2f} will be debited on the 5th of every month starting next month."
- Suggest 1-2 smart money moves.
- Provide the instruction: "Please click the **'Accept & E-Sign'** button above to finalize your loan."

# ... (rest of rejection cases remain same)

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
    is_signed = state.get("is_signed", False)
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

    # Format past loans summary
    past_loans = customer.get("past_loans", [])
    past_loans_summary = ""
    last_loan_amt = "N/A"
    if past_loans:
        past_loans_summary = "Customer has successfully handled previous loans with us:\n"
        for pl in past_loans[:3]: # last 3
            past_loans_summary += f"- ₹{pl.get('amount', 0):,} {pl.get('type','loan')} on {pl.get('date','recent')}: {pl.get('decision','Completed')}\n"
            if pl.get("amount"): last_loan_amt = f"{pl.get('amount'):,}"
    else:
        past_loans_summary = "No previous loan history found in sessions."

    # Suggest viable alternate amount if DTI rejection
    if salary > 0 and dti > 0.50:
        target_emi = salary * 0.45 - existing_emi
        rate_monthly = (terms.get("rate") or 12) / 100 / 12
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
    
    docs_text = f"- **Currently Uploaded & Verified Document**: {verified_doc} (Score: {docs.get('confidence', 0):.0%})\n"
    if docs.get("salary_extracted"):
        docs_text += f"- **Verified OCR Monthly Income**: ₹{docs.get('salary_extracted'):,}\n"
    if docs.get("address_extracted"):
        docs_text += f"- **Verified Address**: {docs.get('address_extracted')}\n"
    
    past_records = customer.get("past_records", "")
    drop_off = customer.get("drop_off_history", "")
    if past_records: docs_text += f"\n- **Past CRM Records**: {past_records}\n"
    if drop_off: docs_text += f"- **Drop-off History**: {drop_off}\n"

    # Use "SIGNED" as decision if is_signed is true
    adj_decision = "SIGNED" if is_signed else decision

    # Context strings
    reasons_str = "; ".join(reasons) if reasons else "N/A"
    doc_type = docs.get("document_type", "None")
    doc_conf = f"{docs.get('confidence', 0):.0%}"
    
    profile_context = f"""Name: {customer.get("name", "Customer")}
City: {customer.get("city", "N/A")}
Monthly Salary: ₹{salary:,}
Credit Score: {customer.get("credit_score", "N/A")}
Pre-Approved Limit: ₹{customer.get("pre_approved_limit", 0):,}
Current EMI Burden: ₹{existing_emi_total:,}/month
Active Loans: {", ".join(customer.get("current_loans", [])) or "None"}
"""

    loan_context = f"""Decision: {adj_decision.upper()}
Requested Amount: ₹{principal:,}
Monthly EMI: ₹{emi:,.2f}
Tenure: {tenure} months
Loan Type: {terms.get("loan_type", "Personal").capitalize()}
DTI (Debt-to-Income) Ratio: {dti * 100:.1f}%
Fraud Risk Score: {fraud:.2f} / 1.0
Rejection Reasons: {reasons_str}
"""

    memories_context = f"""{docs_text}
{past_loans_summary}
"""

    # Rejection guidance for the LLM
    rejection_guidance = f"""
CASE: HARD_REJECT
- Deliver the news firmly but respectfully.
- EXPLAIN the specific reason (e.g., "Requested loan of ₹{principal:,} exceeds our maximum exposure limit which is set at 2× your pre-approved limit of ₹{customer.get("pre_approved_limit", 0):,}.").
- If credit score is the issue, suggest building credit behavior.
- Do NOT offer a counter-offer here unless it's a "Soft Reject" case.

CASE: SOFT_REJECT (NEGOTIATION)
- Acknowledge that while the original request was rejected, they are eligible for a restructured offer.
- Mention the suggested amount: ₹{suggested_amount:,} with EMI of ₹{suggested_emi:,}.
- Invite them to explore the counter-offer.

CASE: NO ACTIVE LOANS (ADVICE ONLY)
- If Requested Amount is ₹0, provide general financial wellness advice based on their profile.
- Reference their city or past records to make it feel local and personal.
"""

    sys_msg = SystemMessage(content=ADVISOR_PROMPT_TEMPLATE + rejection_guidance)
    
    # Context messages to avoid braces issues
    context_msgs = [
        SystemMessage(content=f"### CUSTOMER PROFILE\n{profile_context}"),
        SystemMessage(content=f"### LOAN APPLICATION RESULT\n{loan_context}"),
        SystemMessage(content=f"### DOCUMENTS & PAST HISTORY\n{memories_context}"),
        SystemMessage(content=f"### ALTERNATIVE OFFER (if applicable)\nSuggested Amount: ₹{suggested_amount:,}\nSuggested EMI: ₹{suggested_emi:,}")
    ]

    messages = [sys_msg] + context_msgs + state.get("messages", [])
    response = llm.invoke(messages)
    
    updates = {"messages": [response]}
    
    # If the user just signed, update the state
    if state.get("intent") == "sign":
        updates["is_signed"] = True
        updates["current_phase"] = "loan_disbursed"
        print("✅ [ADVISOR AGENT] Signature recorded. Loan transitioning to disbursed phase.")
    
    return updates
