"""EMI Calculator Agent — computes loan EMI, total interest, and amortization breakdown."""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage


async def emi_agent_node(state: dict) -> dict:
    """Pure deterministic math — no LLM tokens wasted."""
    print("🔢 [EMI AGENT] Calculating...")

    terms = state.get("loan_terms", {})
    principal = terms.get("principal", 0)
    rate_pa = terms.get("rate", 12.0)
    tenure = terms.get("tenure", 12)

    if principal <= 0 or tenure <= 0:
        return {"messages": [AIMessage(content="⚠️ Invalid loan terms. Cannot compute EMI.")]}

    from utils.financial_rules import calculate_emi

    emi = calculate_emi(principal, rate_pa, tenure)
    total_interest = round((emi * tenure) - principal, 2)
    total_payment = round(principal + total_interest, 2)

    updated_terms = {**terms, "emi": emi}
    msg = (
        f"📊 **EMI Breakdown:**\n"
        f"- Monthly EMI: **₹{emi:,.2f}**\n"
        f"- Total Interest: ₹{total_interest:,.2f}\n"
        f"- Total Repayment: ₹{total_payment:,.2f}\n"
        f"- Tenure: {tenure} months @ {rate_pa}% p.a."
    )

    import json
    msg_json = json.dumps({"type": "emi_slider", "content": msg})
    return {
        "loan_terms": updated_terms, 
        "messages": [AIMessage(content=msg_json)],
        "current_phase": "sales",
        "pending_question": "confirm_loan_terms",
        "options": ["Yes, Proceed", "No, Change Details"]
    }
