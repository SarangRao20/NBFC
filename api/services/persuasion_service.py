"""Persuasion Service — Generate counter offers and negotiation options for soft-rejected loans."""

from typing import Optional, List, Dict
from datetime import datetime
from api.core.state_manager import get_session, update_session
from api.config import Settings
from utils.financial_rules import calculate_emi

settings = Settings()


def _calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculate monthly EMI."""
    return calculate_emi(principal, annual_rate, tenure_months)


async def analyze_rejection(session_id: str) -> dict:
    """
    Analyze why a loan was soft-rejected.
    Returns: Rejection reasons, credit score status, DTI analysis, etc.
    """
    state = await get_session(session_id)
    if not state:
        return {"error": "Session not found"}
    
    decision = state.get("decision", "")
    if decision not in ("soft_reject", "reject"):
        return {"error": "No rejection to analyze"}
    
    customer = state.get("customer_data", {})
    loan_terms = state.get("loan_terms", {})
    dti_ratio = state.get("dti_ratio", 0.0)
    reasons = state.get("reasons", [])
    salary = customer.get("salary", 0)
    score = customer.get("credit_score", 0)
    existing_emi = customer.get("existing_emi_total", 0)
    
    credit_score_ok = score >= settings.MIN_CREDIT_SCORE
    dti_threshold = settings.MAX_DTI_RATIO
    
    return {
        "rejection_reasons": reasons,
        "credit_score_ok": credit_score_ok,
        "credit_score": score,
        "dti_current": dti_ratio,
        "dti_threshold": dti_threshold,
        "dti_exceeds": dti_ratio > dti_threshold,
        "monthly_income": salary,
        "existing_emi": existing_emi,
        "message": f"Your DTI ratio ({dti_ratio*100:.1f}%) exceeds the safe limit ({dti_threshold*100:.0f}%). "
                   f"We can offer adjusted terms to bring this within healthy range."
    }


async def suggest_fix(session_id: str) -> dict:
    """
    Generate counter-offer options for soft-rejected loans.
    Returns: List of alternative loan options (different amount/tenure combinations).
    """
    state = await get_session(session_id)
    if not state:
        return {"error": "Session not found"}
    
    decision = state.get("decision", "")
    if decision != "soft_reject":
        return {"error": "Decision is not soft_reject"}
    
    customer = state.get("customer_data", {})
    loan_terms = state.get("loan_terms", {})
    alternative_offer = state.get("alternative_offer", 0)
    
    salary = customer.get("salary", 0)
    existing_emi = customer.get("existing_emi_total", 0)
    principal = loan_terms.get("principal", 0)
    tenure = loan_terms.get("tenure", 24)
    rate = loan_terms.get("rate", 12.0)
    
    if not alternative_offer:
        return {
            "options": [],
            "max_approvable_amount": 0,
            "negotiation_round": 1,
            "max_rounds": 3,
            "rejection_reasons": state.get("reasons", []),
            "message": "Unable to generate counter-offers. Insufficient income."
        }
    
    # ─── GENERATE 3 OPTIONS ───────────────────────────────────────────
    # Option 1: Safe amount @ same tenure (best for predictability)
    # Option 2: Slightly higher @ longer tenure
    # Option 3: Moderate amount @ shortest viable tenure
    
    options = []
    dti_threshold = settings.MAX_DTI_RATIO
    max_emi_allowed = (dti_threshold * salary) - existing_emi
    
    try:
        # Option A: Conservative - Most aggressive cost reduction
        if alternative_offer > 0:
            opt_a_amount = int(alternative_offer * 0.8)  # 80% of max
            opt_a_tenure = tenure  # Keep same tenure for predictability
            opt_a_emi = _calculate_emi(opt_a_amount, rate, opt_a_tenure)
            
            if opt_a_emi > 0 and opt_a_emi <= max_emi_allowed:
                options.append({
                    "label": f"Option A: ₹{opt_a_amount:,} @ {opt_a_tenure} months",
                    "amount": opt_a_amount,
                    "tenure": opt_a_tenure,
                    "emi": round(opt_a_emi, 2),
                    "total_interest": round(opt_a_emi * opt_a_tenure - opt_a_amount, 2),
                    "description": "Conservative approach - Lower amount, same tenure. Safest for DTI."
                })
        
        # Option B: Balanced - Medium amount, longer tenure
        if alternative_offer > 0:
            opt_b_amount = int(alternative_offer * 0.9)  # 90% of max
            opt_b_tenure = min(tenure + 12, 60)  # Extend by 12 months (max 60)
            opt_b_emi = _calculate_emi(opt_b_amount, rate, opt_b_tenure)
            
            if opt_b_emi > 0 and opt_b_emi <= max_emi_allowed:
                options.append({
                    "label": f"Option B: ₹{opt_b_amount:,} @ {opt_b_tenure} months",
                    "amount": opt_b_amount,
                    "tenure": opt_b_tenure,
                    "emi": round(opt_b_emi, 2),
                    "total_interest": round(opt_b_emi * opt_b_tenure - opt_b_amount, 2),
                    "description": "Balanced approach - Get more, extend tenure to manage EMI."
                })
        
        # Option C: Aggressive - Maximum approvable amount @ shorter timeline
        if alternative_offer > 0:
            opt_c_amount = int(alternative_offer)  # Full max
            opt_c_tenure = max(tenure - 6, 12)  # Reduce by 6 months (min 12)
            opt_c_emi = _calculate_emi(opt_c_amount, rate, opt_c_tenure)
            
            if opt_c_emi > 0 and opt_c_emi <= max_emi_allowed:
                options.append({
                    "label": f"Option C: ₹{opt_c_amount:,} @ {opt_c_tenure} months",
                    "amount": opt_c_amount,
                    "tenure": opt_c_tenure,
                    "emi": round(opt_c_emi, 2),
                    "total_interest": round(opt_c_emi * opt_c_tenure - opt_c_amount, 2),
                    "description": "Maximize approval - Full eligible amount, shorter tenure."
                })
    except Exception as e:
        print(f"⚠️ Error generating options: {e}")
    
    return {
        "options": options,
        "max_approvable_amount": int(alternative_offer),
        "negotiation_round": state.get("negotiation_round", 1),
        "max_rounds": 3,
        "original_request": int(principal),
        "rejection_reasons": state.get("reasons", []),
        "message": f"We've generated {len(options)} restructured offers. Choose one or let us know your preferred amount."
    }


async def respond_to_offer(session_id: str, action: str, custom_amount: Optional[float] = None, custom_tenure: Optional[int] = None) -> dict:
    """
    Handle user acceptance/rejection of counter-offer or custom proposal.
    - 'accept_option_a' / 'accept_option_b' / 'accept_option_c': User selected predefined option
    - 'accept': User accepted modified terms
    - 'decline': User rejected all offers
    - 'custom': User specifies custom amount/tenure
    """
    state = await get_session(session_id)
    if not state:
        return {"error": "Session not found"}
    
    loan_terms = state.get("loan_terms", {})
    customer = state.get("customer_data", {})
    salary = customer.get("salary", 0)
    existing_emi = customer.get("existing_emi_total", 0)
    rate = loan_terms.get("rate", 12.0)
    
    if action.startswith("accept_option_"):
        option_id = action.split("_")[-1].lower()  # Extract "a", "b", "c"
        # Note: In a real scenario, we'd re-query the options to get the details
        # For now, we accept and proceed to next phase
        return {
            "action": "accepted",
            "revised_loan_terms": None,  # Will be calculated in next step
            "next_step": "kyc_verification",
            "message": "Great! Your revised offer has been accepted. Let's proceed to document verification."
        }
    
    elif action == "decline":
        await update_session(session_id, {
            "persuasion_status": "declined",
            "current_phase": "advisory"  # Route to advisor for guidance
        })
        return {
            "action": "declined",
            "revised_loan_terms": None,
            "next_step": "advisory",
            "message": "Understood. Our financial advisor Priya is here if you'd like guidance on improving your financial profile."
        }
    
    elif action == "custom" and custom_amount and custom_tenure:
        # Validate custom proposal
        custom_emi = _calculate_emi(custom_amount, rate, custom_tenure)
        max_emi_allowed = (settings.MAX_DTI_RATIO * salary) - existing_emi
        
        if custom_emi <= max_emi_allowed:
            new_terms = {
                "principal": custom_amount,
                "tenure": custom_tenure,
                "emi": custom_emi,
                "rate": rate
            }
            await update_session(session_id, {
                "loan_terms": new_terms,
                "persuasion_status": "accepted",
                "current_phase": "kyc_verification"
            })
            return {
                "action": "accepted",
                "revised_loan_terms": new_terms,
                "next_step": "kyc_verification",
                "message": f"✅ Your custom offer for ₹{custom_amount:,} @ {custom_tenure} months is accepted!"
            }
        else:
            return {
                "action": "invalid",
                "revised_loan_terms": None,
                "next_step": "persuasion",
                "message": f"⚠️ This amount would create a DTI of {(custom_emi / salary * 100):.1f}%, beyond our safe limit. Please adjust."
            }
    
    else:
        return {
            "action": "invalid",
            "revised_loan_terms": None,
            "next_step": "persuasion",
            "message": "Invalid action. Please choose an option or specify custom amount/tenure."
        }


async def recalculate_terms(session_id: str, principal: float, tenure_months: int) -> dict:
    """Recalculate EMI and other terms for custom amount/tenure."""
    state = await get_session(session_id)
    if not state:
        return {"error": "Session not found"}
    
    customer = state.get("customer_data", {})
    loan_terms = state.get("loan_terms", {})
    rate = loan_terms.get("rate", 12.0)
    salary = customer.get("salary", 0)
    existing_emi = customer.get("existing_emi_total", 0)
    
    try:
        emi = _calculate_emi(principal, rate, tenure_months)
        total_interest = emi * tenure_months - principal
        total_repayment = principal + total_interest
        
        # Calculate DTI
        new_total_emi = existing_emi + emi
        dti = new_total_emi / salary if salary > 0 else 1.0
        within_threshold = dti <= settings.MAX_DTI_RATIO
        
        return {
            "loan_terms": {
                "principal": principal,
                "tenure": tenure_months,
                "rate": rate,
                "emi": round(emi, 2)
            },
            "emi": round(emi, 2),
            "total_interest": round(total_interest, 2),
            "total_repayment": round(total_repayment, 2),
            "dti_estimate": round(dti, 3),
            "within_threshold": within_threshold,
            "message": f"EMI: ₹{emi:,.2f} | Total Interest: ₹{total_interest:,.2f} | DTI: {dti*100:.1f}%"
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }
