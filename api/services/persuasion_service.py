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
    """Step 12: Analyze reason for rejection using the Persuasion Agent."""
    state = await get_session(session_id)
    if not state:
        return None

    from agents.persuasion_agent import persuasion_agent_node
    
    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    reasons = state.get("reasons", [])
    dti = state.get("dti_ratio", 0)
    score = customer.get("credit_score", 0)
    negotiation_round = state.get("negotiation_round", 0)

    # Map API state to Agent state
    agent_state = {
        "customer_data": customer,
        "loan_terms": terms,
        "reasons": reasons,
        "dti_ratio": dti,
        "negotiation_round": negotiation_round
    }
    
    agent_result = persuasion_agent_node(agent_state)
    
    # Update state from agent result
    await update_session(session_id, {
        "negotiation_round": agent_result.get("negotiation_round", negotiation_round + 1),
        "persuasion_options": agent_result.get("persuasion_options", [])
    })
    
    await advance_phase(session_id, "persuasion_analysis")

    return {
        "rejection_reasons": reasons,
        "credit_score_ok": score >= settings.MIN_CREDIT_SCORE,
        "dti_current": dti,
        "dti_threshold": settings.MAX_DTI_RATIO,
        "message": agent_result["messages"][0].content if agent_result.get("messages") else "Negotiation initiated."
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
    """Step 14: Process user's accept/decline response using the Persuasion Agent."""
    state = await get_session(session_id)
    if not state:
        return None

    from agents.persuasion_agent import process_persuasion_response
    
    # Map API action to a simulated user message for the agent
    user_msg = action
    if action == "accept" and custom_amount:
        user_msg = f"I want to accept ₹{custom_amount} for {custom_tenure} months"
    
    agent_result = process_persuasion_response(user_msg, state)
    
    updates = {}
    if "loan_terms" in agent_result:
        updates["loan_terms"] = agent_result["loan_terms"]
    if "decision" in agent_result:
        updates["decision"] = agent_result["decision"]
    if "persuasion_status" in agent_result:
        updates["persuasion_status"] = agent_result["persuasion_status"]
    else:
        updates["persuasion_status"] = agent_result.get("action", "")

    await update_session(session_id, updates)
    
    phase = "persuasion_accepted" if agent_result.get("action") == "accept" else "persuasion_declined"
    await advance_phase(session_id, phase)

    return {
        "action": agent_result.get("action", "unclear"),
        "revised_loan_terms": agent_result.get("loan_terms"),
        "next_step": "underwriting" if agent_result.get("action") == "accept" else "advisory",
        "message": agent_result["messages"][0].content if agent_result.get("messages") else "Response processed."
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
