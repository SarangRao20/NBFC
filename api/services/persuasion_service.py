"""Persuasion Service — Closer mode for soft-rejected applications (Steps 12-15).

Workflow per diagram:
  1. Analyze Reason for Rejection
  2. Suggest Fix: Reduce Amount or Increase Tenure
  3. User Accepts Modified Offer?
     → Yes: Recalculate Loan Terms → loop back to Decision Engine
     → No:  Route to Advisory Agent
"""

from api.core.state_manager import get_session, update_session, advance_phase
from api.config import get_settings

settings = get_settings()


def _calculate_emi(principal: float, rate_pa: float, tenure: int) -> float:
    if principal <= 0 or tenure <= 0 or rate_pa <= 0:
        return 0.0
    r = (rate_pa / 12) / 100
    return round(principal * r * ((1 + r) ** tenure) / (((1 + r) ** tenure) - 1), 2)


def _calculate_max_principal(target_emi: float, rate_pa: float, tenure: int) -> float:
    if target_emi <= 0 or tenure <= 0 or rate_pa <= 0:
        return 0.0
    r = (rate_pa / 12) / 100
    return round(target_emi * (((1 + r) ** tenure) - 1) / (r * ((1 + r) ** tenure)), -3)


async def analyze_rejection(session_id: str) -> dict:
    """Step 12: Analyze reason for rejection."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    reasons = state.get("reasons", [])
    dti = state.get("dti_ratio", 0)
    score = customer.get("credit_score", 0)

    await advance_phase(session_id, "persuasion_analysis")

    return {
        "rejection_reasons": reasons,
        "credit_score_ok": score >= settings.MIN_CREDIT_SCORE,
        "dti_current": dti,
        "dti_threshold": settings.MAX_DTI_RATIO,
        "message": (
            f"Rejection analysis: DTI is {dti*100:.1f}% (threshold: {settings.MAX_DTI_RATIO*100:.0f}%). "
            f"Credit score {score} qualifies for negotiation."
        )
    }


async def suggest_fix(session_id: str) -> dict:
    """Step 13: Suggest fix — generate restructured loan options."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})

    salary = customer.get("salary", 0)
    existing_emi = customer.get("existing_emi_total", 0)
    rate = terms.get("rate", 12.0)
    principal = terms.get("principal", 0)
    tenure = terms.get("tenure", 12)

    max_emi = (settings.MAX_DTI_RATIO * salary) - existing_emi
    negotiation_round = state.get("negotiation_round", 0) + 1

    # Check max rounds
    if negotiation_round > settings.MAX_NEGOTIATION_ROUNDS:
        await update_session(session_id, {
            "negotiation_round": negotiation_round,
            "decision": "reject",
        })
        await advance_phase(session_id, "persuasion_max_rounds")
        return {
            "options": [],
            "max_approvable_amount": 0,
            "negotiation_round": negotiation_round,
            "max_rounds": settings.MAX_NEGOTIATION_ROUNDS,
            "message": f"Maximum negotiation rounds ({settings.MAX_NEGOTIATION_ROUNDS}) reached. Routing to Advisory."
        }

    options = []

    # Option A: Same tenure, reduced amount
    if max_emi > 0:
        max_principal = _calculate_max_principal(max_emi, rate, tenure)
        if max_principal > 0:
            new_emi = _calculate_emi(max_principal, rate, tenure)
            options.append({
                "label": f"Reduce to ₹{max_principal:,.0f} ({tenure} months)",
                "amount": max_principal,
                "tenure": tenure,
                "emi": new_emi,
            })

    # Option B/C: Extended tenures with original amount
    for ext_tenure in [36, 48, 60]:
        if ext_tenure <= tenure:
            continue
        ext_emi = _calculate_emi(principal, rate, ext_tenure)
        if ext_emi > 0 and (existing_emi + ext_emi) / salary <= settings.MAX_DTI_RATIO:
            options.append({
                "label": f"Full ₹{principal:,.0f} ({ext_tenure} months)",
                "amount": principal,
                "tenure": ext_tenure,
                "emi": ext_emi,
            })

    max_approvable = max_principal if options else 0

    await update_session(session_id, {
        "negotiation_round": negotiation_round,
        "persuasion_options": options,
    })
    await advance_phase(session_id, "persuasion_suggested")

    return {
        "options": options,
        "max_approvable_amount": max_approvable,
        "negotiation_round": negotiation_round,
        "max_rounds": settings.MAX_NEGOTIATION_ROUNDS,
        "message": f"Round {negotiation_round}/{settings.MAX_NEGOTIATION_ROUNDS}: {len(options)} options generated."
    }


