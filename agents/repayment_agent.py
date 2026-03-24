"""Repayment Agent — Guides users through making EMI payments for active loans."""

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from api.core.websockets import manager
from config import get_master_llm
from datetime import datetime

REPAYMENT_PROMPT = """You are Arjun, the Senior Financial Advisor at FinServe.
Your goal is to help users manage their repayments naturally and supportively.

GUIDELINES:
1. **BE HUMAN**: Acknowledge their payment progress with encouragement (e.g., "You're halfway there!", "Almost done!").
2. **BE CONCISE**: Limit your response to 2-3 sentences.
3. **GUIDE TO UI**: Naturally mention that they can use the "Pay Next EMI" button in their dashboard.
4. **NO ROBOTIC HEADERS**: Avoid using "Loan Repayment Portal" or similar technical headers.
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
    next_due = terms.get("next_emi_date", "TBD")
    
    # Fallback to past_loans if current terms are empty (returning user scenario)
    if principal <= 0:
        past_loans = customer.get("past_loans", [])
        active_loan = next((l for l in past_loans if l.get("status") == "Approved"), None)
        if active_loan:
            principal = active_loan.get("amount", 0)
            emi = active_loan.get("emi", 0)
            tenure = active_loan.get("tenure", 0)
            payments_made = active_loan.get("payments_made", 0) # Assuming this is tracked in past_loans
            next_due = active_loan.get("next_emi_date", "TBD")
            
            # Hydrate state for other agents
            terms.update({
                "principal": principal,
                "emi": emi,
                "tenure": tenure,
                "payments_made": payments_made,
                "next_emi_date": next_due
            })

    # Count only active (non-closed) loans
    past_loans = customer.get("past_loans", []) # Ensure past_loans is defined for this block
    active_loans = [l for l in past_loans if l.get("status") == "Approved" and not l.get("is_closed")]
    num_active = len(active_loans)
    total_monthly = sum(l.get("emi", 0) for l in active_loans)
    
    # If the current session loan is active but not in past_loans yet (rare but possible), add it
    if terms.get("principal", 0) > 0 and not terms.get("is_closed"):
        # Check if already counted
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
    
    response = await llm.ainvoke([
        SystemMessage(content=REPAYMENT_PROMPT),
        HumanMessage(content=f"Help me with my payment. Context: {prompt_context}")
    ])

    return {
        "messages": [AIMessage(content=response.content)],
        "current_phase": "payment",
        "options": ["Confirm Payment", "View Detailed Schedule", "Talk to Advisor"]
    }
