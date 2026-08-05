"""Repayment Agent — Guides users through making EMI payments for active loans."""

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from api.core.websockets import manager
from config import get_master_llm, llm_invoke_with_retry
from datetime import datetime

REPAYMENT_PROMPT = """You are Arjun, a concise loan repayment guide at FinServe.

GUIDELINES:
1. **NEVER RE-ASK**: If the customer already stated their intent (pay, check due date, etc.), respond directly. Do NOT ask "what would you like to do?" again.
2. **BE CONCISE**: 1-2 sentences max. No bullet points, no headers, no loan summaries.
3. **GUIDE TO UI**: Mention the "Pay Next EMI" button in dashboard if they want to pay.
4. **NO ROBOTIC**: No "Your Loan Summary" or "Loan Repayment Portal" headers.
"""

async def repayment_agent_node(state: dict) -> dict:
    """Provides a humanized conversational flow for loan repayments."""
    session_id = state.get("session_id", "default")
    terms = state.get("loan_terms", {})
    customer = state.get("customer_data", {})
    llm = get_master_llm()
    
    # Context for LLM
    principal = terms.get("principal", 0)
    emi = terms.get("emi", 0)
    payments_made = terms.get("payments_made", 0)
    tenure = terms.get("tenure", 0)
    next_due = terms.get("next_emi_date")
    
    # Fetch real active loans from MongoDB loan_applications_collection
    past_loans = customer.get("past_loans", [])
    phone = customer.get("phone", "")
    if phone:
        try:
            from db.database import loan_applications_collection
            from api.services.sales_service import _normalize_phone
            clean_phone = _normalize_phone(phone)
            cursor = loan_applications_collection.find({"phone": clean_phone})
            db_loans = await cursor.to_list(length=100)
            if db_loans:
                past_loans = db_loans
        except Exception as e:
            print(f"⚠️ Failed to query db_loans in repayment_agent: {e}")

    # Fallback to past_loans if current terms are empty (returning user scenario)
    if principal <= 0 and past_loans:
        active_loan = next((l for l in past_loans if l.get("status") in ("Approved", "Disbursed")), past_loans[0])
        if active_loan:
            principal = active_loan.get("amount", 0)
            emi = active_loan.get("emi", 0)
            tenure = active_loan.get("tenure", 0)
            payments_made = active_loan.get("payments_made", 0)
            next_due = active_loan.get("next_emi_date") or active_loan.get("first_emi_due_date")
            
            terms.update({
                "principal": principal,
                "emi": emi,
                "tenure": tenure,
                "payments_made": payments_made,
                "next_emi_date": next_due
            })

    # Count active (non-closed) loans
    active_loans = [l for l in past_loans if l.get("status") in ("Approved", "Disbursed") and not l.get("is_closed")]
    num_active = len(active_loans)
    total_monthly = sum(l.get("emi", 0) for l in active_loans)
    
    if terms.get("principal", 0) > 0 and not terms.get("is_closed"):
        if not any(l.get("session_id") == state.get("session_id") for l in active_loans):
            num_active += 1
            total_monthly += terms.get("emi", 0)

    # ... and we can calculate total remaining EMIs globally
    total_remaining_emis = sum((l.get("tenure", 0) - l.get("payments_made", 0)) for l in active_loans)
    if terms.get("principal", 0) > 0 and not terms.get("is_closed"):
         if not any(l.get("session_id") == state.get("session_id") for l in active_loans):
             total_remaining_emis += (terms.get("tenure", 0) - terms.get("payments_made", 0))

    summary = (
        f"\n📋 **Your Loan Summary**\n\n"
        f"You have **{num_active}** active loan(s):"
        f" • Total Monthly Payment: **₹{total_monthly:,.2f}**"
        f" • Total EMIs Remaining: **{total_remaining_emis}**\n\n"
        f"What would you like to do? "
        f"• Check next EMI due date "
        f"• View detailed loan status "
        f"• Make an EMI payment "
        f"• Get financial advice\n\n"
        f"Just ask! 🤝"
    )

    if principal <= 0 or emi <= 0 or tenure <= 0:
        msg = "It looks like you don't have an active loan with us yet. Is there a specific goal you're saving for, or would you like to see what you're eligible for?"
        return {
            "messages": [AIMessage(content=msg)],
            "current_phase": "advisory",
            "options": ["Apply for Loan", "Check Credit Score"]
        }

    # Generate humanized response via LLM
    prompt_context = (
        f"CUSTOMER: {customer.get('name', 'User')}\n"
        f"LOAN: ₹{principal:,.0f} | EMI: ₹{emi:,.2f}\n"
        f"PROGRESS: {payments_made} out of {tenure} paid\n"
        f"NEXT DUE: {next_due}"
    )
    
    response = await llm_invoke_with_retry(llm, [
        SystemMessage(content=REPAYMENT_PROMPT),
        HumanMessage(content=f"Help me with my payment. Context: {prompt_context}\n\nIMPORTANT: Your entire response must be valid JSON: {{\"type\": \"text\", \"content\": \"your message here\", \"ui_trigger\": \"payment_modal\"}}\nWhen user wants to pay, set ui_trigger to \"payment_modal\". Otherwise omit ui_trigger.")  # noqa: E501
    ])

    return {
        "messages": [AIMessage(content=response.content)],
        "current_phase": "payment",
        "intent": "none",
        "payment_handled": True,
        "options": ["Confirm Payment", "View Detailed Schedule", "Talk to Advisor"]
    }
