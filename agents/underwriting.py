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
    """Deterministic underwriting engine checking NTC and FOIR heuristics."""
    print("⚖️ [UNDERWRITING AGENT] Evaluating advanced eligibility rules...")

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
    max_affordable_principal = terms.get("max_affordable_principal", 0)

    reasons = []
    decision = "approve"
    risk_level = "low"
    alternative_offer = 0.0

    # Base Metrics
    total_emi = existing_emi + emi
    dti = round(total_emi / salary, 3) if salary > 0 else 1.0

    # ── DECISION TREE LOGIC ENGINE (Mapped to Diagram) ── #
    
    # Pre-check: Fraud Escapement Gate
    if fraud_score >= 0.7:
        reasons.append(f"Fraud score ({fraud_score}) ≥ 0.7 — Escalated to manual audit.")
        decision = "hard_reject"
        risk_level = "high"

    # Pre-check: NTC (New To Credit) Thin-file Detection
    elif score == 0 or score == -1:
        if not docs.get("bank_statement_verified"):
            reasons.append("New-To-Credit Detected. Please upload 6 months' Bank Statement for limit assessment.")
            decision = "pending_docs"
        elif principal > 50000:
            reasons.append("For 'New to Credit' users without a CIBIL score, the maximum introductory loan is strictly ₹50,000.")
            decision = "soft_reject"
            alternative_offer = 50000.0
            
    # Core Strategy: Standard CIBIL Borrower Execution Tree
    else:
        # Branch 1: Credit Score >= 700?
        if score < 700:
            reasons.append(f"Credit Score ({score}) is below the minimum threshold of 700.")
            decision = "hard_reject"
            risk_level = "high"
            
        # Branch 2: Credit Score IS >= 700 -> Check Loan Limit
        else:
            # Categorize the Limit
            if principal <= pre_approved:
                limit_category = "Low"
            elif principal > (2 * pre_approved):
                limit_category = "High"
            else:
                limit_category = "Medium"

            # Route by Limit Category
            if limit_category == "Low":
                # Tag: Low Risk -> Approved (Bypasses DTI caps!)
                risk_level = "low"
                decision = "approve"
                
            elif limit_category == "High":
                # Hard Reject: Exposure Limit
                reasons.append(f"Requested loan strongly exceeds maximum permissible exposure (2× pre-approved limit).")
                decision = "hard_reject"
                risk_level = "high"
                
            elif limit_category == "Medium":
                # Calculate DTI
                # If they require a Medium limit, we MUST verify their salary slip first.
                if not docs.get("verified"):
                    reasons.append("To approve a medium-exposure loan exceeding your basic pre-approved limits, please upload your Salary Slip.")
                    decision = "pending_docs"
                else:
                    if dti > 0.50:
                        # High DTI -> Soft Reject
                        reasons.append(f"EMI pushes DTI to {dti*100:.1f}%, exceeding 50% safety limit.")
                        decision = "soft_reject"
                        risk_level = "medium"
                        if max_affordable_principal > 0:
                            alternative_offer = min(max_affordable_principal, 2 * pre_approved)
                    else:
                        # Acceptable DTI -> Approved
                        decision = "approve"
                        risk_level = "medium"

    # Rule 9: Explainability Layer Output Generator
    if decision == "approve":
        msg = (f"✅ **LOAN APPROVED**\n\n"
               f"**Decision Reasoning**: Your EMI of ₹{emi:,.2f} accounts for {dti*100:.1f}% of your monthly income, "
               f"which is comfortably within our safety threshold. Your application has been fully sanctioned under a **{risk_level.title()} Risk** classification.")
    
    elif decision == "pending_docs":
        msg = (f"⏳ **LOAN PENDING (Additional Documents Required)**\n\n"
               f"**Decision Reasoning**: {' '.join(reasons)}")
        
    elif decision == "soft_reject":
        reason_text = "\n".join(f"• {r}" for r in reasons)
        msg = (f"❌ **LOAN BLOCKED AT CURRENT AMOUNT**\n\n"
               f"**Cause**:\n{reason_text}\n\n"
               f"💡 **Smart Re-Optimization Offer**: While we cannot approve ₹{principal:,.0f}, we can instantly approve an optimized alternative "
               f"loan amount of **₹{alternative_offer:,.0f}** for the exact same tenure based on your verified safety limits.")
               
    else:
        reason_text = "\n".join(f"• {r}" for r in reasons)
        msg = (f"❌ **LOAN REJECTED**\n\n"
               f"**Decision Reasoning**:\n{reason_text}")

    return {
        "decision": decision,
        "dti_ratio": dti,
        "risk_level": risk_level,
        "alternative_offer": alternative_offer,
        "reasons": reasons,
        "messages": [AIMessage(content=msg)]
    }
