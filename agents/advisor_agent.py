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
You are the user's ally for financial planning and orientation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR ROLE & BOUNDARIES (STRICT):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **BRIDGE TO ARJUN**: You NEVER process or discuss loan details (amount, terms). If a user mentions wanting a loan, DO NOT ask "would you like to proceed?". Instead, warmly say you'll bring in Arjun, our Sales Specialist.
2. **NO DECISIONING**: You never "inform" the user about rejections or approvals during a new application. That is the system's role.
3. **ORIENTATION**: Your job is to help the user understand the dashboard, their credit score (if available), or generic financial wellness.
4. **HUMAN-FIRST**: Write like a person. NO "I've checked your profile and unfortunately...". Try "Looking at your goals, I think we can build a great plan together!"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## INTERACTIVE RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **BE CONVERSATIONAL**: Write 2-3 natural sentences.
2. **ONE QUESTION**: Always end your message with exactly one question to keep the dialogue flowing.
3. **NO ROBOTS**: NO rigid bullet points or technical headers like "CASE: NO ACTIVE LOANS".
4. **EMPATHY**: Celebrate successes and be supportive during challenges.
"""


from api.core.websockets import manager

async def advisor_agent_node(state: dict) -> dict:
    """LLM-powered post-decision financial advisor with rich contextual prompt."""
    session_id = state.get("session_id", "default")
    await manager.broadcast_thinking(session_id, "Priya (Advisor)", True)
    
    print("💡 [ADVISOR AGENT] Generating personalized advice...")
    
    log = list(state.get("action_log") or [])
    
    # ─── DETECT RE-NEGOTIATION: User asking for explicit amount when already rejected ─────
    from langchain_core.messages import HumanMessage
    import re as _re
    msgs = state.get("messages", [])
    decision = state.get("decision", "")
    
    if msgs and isinstance(msgs[-1], HumanMessage):
        last_msg = str(msgs[-1].content).lower()
        
        # 🚨 GLOBAL LOAN REDIRECT: If user mentions loan/borrowing/amount, ALWAYS hand off to Arjun
        loan_keywords = ["loan", "borrow", "apply", "money", "rupees", "lak", "lakh", "k", "amount"]
        has_loan_intent = any(kw in last_msg for kw in loan_keywords)
        
        # Look for explicit amount patterns
        has_explicit_amount = bool(
            _re.search(r"\d+\s*k\b", last_msg) or
            _re.search(r"\d+\s*lakh", last_msg) or
            _re.search(r"\d+\s*lac\b", last_msg) or
            _re.search(r"\d+\s*thousand", last_msg) or
            (_re.search(r"\d{4,9}", last_msg) and ("loan" in last_msg or "amount" in last_msg))
        )
        
        if has_loan_intent or has_explicit_amount:
            print("🔄 [ADVISOR] Global Loan Redirect triggered - handing off to Arjun (Sales)")
            
            # Reset loan amount if it was just a raw number (to let sales collect it properly)
            # or keep it if it was a confirmation.
            updates = {
                "next_agent": "sales_agent",
                "intent": "loan",
                "action_log": log + ["🔄 Priya handing off loan interest to Arjun"]
            }
            
            # If we're not currently in a decision state, help clear it
            if decision == "unknown" or decision == "":
                updates["decision"] = ""
                
            return updates
    
    # ─── Normal advisor flow ─────────────────────────────────────────────────────────────

    llm = get_master_llm()
    customer = state.get("customer_data", {})
    decision = state.get("decision", "unknown")
    is_signed = state.get("is_signed", False)
    dti = state.get("dti_ratio") or 0  # Handle None values
    terms = state.get("loan_terms", {})
    fraud = state.get("fraud_score", 0.0)
    reasons = state.get("reasons", [])

    salary = customer.get("salary") or 0  # Handle None values
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
        if rate_monthly > 0 and target_emi > 0:
            suggested_amount = int(target_emi * ((1 + rate_monthly) ** n - 1) / (rate_monthly * (1 + rate_monthly) ** n))
            suggested_emi = int(target_emi)
        elif target_emi > 0:
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
- If DTI is too high, suggest debt restructuring or paying down existing EMIs first.

CASE: SOFT_REJECT (NEGOTIATION)
- Acknowledge the original request was rejected, but they are eligible for a restructured offer.
- If Suggested Amount is ₹{suggested_amount:,} and is > 500: Mention it explicitly: "You can apply for ₹{suggested_amount:,} instead."
- If Suggested Amount is too low (< ₹50000) or zero: Suggest alternatives like:
  * "Your current EMI burden is high. Paying down existing loans could free up more capacity."
  * "Consider restructuring your current loans to improve eligibility."
  * "In 6-12 months of maintaining good payment history, you'll likely qualify for higher amounts."

CASE: NO ACTIVE LOANS (ADVICE ONLY)
- If the user expressed interest in a loan but 'principal' is ₹0: DO NOT give generic budget advice. Instead, warmly redirect them to Arjun (our Sales Specialist) to start their application.
- Example: "I see you're interested in a loan! I'd love to help, but let's first chat with Arjun to figure out exactly what you need. He's great at finding the right fit for your goals."
- If they are just saying hi or chatting generally, handle it as a warm orientation Specialist.
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