async def process_response(session_id: str, action: str, custom_amount: float = None, custom_tenure: int = None) -> dict:
    """Step 14: Process user's accept/decline response."""
    state = await get_session(session_id)
    if not state:
        return None

    options = state.get("persuasion_options", [])
    terms = state.get("loan_terms", {})
    rate = terms.get("rate", 12.0)

    if action.startswith("decline") or action == "no":
        # User declines → route to Advisory
        await update_session(session_id, {
            "decision": "reject",
            "persuasion_status": "declined",
        })
        await advance_phase(session_id, "persuasion_declined")
        return {
            "action": "declined",
            "revised_loan_terms": None,
            "next_step": "advisory",
            "message": "Offer declined. Routing to Advisory Agent."
        }

    # Determine which option was chosen
    selected = None

    if action.startswith("accept_option_") and len(action) > len("accept_option_"):
        idx = ord(action[-1].lower()) - ord('a')
        if 0 <= idx < len(options):
            selected = options[idx]

    if action == "accept" or action == "yes":
        if custom_amount and custom_tenure:
            new_emi = _calculate_emi(custom_amount, rate, custom_tenure)
            selected = {"amount": custom_amount, "tenure": custom_tenure, "emi": new_emi}
        elif options:
            selected = options[0]

    if not selected:
        return {
            "action": "invalid",
            "revised_loan_terms": None,
            "next_step": "persuasion",
            "message": "Invalid action. Use 'accept_option_a', 'accept', or 'decline'."
        }

    # Update loan terms with accepted option
    new_emi = _calculate_emi(selected["amount"], rate, selected["tenure"])
    revised_terms = {
        **terms,
        "principal": selected["amount"],
        "tenure": selected["tenure"],
        "emi": new_emi,
    }

    await update_session(session_id, {
        "loan_terms": revised_terms,
        "decision": "",  # Reset for re-evaluation
        "persuasion_status": "accepted",
    })
    await advance_phase(session_id, "persuasion_accepted")

    return {
        "action": "accepted",
        "revised_loan_terms": revised_terms,
        "next_step": "underwriting",
        "message": f"Terms accepted: ₹{selected['amount']:,.0f} for {selected['tenure']} months. Re-submitting to Decision Engine."
    }


async def recalculate_terms(session_id: str, principal: float, tenure_months: int, rate: float = None) -> dict:
    """Step 15: Recalculate loan terms with new parameters."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    salary = customer.get("salary", 0)
    existing_emi = customer.get("existing_emi_total", 0)

    if rate is None:
        rate = terms.get("rate", 12.0)

    emi = _calculate_emi(principal, rate, tenure_months)
    total_payment = round(emi * tenure_months, 2)
    total_interest = round(total_payment - principal, 2)
    total_emi = existing_emi + emi
    dti = round(total_emi / salary, 3) if salary > 0 else 1.0

    revised_terms = {
        "loan_type": terms.get("loan_type", ""),
        "principal": principal,
        "rate": rate,
        "tenure": tenure_months,
        "emi": emi,
    }

    await update_session(session_id, {"loan_terms": revised_terms})
    await advance_phase(session_id, "terms_recalculated")

    return {
        "loan_terms": revised_terms,
        "emi": emi,
        "total_interest": total_interest,
        "total_repayment": total_payment,
        "dti_estimate": dti,
        "within_threshold": dti <= settings.MAX_DTI_RATIO,
        "message": (
            f"Recalculated: ₹{principal:,.0f} @ {rate}% for {tenure_months}m → EMI ₹{emi:,.2f}. "
            f"DTI: {dti*100:.1f}% ({'✅ within' if dti <= settings.MAX_DTI_RATIO else '❌ exceeds'} threshold)."
        )
    }
