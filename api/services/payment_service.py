"""Payment Service — handles EMI payments via Razorpay and updates session state."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from api.core.state_manager import get_session, update_session
from api.core.websockets import manager
from api.config import get_settings
from api.services.razorpay_service import get_razorpay_service

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_emi_order(session_id: str) -> Optional[dict]:
    """Create a Razorpay Order for the next EMI payment.
    
    Returns checkout configuration for the frontend Razorpay widget.
    """
    state = await get_session(session_id)
    if not state:
        return None

    terms = state.get("loan_terms", {})
    customer = state.get("customer_data", {})
    emi = terms.get("emi") or 0
    payments_made = terms.get("payments_made") or 0
    tenure = terms.get("tenure") or 0

    if payments_made >= tenure:
        return {"success": False, "message": "Loan is already fully repaid."}

    if emi <= 0:
        return {"success": False, "message": "No active EMI found for this session."}

    razorpay = get_razorpay_service()

    if not razorpay.is_configured:
        # Fallback: return mock order for development
        mock_order_id = f"order_mock_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.warning(f"⚠️ Razorpay not configured — returning mock order: {mock_order_id}")
        return {
            "success": True,
            "order_id": mock_order_id,
            "amount": emi,
            "amount_paise": int(round(emi * 100)),
            "currency": "INR",
            "key_id": "rzp_test_1234567890abcdef",  # Valid test key format
            "customer_name": customer.get("name", ""),
            "customer_email": customer.get("email", ""),
            "customer_phone": customer.get("phone", ""),
            "session_id": session_id,
            "description": f"EMI Payment #{payments_made + 1} of {tenure}",
            "mock": True,
            "message": "Mock order created for testing",
        }

    try:
        # Create receipt ID (max 40 chars per Razorpay requirement)
        receipt_id = f"emi_{session_id[:30]}_{payments_made + 1}"
        if len(receipt_id) > 40:
            receipt_id = f"emi_{session_id[:25]}_{payments_made + 1}"
        
        order = razorpay.create_order(
            amount=emi,
            currency="INR",
            receipt=receipt_id,
            notes={
                "session_id": session_id,
                "emi_number": payments_made + 1,
                "total_emis": tenure,
                "type": "emi_payment",
            },
        )

        return {
            "success": True,
            "order_id": order["id"],
            "amount": emi,
            "amount_paise": order["amount"],
            "currency": order.get("currency", "INR"),
            "key_id": settings.RAZORPAY_KEY_ID,
            "customer_name": customer.get("name", ""),
            "customer_email": customer.get("email", ""),
            "customer_phone": customer.get("phone", ""),
            "session_id": session_id,
            "description": f"EMI Payment #{payments_made + 1} of {tenure}",
            "mock": False,
        }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Failed to create EMI order: {error_msg}")
        logger.error(f"   Session ID: {session_id}")
        logger.error(f"   EMI Amount: {emi}")
        logger.error(f"   Receipt ID: {receipt_id if 'receipt_id' in locals() else 'N/A'}")
        return {"success": False, "message": f"Failed to create payment order: {error_msg}"}


async def verify_emi_payment(
    session_id: str,
    razorpay_payment_id: str,
    razorpay_order_id: str,
    razorpay_signature: str,
) -> Optional[dict]:
    """Verify Razorpay payment signature and process the EMI payment.
    
    This is called after the user completes payment via Razorpay Checkout on the frontend.
    """
    state = await get_session(session_id)
    if not state:
        return None

    razorpay = get_razorpay_service()

    # ── 1. Verify Payment Signature ──────────────────────────────────────────
    if razorpay.is_configured:
        is_valid = razorpay.verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )
        if not is_valid:
            logger.warning(f"❌ Payment signature invalid for session {session_id}")
            return {
                "success": False,
                "message": "Payment verification failed. Signature mismatch.",
                "payment_id": razorpay_payment_id,
            }
    else:
        # Mock mode — skip verification
        logger.warning("⚠️ Razorpay not configured — skipping signature verification")

    # ── 2. Process the EMI Payment (update loan state) ───────────────────────
    terms = state.get("loan_terms", {})
    customer = state.get("customer_data", {})

    payments_made = terms.get("payments_made") or 0
    tenure = terms.get("tenure") or 0
    emi = terms.get("emi") or 0

    if payments_made >= tenure:
        return {"success": False, "message": "Loan is already fully repaid.", "payment_id": razorpay_payment_id}

    new_payments_made = payments_made + 1
    remaining_balance = max(0, (tenure - new_payments_made) * emi)

    updated_terms = {
        **terms,
        "payments_made": new_payments_made,
        "last_payment_date": datetime.now().strftime("%Y-%m-%d"),
        "remaining_balance": round(remaining_balance, 2),
        "last_razorpay_payment_id": razorpay_payment_id,
        "last_razorpay_order_id": razorpay_order_id,
    }

    # Calculate next EMI date
    next_emi_date = terms.get("next_emi_date")
    if next_emi_date and isinstance(next_emi_date, str):
        try:
            curr_date = datetime.strptime(next_emi_date, "%Y-%m-%d")
            if curr_date.month == 12:
                next_date = curr_date.replace(year=curr_date.year + 1, month=1)
            else:
                next_date = curr_date.replace(month=curr_date.month + 1)
            updated_terms["next_emi_date"] = next_date.strftime("%Y-%m-%d")
        except Exception:
            pass

    # ── 3. Credit Score Boost ────────────────────────────────────────────────
    old_score = customer.get("credit_score", 700) or 700
    new_score = min(old_score + 10, 850)
    customer["credit_score"] = new_score

    # ── 4. Check for Loan Completion ─────────────────────────────────────────
    is_completed = new_payments_made >= tenure
    if is_completed:
        updated_terms["is_closed"] = True
        score_boost = 50
        new_score = min(old_score + score_boost, 900)
        customer["credit_score"] = new_score

        old_limit = customer.get("pre_approved_limit", 25000) or 25000
        new_limit = old_limit + int(old_limit * 0.5)
        customer["pre_approved_limit"] = new_limit

    # ── 5. Save to Session ───────────────────────────────────────────────────
    await update_session(session_id, {
        "loan_terms": updated_terms,
        "customer_data": customer,
    })

    # ── 6. Sync to MongoDB ───────────────────────────────────────────────────
    try:
        from db.database import loan_applications_collection
        update_fields = {
            "payments_made": new_payments_made,
            "remaining_balance": updated_terms.get("remaining_balance"),
            "next_emi_date": updated_terms.get("next_emi_date", ""),
            "last_payment_date": updated_terms["last_payment_date"],
            "last_razorpay_payment_id": razorpay_payment_id,
        }
        if is_completed:
            update_fields["status"] = "Closed"
            update_fields["is_closed"] = True
            update_fields["closed_at"] = datetime.now().isoformat()

        await loan_applications_collection.update_one(
            {"session_id": session_id},
            {"$set": update_fields}
        )
    except Exception as e:
        logger.error(f"⚠️ Failed to sync payment to DB: {e}")

    # ── 7. Store Razorpay Transaction ────────────────────────────────────────
    try:
        from db.database import razorpay_transactions_collection
        await razorpay_transactions_collection.insert_one({
            "payment_id": razorpay_payment_id,
            "order_id": razorpay_order_id,
            "session_id": session_id,
            "amount": emi,
            "type": "emi_payment",
            "emi_number": new_payments_made,
            "status": "verified",
            "verified_at": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"⚠️ Failed to store transaction record: {e}")

    # ── 8. Broadcast to Frontend ─────────────────────────────────────────────
    asyncio.create_task(manager.broadcast_to_session(session_id, {
        "type": "PAYMENT_SUCCESS",
        "payment_id": razorpay_payment_id,
        "emi_number": new_payments_made,
        "remaining": tenure - new_payments_made,
        "new_credit_score": new_score,
    }))

    if is_completed:
        completion_msg = (
            f"🎉 Loan fully repaid! Credit Score boosted to {new_score}. "
            f"Pre-approved limit increased to ₹{customer.get('pre_approved_limit', 0):,}."
        )
    else:
        completion_msg = (
            f"EMI #{new_payments_made} of {tenure} paid successfully. "
            f"Next due: {updated_terms.get('next_emi_date', 'TBD')}. "
            f"Credit Score: {new_score} (↑ 10 pts)."
        )

    return {
        "success": True,
        "message": completion_msg,
        "payment_id": razorpay_payment_id,
        "loan_terms": updated_terms,
        "is_completed": is_completed,
    }


async def process_emi_payment(session_id: str) -> dict:
    """Legacy endpoint: Process an EMI payment for the given session.
    
    This is the MOCK fallback used when Razorpay Checkout is not available.
    For the real flow, use create_emi_order() + verify_emi_payment().
    """
    state = await get_session(session_id)
    if not state:
        return None

    terms = state.get("loan_terms", {})
    principal = terms.get("principal") or 0
    emi = terms.get("emi") or 0
    payments_made = terms.get("payments_made") or 0
    tenure = terms.get("tenure") or 0
    
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


def calculate_cooling_off_settlement(principal: float, annual_rate: float, days_held: int, processing_fee: float) -> float:
    """Apply cooling-off formula: P + (P × R/365 × t) + PF"""
    from utils.financial_rules import calculate_cooling_off_settlement as cooling_func
    return cooling_func(principal, annual_rate, days_held, processing_fee)
