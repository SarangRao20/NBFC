"""Underwriting Service — Decision Engine (Step 11).

Decision tree per workflow diagram:
  Credit Score >= 700?
  ├── No  → Hard Reject: Poor Score
  └── Yes → Check Loan Limit
            ├── Low    → Tag: Low Risk → Approved
            ├── High   → Hard Reject: Exposure Limit
            └── Medium → Calculate DTI
                         ├── High DTI → Soft Reject
                         └── Acceptable → Approved → State Update: Decision Stored
"""

from api.core.state_manager import get_session, update_session, advance_phase
from api.config import get_settings

settings = get_settings()


def _calculate_max_principal(target_emi: float, rate_pa: float, tenure: int) -> float:
    """Reverse-calculate the max principal for a target EMI."""
    if target_emi <= 0 or tenure <= 0 or rate_pa <= 0:
        return 0.0
    r = (rate_pa / 12) / 100
    p = target_emi * (((1 + r) ** tenure) - 1) / (r * ((1 + r) ** tenure))
    return round(p, 2)


async def underwrite(session_id: str) -> dict:
    """Step 11: Full underwriting decision engine."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    docs = state.get("documents", {})

    salary = customer.get("salary", 0)
    score = customer.get("credit_score", 0)
    pre_approved = customer.get("pre_approved_limit", 0)
    existing_emi = customer.get("existing_emi_total", 0)

    principal = terms.get("principal", 0)
    emi = terms.get("emi", 0)
    rate = terms.get("rate", 12.0)
    tenure = terms.get("tenure", 12)
    fraud_score = state.get("fraud_score", 0.0)

    reasons = []
    decision = "approve"
    risk_level = "low"
    alternative_offer = 0.0

    # Base Metrics
    total_emi = existing_emi + emi
    dti = round(total_emi / salary, 3) if salary > 0 else 1.0

    # Risk Classification
    if score < 720 or dti > 0.40 or principal > pre_approved:
        risk_level = "high"
    elif 720 <= score <= 750 or 0.30 <= dti <= 0.40:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Gate 1: Fraud escalation
    if fraud_score >= 0.7:
        reasons.append(f"Fraud score ({fraud_score}) ≥ 0.7 — Escalated to manual audit.")
        decision = "reject"

    # Gate 2: Credit score check (per workflow: Credit Score >= 700?)
    if score < settings.MIN_CREDIT_SCORE:
        reasons.append(f"Credit score ({score}) below minimum threshold of {settings.MIN_CREDIT_SCORE}.")
        decision = "reject"

    # Gate 3: Loan limit check (per workflow: Check Loan Limit → Low/Medium/High)
    if principal > settings.MAX_EXPOSURE_MULTIPLIER * pre_approved:
        reasons.append(f"Requested loan exceeds maximum exposure ({settings.MAX_EXPOSURE_MULTIPLIER}× limit).")
        decision = "reject"
    elif principal > pre_approved:
        if not docs.get("verified"):
            reasons.append("Loan exceeds pre-approved limit; additional income verification required.")
            decision = "pending_docs"
        elif dti > settings.MAX_DTI_RATIO:
            reasons.append(f"DTI ratio ({dti*100:.1f}%) exceeds {settings.MAX_DTI_RATIO*100:.0f}% threshold.")
            decision = "reject"
    else:
        # Principal <= pre_approved — still check DTI
        if dti > settings.MAX_DTI_RATIO:
            reasons.append(f"DTI ratio ({dti*100:.1f}%) exceeds {settings.MAX_DTI_RATIO*100:.0f}% threshold.")
            decision = "reject"

    # Soft Reject Classification (per workflow: Soft Reject → Persuasion Loop)
    if decision == "reject" and fraud_score < 0.7 and score >= settings.MIN_CREDIT_SCORE:
        max_viable_emi = (settings.MAX_DTI_RATIO * salary) - existing_emi
        if max_viable_emi > 0:
            alt_p = _calculate_max_principal(max_viable_emi, rate, tenure)
            alt_p = min(alt_p, settings.MAX_EXPOSURE_MULTIPLIER * pre_approved)
            alternative_offer = alt_p
            if alt_p > 1000:
                decision = "soft_reject"

    # Build message
    if decision == "approve":
        message = (
            f"LOAN APPROVED. EMI ₹{emi:,.2f} = {dti*100:.1f}% of income. "
            f"Credit score {score}. Risk: {risk_level}."
        )
    elif decision == "pending_docs":
        message = f"LOAN PENDING. Additional documentation required for ₹{principal:,}."
    elif decision == "soft_reject":
        message = (
            f"LOAN UNDER REVIEW. DTI exceeds threshold but credit qualifies for negotiation. "
            f"Alternative offer: ₹{alternative_offer:,.0f}. Proceed to Persuasion Loop."
        )
    else:
        message = f"LOAN REJECTED. {'; '.join(reasons)}"

    await update_session(session_id, {
        "decision": decision,
        "dti_ratio": dti,
        "risk_level": risk_level,
        "alternative_offer": alternative_offer,
        "reasons": reasons,
    })
    await advance_phase(session_id, "underwriting_complete")

    return {
        "decision": decision,
        "risk_level": risk_level,
        "dti_ratio": dti,
        "reasons": reasons,
        "alternative_offer": alternative_offer if alternative_offer > 0 else None,
        "message": message,
    }
