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


def underwriting_agent_node(state: dict) -> dict:
    """Deterministic underwriting — exact PS problem statement rules."""
    print("⚖️ [UNDERWRITING AGENT] Evaluating eligibility...")

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    docs = state.get("documents", {})

    salary = customer.get("salary", 0)
    score = customer.get("credit_score", customer.get("score", 0))
    pre_approved = customer.get("pre_approved_limit", customer.get("limit", 0))
    existing_emi = customer.get("existing_emi_total", 0)
    principal = terms.get("principal", 0)
    emi = terms.get("emi", 0)
    fraud_score = state.get("fraud_score", 0.0)

    reasons = []
    decision = "approve"
    doc_tier = "basic"  # basic or extended

    # Rule 1: Fraud escalation
    if fraud_score >= 0.7:
        reasons.append(f"Fraud score ({fraud_score}) ≥ 0.7 — Escalated to manual audit.")
        decision = "reject"

    # Rule 2: Credit score
    if score < 700:
        reasons.append(f"Credit score ({score}) is below the minimum threshold of 700.")
        decision = "reject"

    # Rule 3: Loan amount vs pre-approved limit
    if principal > 2 * pre_approved:
        reasons.append(f"Requested ₹{principal:,} exceeds 2× pre-approved limit (₹{2*pre_approved:,}).")
        decision = "reject"
    elif principal > pre_approved:
        doc_tier = "extended"
        # Need salary slip verification + FOIR check
        if not docs.get("verified"):
            reasons.append("Extended verification required: Salary slip not yet uploaded/verified.")
            decision = "pending_docs"
        else:
            # FOIR: Total EMI load ≤ 50% of salary
            total_emi = existing_emi + emi
            foir = total_emi / salary if salary > 0 else 1.0
            if foir > 0.50:
                reasons.append(
                    f"FOIR {foir*100:.1f}%: Total EMIs (₹{total_emi:,}) exceed 50% of salary (₹{salary:,})."
                )
                decision = "reject"
    # else: amount ≤ pre-approved → instant approve (basic docs enough)

    # Compute DTI for records
    total_emi = existing_emi + emi
    dti = round(total_emi / salary, 3) if salary > 0 else 1.0

    # Build message
    if decision == "approve":
        tier_note = "(Extended docs verified ✅)" if doc_tier == "extended" else "(Within pre-approved limit ✅)"
        msg = (
            f"✅ **LOAN APPROVED** {tier_note}\n"
            f"- Amount: ₹{principal:,} | EMI: ₹{emi:,.2f}/month\n"
            f"- Credit Score: {score} | DTI: {dti*100:.1f}%\n"
            f"- Generating sanction letter..."
        )
    elif decision == "pending_docs":
        msg = (
            f"📄 **Additional Documents Required**\n"
            f"Your loan amount (₹{principal:,}) is between 1×-2× your pre-approved limit.\n"
            f"Please upload your salary slip for extended verification."
        )
    else:
        reason_text = "\n".join(f"  • {r}" for r in reasons)
        msg = f"❌ **LOAN REJECTED**\n{reason_text}"

    return {
        "decision": decision,
        "dti_ratio": dti,
        "reasons": reasons,
        "messages": [AIMessage(content=msg)]
    }
