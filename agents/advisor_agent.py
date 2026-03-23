"""Advisor Agent — deep personalized financial advice after loan decision.

Fires after underwriting with decision = approve / reject.
Uses a rich LLM prompt to generate specific, non-generic advice.
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from config import get_master_llm
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

ADVISOR_PROMPT_TEMPLATE = """You are Priya, a Senior Financial Wellness Advisor at FinServe.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR INTERACTIVE RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **BE CONCISE**: Never write more than 2 short sentences.
2. **ONE QUESTION**: Always end your message with exactly one question to the user.
3. **NO ROBOTS**: Talk like a human specialist. Use "I've been looking at your profile..." instead of "Based on the data...".
4. **EMPATHY**: If they are in debt, be supportive. If they are doing well, celebrate it.

CASE: ADVICE ONLY
- If the user has just corrected a profile detail (like salary or bike value), acknowledge it humanly (e.g., "Oh, my apologies! with ₹1.5 lakh, that changes things...").
- Give one small tip. Ask if they want to know more about that topic or something else.
"""


from api.core.websockets import manager

async def advisor_agent_node(state: dict) -> dict:
    """LLM-powered post-decision financial advisor with rich contextual prompt."""
    session_id = state.get("session_id", "default")
    await manager.broadcast_thinking(session_id, "Priya (Advisor)", True)
    
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
    active_loans_found = False
    if past_loans:
        past_loans_summary = "Customer Loan Profile:\n"
        for pl in past_loans:
            status = pl.get('status', 'Unknown')
            emi_val = pl.get('emi', 0)
            if status == "Approved":
                active_loans_found = True
                past_loans_summary += f"✅ ACTIVE: ₹{pl.get('amount', 0):,} loan with ₹{emi_val:,} monthly EMI. "
                if pl.get('tenure'):
                    past_loans_summary += f"Tenure: {pl.get('tenure')} months. "
                past_loans_summary += "\n"
            else:
                past_loans_summary += f"🕒 PAST: ₹{pl.get('amount', 0):,} {pl.get('type','loan')} - Status: {status}\n"
    else:
        past_loans_summary = "No previous loan history found in sessions."

    if not active_loans_found:
        existing_emi = customer.get("existing_emi_total", 0)
        if existing_emi > 0:
            past_loans_summary += f"\nNote: Customer has external EMI obligations of ₹{existing_emi:,}/month."

    # Suggest viable alternate amount if DTI rejection
    suggested_amount = 0
    suggested_emi = 0
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

    # Calculate EMI dates
    today = datetime.now()
    first_emi_date = today + timedelta(days=30)
    loan_end_date = first_emi_date + timedelta(days=(tenure - 1) * 30) if tenure > 0 else first_emi_date
    
    first_emi_str = first_emi_date.strftime("%d %B %Y")
    loan_end_str = loan_end_date.strftime("%d %B %Y")

    intent = state.get("intent", "none")
    log = list(state.get("action_log") or [])
    
    profile_context = f"""Name: {customer.get("name", "Customer")}
City: {customer.get("city", "N/A")}
Monthly Salary: ₹{salary:,}
Credit Score: {customer.get("credit_score", "N/A")}
Pre-Approved Limit: ₹{customer.get("pre_approved_limit", 0):,}
Current EMI Burden: ₹{existing_emi:,}/month
Active Loans: {", ".join(customer.get("current_loans", [])) or "None"}
"""

    reasons_str = "; ".join(reasons) if reasons else "N/A"
    loan_context = f"""Decision: {adj_decision.upper()}
Requested Amount: ₹{principal:,}
Monthly EMI: ₹{emi:,.2f}
Tenure: {tenure} months
Loan Type: {terms.get("loan_type", "Personal").capitalize()}
DTI (Debt-to-Income) Ratio: {dti * 100:.1f}%
Fraud Risk Score: {fraud:.2f} / 1.0
First EMI Due Date: {first_emi_str}
Loan End Date: {loan_end_str}
Rejection Reasons: {reasons_str}
"""

    memories_context = f"""{docs_text}
{past_loans_summary}
Customer Since: {customer.get("created_at", "N/A")}
Score Trend: {customer.get("score_source", "Default")}
"""

    # Rejection guidance for the LLM
    rejection_guidance = f"""
CASE: HARD_REJECT
- Deliver the news firmly but respectfully.
- EXPLAIN the specific reason.
- If credit score is the issue, suggest building credit behavior.

CASE: SOFT_REJECT (NEGOTIATION)
- Acknowledge the original request was rejected, but they are eligible for a restructured offer.
- Mention Suggested Amount: ₹{suggested_amount:,} with EMI of ₹{suggested_emi:,}.

CASE: NO ACTIVE LOANS (ADVICE ONLY)
- If Requested Amount is ₹0, provide general financial wellness advice based on their profile.
"""

    sys_msg = SystemMessage(content=ADVISOR_PROMPT_TEMPLATE + rejection_guidance)
    
    context_msgs = [
        SystemMessage(content=f"### CUSTOMER PROFILE\n{profile_context}"),
        SystemMessage(content=f"### LOAN APPLICATION RESULT\n{loan_context}"),
        SystemMessage(content=f"### DOCUMENTS & PAST HISTORY\n{memories_context}"),
        SystemMessage(content=f"### ALTERNATIVE OFFER\nSuggested Amount: ₹{suggested_amount:,}\nSuggested EMI: ₹{suggested_emi:,}")
    ]

    messages = [sys_msg] + context_msgs + state.get("messages", [])
    response = await llm.ainvoke(messages)
    
    updates = {
        "messages": [response],
        "action_log": log + [f"⚖️ Priya responded for {adj_decision.upper()} case"],
        "options": ["Accept & E-Sign", "Talk to Specialist", "Exit"] if adj_decision == "approve" else ["View Recovery Plan", "Talk to Specialist", "About DTI"]
    }
    
    if intent == "sign":
        log.append("✍️ E-Signature confirmed.")
        updates["is_signed"] = True
        updates["current_phase"] = "loan_disbursed"
        
        try:
            from api.core.email_service import get_email_service
            email_svc = await get_email_service()
            await email_svc.send_loan_application_notification(
                customer_data=customer,
                loan_terms=terms,
                decision=decision,
                session_id=session_id
            )
        except Exception as e:
            print(f"  ⚠️ Email Error: {e}")

    # Ensure loan metadata JSON is present
    if terms.get("principal") and terms.get("tenure"):
        import json
        loan_json = {
            "loan_type": terms.get("loan_type", "personal"),
            "loan_amount": terms.get("principal"),
            "tenure": terms.get("tenure"),
            "interest_rate": terms.get("rate", 12),
            "confirmed": True if state.get("intent") in ("loan_confirmed", "sign") else False
        }
        response.content += f"\n\n```json\n{json.dumps(loan_json)}\n```"
    
    return updates
