"""EMI Calculator Agent — computes loan EMI, total interest, and amortization breakdown."""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage


def emi_agent_node(state: dict) -> dict:
    """Pure deterministic math — no LLM tokens wasted."""
    print("🔢 [EMI AGENT] Calculating...")

    terms = state.get("loan_terms", {})
    principal = terms.get("principal", 0)
    rate_pa = terms.get("rate", 12.0)
    tenure = terms.get("tenure", 12)

    if principal <= 0 or tenure <= 0:
        return {"messages": [AIMessage(content="⚠️ Invalid loan terms. Cannot compute EMI.")]}

    monthly_rate = (rate_pa / 12) / 100
    emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1)
    emi = round(emi, 2)
    total_payment = round(emi * tenure, 2)
    total_interest = round(total_payment - principal, 2)

    updated_terms = {**terms, "emi": emi}

    msg = (
        f"📊 **EMI Breakdown:**\n"
        f"- Monthly EMI: **₹{emi:,.2f}**\n"
        f"- Total Interest: ₹{total_interest:,.2f}\n"
        f"- Total Repayment: ₹{total_payment:,.2f}\n"
        f"- Tenure: {tenure} months @ {rate_pa}% p.a."
    )

    return {"loan_terms": updated_terms, "messages": [AIMessage(content=msg)]}
