"""Underwriting Agent — evaluates loan eligibility using PS rules:
  - If amount ≤ pre-approved limit → instant approve (basic docs only)
  - If amount ≤ 2× pre-approved limit → approve only if EMI ≤ 50% salary (needs salary slip)
  - If amount > 2× pre-approved limit → reject
  - If credit score < 700 → reject
  - If fraud score ≥ 0.7 → reject (escalate)
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage

def _calculate_max_principal(max_emi, rate_annual, tenure_months):
    """Helper to back-calculate principal from a target EMI."""
    r = (rate_annual / 100) / 12
    n = tenure_months
    if r > 0:
        return int(max_emi * ((1 + r)**n - 1) / (r * (1 + r)**n))
    return int(max_emi * n)

def underwriting_agent_node(state: dict) -> dict:
    """Deterministic underwriting engine following the flowchart logic."""
    print("⚖️ [UNDERWRITING AGENT] Evaluating flowchart-based eligibility...")

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    
    salary = customer.get("salary", 0)
    score = customer.get("credit_score", customer.get("score", 0))
    pre_approved = customer.get("pre_approved_limit", customer.get("limit", 0))
    existing_emi = customer.get("existing_emi_total", 0)
    
    principal = terms.get("principal", 0)
    emi = terms.get("emi", 0)
    tenure = terms.get("tenure", 24)
    rate = terms.get("rate", 12)
    fraud_score = state.get("fraud_score", 0.0)

    reasons = []
    decision = "approve"
    risk_level = "low"
    alternative_offer = 0.0

    # Base Metrics
    total_emi = existing_emi + emi
    dti = round(total_emi / salary, 3) if salary > 0 else 1.0

    # 1. Score Gate
    if score < 700:
        reasons.append(f"Credit score ({score}) is below the minimum threshold of 700.")
        decision = "hard_reject"
    
    # 2. Fraud Gate (Pre-gate)
    elif fraud_score >= 0.7:
        reasons.append(f"Fraud score ({fraud_score}) triggered a critical safety block.")
        decision = "hard_reject"

    # 3. Limit Gate
    else:
        if principal > 2 * pre_approved:
            reasons.append(f"Requested loan (₹{principal:,}) exceeds maximum exposure limit (₹{2*pre_approved:,}).")
            decision = "hard_reject"
        elif principal <= pre_approved:
            risk_level = "low"
            # Final DTI Check for Approved Low-Limit
            if dti > 0.50:
                reasons.append("High DTI (Debt-to-Income ratio) against requested amount.")
                decision = "soft_reject"
        else:
            # Medium Limit: pre_approved < principal <= 2 * pre_approved
            risk_level = "medium"
            if dti > 0.50:
                reasons.append(f"DTI ({dti*100:.0f}%) is higher than our acceptable threshold for this limit.")
                decision = "soft_reject"
            else:
                decision = "approve"

    # Calculate Alternative Offer for Soft Rejects
    if decision == "soft_reject":
        max_viable_emi = (0.50 * salary) - existing_emi
        if max_viable_emi > 0:
            alternative_offer = _calculate_max_principal(max_viable_emi, rate, tenure)
            alternative_offer = min(alternative_offer, principal * 0.9) # Offer slightly less

    # Generate Message
    if decision == "approve":
        msg = f"✅ **LOAN APPROVED**\n\nYour application for ₹{principal:,} has been approved! Your EMI of ₹{emi:,.2f} fits perfectly within your profile."
    elif decision == "soft_reject":
        msg = (f"⚠️ **LOAN UNDER REVIEW**\n\nYour profile is strong, but the current EMI burden is high. "
               f"We can approve a modified amount of ₹{alternative_offer:,.0f}. Arjun will discuss this with you.")
    else:
        msg = f"❌ **LOAN REJECTED**\n\n" + "\n".join(f"• {r}" for r in reasons)

    return {
        "decision": decision,
        "dti_ratio": dti,
        "risk_level": risk_level,
        "alternative_offer": alternative_offer,
        "reasons": reasons,
        "messages": [AIMessage(content=msg)]
    }
