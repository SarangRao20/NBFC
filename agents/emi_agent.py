"""EMI Calculator & Advanced FOIR Optimizer Agent."""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage

def _calculate_max_principal(target_emi: float, rate_pa: float, tenure_months: int) -> float:
    """Reverse-calculates the max principal for a target EMI."""
    if target_emi <= 0 or tenure_months <= 0 or rate_pa <= 0:
        return 0.0
    r = (rate_pa / 12) / 100
    n = tenure_months
    p = target_emi * (((1 + r) ** n) - 1) / (r * ((1 + r) ** n))
    return round(p, 2)

def emi_agent_node(state: dict) -> dict:
    """Pure deterministic math — Calculates monthly EMI + smart Reverse-EMI limit optimizations."""
    print("🔢 [EMI AGENT] Calculating Loan Economics...")

    terms = state.get("loan_terms", {})
    customer = state.get("customer_data", {})
    
    principal = terms.get("principal", 0)
    rate_pa = terms.get("rate", 12.0)
    tenure = terms.get("tenure", 12)
    
    salary = customer.get("salary", 0)
    existing_emi = customer.get("existing_emi_total", 0)

    if principal <= 0 or tenure <= 0:
        return {"messages": [AIMessage(content="⚠️ Invalid loan terms. Cannot compute EMI.")]}

    # Standard EMI Calculation
    monthly_rate = (rate_pa / 12) / 100
    emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1)
    emi = round(emi, 2)
    
    total_payment = round(emi * tenure, 2)
    total_interest = round(total_payment - principal, 2)

    # Persuasion Loop Optimization: Reverse Calculate maximum allowable principal for this user
    max_viable_emi = (0.50 * salary) - existing_emi
    max_affordable_principal = _calculate_max_principal(max_viable_emi, rate_pa, tenure)

    updated_terms = {
        **terms, 
        "emi": emi, 
        "total_interest": total_interest,
        "max_affordable_principal": max_affordable_principal
    }

    msg = (
        f"📊 **EMI Breakdown:**\n"
        f"- Monthly EMI: **₹{emi:,.2f}**\n"
        f"- Total Interest: ₹{total_interest:,.2f}\n"
        f"- Total Repayment: ₹{total_payment:,.2f}\n"
        f"- Tenure: {tenure} months @ {rate_pa}% p.a."
    )

    return {"loan_terms": updated_terms, "messages": [AIMessage(content=msg)]}
