"""Payment Service — handles EMI payments and updates session state."""

import asyncio
from datetime import datetime
from api.core.state_manager import get_session, update_session
from api.core.websockets import manager

async def process_emi_payment(session_id: str) -> dict:
    """Process an EMI payment for the given session."""
    state = await get_session(session_id)
    if not state:
        return None

    terms = state.get("loan_terms", {})
    principal = terms.get("principal", 0)
    emi = terms.get("emi", 0)
    payments_made = terms.get("payments_made", 0)
    tenure = terms.get("tenure", 0)
    
    if payments_made >= tenure:
        return {"success": False, "message": "Loan is already fully repaid."}

    # Simulate payment processing
    new_payments_made = payments_made + 1
    remaining_balance = max(0, (tenure - new_payments_made) * emi)
    
    updated_terms = {
        **terms,
        "payments_made": new_payments_made,
        "last_payment_date": datetime.now().strftime("%Y-%m-%d"),
        "remaining_balance": round(remaining_balance, 2)
    }
    
    # Update next EMI date
    next_emi_date = terms.get("next_emi_date")
    if next_emi_date and isinstance(next_emi_date, str):
        try:
            curr_date = datetime.strptime(next_emi_date, "%Y-%m-%d")
            # Move to same day next month
            if curr_date.month == 12:
                next_date = curr_date.replace(year=curr_date.year + 1, month=1)
            else:
                next_date = curr_date.replace(month=curr_date.month + 1)
            updated_terms["next_emi_date"] = next_date.strftime("%Y-%m-%d")
        except:
            pass

    await update_session(session_id, {"loan_terms": updated_terms})
    
    # Broadcast update to frontend
    asyncio.create_task(manager.broadcast_to_session(session_id, {
        "type": "PHASE_UPDATE",
        "phase": state.get("current_phase", "payment")
    }))
    
    return {
        "success": True, 
        "message": f"Payment of ₹{emi:,.2f} successful!",
        "loan_terms": updated_terms
    }
