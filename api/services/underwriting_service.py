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
from utils.financial_rules import calculate_foir

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
    if not pre_approved or pre_approved <= 0:
        pre_approved = 150000  # Fallback safety net
    existing_emi = customer.get("existing_emi_total", 0)

    principal = terms.get("principal", 0)
    emi = terms.get("emi", 0)
    rate = terms.get("rate", 12.0)
    tenure = terms.get("tenure", 12)
    fraud_score = state.get("fraud_score", 0.0)

    # Pricing Engine: rate = benchmark + spread
    benchmark_rate = state.get("benchmark_rate", 7.0)
    if score > 800:
        credit_risk_premium = 0.0
    elif score >= 700:
        credit_risk_premium = 2.0
    else:
        credit_risk_premium = 5.0

    business_margin = state.get("business_margin", 1.5)
    operating_cost_loading = state.get("operating_cost_loading", 1.0)

    from utils.financial_rules import calculate_pricing_rate
    # Ensure final rate respects minimum spread above benchmark and a floor for NBFC viability
    rate = calculate_pricing_rate(
        benchmark_rate,
        credit_risk_premium,
        business_margin,
        operating_cost_loading,
        min_spread=2.0,
        floor_rate=8.0
    )
    terms["rate"] = rate

    reasons = []
    decision = "approve"
    risk_level = "low"
    alternative_offer = 0.0

    # Base Metrics
    total_emi = existing_emi + emi
    # calculate_foir returns a fraction (e.g., 0.45 for 45%). Do NOT divide by 100 here.
    dti = calculate_foir(existing_emi, emi, salary)

    # If DTI usage is disabled via settings (demo/test mode), treat DTI as neutral (0.0)
    if not settings.USE_DTI_SCORE:
        dti = 0.0

    # Risk Classification
    if score < 720 or (settings.USE_DTI_SCORE and dti > 0.40) or principal > pre_approved:
        risk_level = "high"
    elif 720 <= score <= 750 or (settings.USE_DTI_SCORE and 0.30 <= dti <= 0.40):
        risk_level = "medium"
    else:
        risk_level = "low"

    # Gate 1: Fraud escalation
    if fraud_score >= 0.7:
        reasons.append(f"Fraud score ({fraud_score}) ≥ 0.7 — Escalated to manual audit.")
        decision = "reject"

    # Enforce credit score threshold (no demo bypasses)
    if score < settings.MIN_CREDIT_SCORE:
        reasons.append(f"⚠️ Credit score ({score}) is below minimum required ({settings.MIN_CREDIT_SCORE}).")
        decision = "reject"

    # Gate 3: Loan limit check (per workflow: Check Loan Limit → Low/Medium/High)
    # Gate 3: Loan limit & DTI enforcement — remove demo bypasses
    if principal > settings.MAX_EXPOSURE_MULTIPLIER * pre_approved:
        reasons.append(f"⚠️ Requested loan (₹{principal:,}) exceeds maximum exposure ({settings.MAX_EXPOSURE_MULTIPLIER}× limit).")
        decision = "hard_reject"
    elif principal > pre_approved:
        if not docs.get("verified"):
            reasons.append("Loan exceeds pre-approved limit; additional income verification required.")
            decision = "pending_docs"
        elif settings.USE_DTI_SCORE and dti > settings.MAX_DTI_RATIO:
            reasons.append(f"⚠️ DTI ratio ({dti*100:.1f}%) is high and exceeds maximum allowed ({settings.MAX_DTI_RATIO*100:.0f}%).")
            decision = "reject"
    else:
        # Principal <= pre_approved — still enforce DTI limits
        if settings.USE_DTI_SCORE and dti > settings.MAX_DTI_RATIO:
            reasons.append(f"⚠️ DTI ratio ({dti*100:.1f}%) exceeds maximum allowed ({settings.MAX_DTI_RATIO*100:.0f}%).")
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

    # Build Highly Personalized Message
    customer_name = customer.get("name", "Valued Customer").title()
    if decision == "approve":
        message = (
            f"✅ **LOAN APPROVED FOR {customer_name.upper()}**\n\n"
            f"Congratulations {customer_name}! Your application for ₹{principal:,} is fully approved. "
            f"Because your {score} credit score is strong and your calculated Debt-to-Income ratio ({dti*100:.1f}%) "
            f"is perfectly manageable within your ₹{salary:,} monthly income, we're happy to grant this standard sanction. "
            f"Your EMI of ₹{emi:,.2f} is locked in!"
        )
    elif decision == "pending_docs":
        message = (
            f"⚠️ **ADDITIONAL REVIEW REQUIRED FOR {customer_name.upper()}**\n\n"
            f"Hi {customer_name}, the requested amount (₹{principal:,}) exceeds your instant pre-approved limit. "
            f"To proceed, we require a Salary Slip to verify your income and recalculate your approval mathematically."
        )
    elif decision == "soft_reject":
        message = (
            f"⚠️ **LOAN UNDER REVIEW FOR {customer_name.upper()}**\n\n"
            f"Hi {customer_name}, your credit profile (Score: {score}) is solid, but the requested ₹{principal:,} "
            f"forces your Debt-to-Income mapping to {dti*100:.1f}%, which exceeds our safety threshold ({settings.MAX_DTI_RATIO*100:.0f}%). "
            f"To protect your financial health, we can comfortably approve a revised amount of ₹{alternative_offer:,.0f}."
            f"Arjun will discuss restructure options with you now."
        )
    else:
        reason_list = "\n".join(f"• {r}" for r in reasons)
        message = (
            f"❌ **LOAN REJECTED FOR {customer_name.upper()}**\n\n"
            f"We're sorry {customer_name}, but your application for ₹{principal:,} could not be approved at this time.\n"
            f"{reason_list}\n\n"
            f"For further help regarding your financial health, our Advisor is available to chat."
        )

    await update_session(session_id, {
        "decision": decision,
        "dti_ratio": dti,
        "risk_level": risk_level,
        "alternative_offer": alternative_offer,
        "reasons": reasons,
        "message": message,
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
