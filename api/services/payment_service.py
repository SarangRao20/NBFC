"""Payment Service — handles EMI payments with Razorpay simulation and updates session state."""

import asyncio
import hashlib
import hmac
import json
import random
from datetime import datetime, timedelta
from typing import Optional
from api.core.state_manager import get_session, update_session
from api.core.websockets import manager


# ─── RAZORPAY SIMULATION ──────────────────────────────────────────────────────

RAZORPAY_KEY_ID = "rzp_live_simulated_key"
RAZORPAY_KEY_SECRET = "simulated_secret_key"

# In-memory order store
_razorpay_orders: dict = {}


async def create_razorpay_order(session_id: str, amount_paise: int, currency: str = "INR") -> dict:
    """Simulate Razorpay order creation.

    Args:
        session_id: Current session ID
        amount_paise: Amount in paise (₹1 = 100 paise)
        currency: Currency code (default INR)

    Returns: Simulated Razorpay order response
    """
    order_id = f"order_{session_id[:8]}_{random.randint(100000, 999999)}"
    receipt_id = f"receipt_{session_id[:8]}"

    order_data = {
        "id": order_id,
        "entity": "order",
        "amount": amount_paise,
        "amount_paid": 0,
        "amount_due": amount_paise,
        "currency": currency,
        "receipt": receipt_id,
        "status": "created",
        "attempts": 0,
        "created_at": int(datetime.now().timestamp()),
        "notes": {
            "session_id": session_id,
            "policy": "NBFC_EMI"
        }
    }

    _razorpay_orders[order_id] = order_data
    return order_data


async def verify_razorpay_payment(order_id: str, payment_id: str, signature: str) -> dict:
    """Verify Razorpay payment signature.

    Simulates the HMAC-SHA256 signature verification that Razorpay uses.

    Args:
        order_id: Razorpay order ID
        payment_id: Razorpay payment ID
        signature: Razorpay signature to verify

    Returns: Verification result
    """
    # Simulate signature generation for verification
    expected_payload = f"{order_id}|{payment_id}"
    expected_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        expected_payload.encode(),
        hashlib.sha256
    ).hexdigest()

    is_valid = hmac.compare_digest(expected_signature, signature)

    if is_valid:
        if order_id in _razorpay_orders:
            _razorpay_orders[order_id]["status"] = "paid"
            _razorpay_orders[order_id]["amount_paid"] = _razorpay_orders[order_id]["amount"]

    return {
        "verified": is_valid,
        "order_id": order_id,
        "payment_id": payment_id,
    }


# ─── EMI PAYMENT PROCESSING ───────────────────────────────────────────────────


async def process_emi_payment(session_id: str, razorpay_payment_id: Optional[str] = None) -> dict:
    """Process an EMI payment for the given session.

    Supports both direct processing and Razorpay-integrated payment.
    
    Args:
        session_id: Session ID
        razorpay_payment_id: Optional Razorpay payment ID for verified payments

    Returns: Payment result
    """
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

    # If Razorpay payment ID provided, verify it
    if razorpay_payment_id:
        # In production, verify with Razorpay API
        if not razorpay_payment_id.startswith("pay_"):
            return {
                "success": False,
                "message": "Invalid Razorpay payment ID. Payment verification failed."
            }

    # Simulate payment processing
    new_payments_made = payments_made + 1
    remaining_balance = max(0, (tenure - new_payments_made) * emi)

    updated_terms = {
        **terms,
        "payments_made": new_payments_made,
        "last_payment_date": datetime.now().strftime("%Y-%m-%d"),
        "remaining_balance": round(remaining_balance, 2),
    }

    if razorpay_payment_id:
        updated_terms["razorpay_payment_id"] = razorpay_payment_id
        updated_terms["payment_method"] = "razorpay"
    else:
        updated_terms["payment_method"] = "direct"

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
        except Exception:
            updated_terms["next_emi_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    else:
        updated_terms["next_emi_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    await update_session(session_id, {"loan_terms": updated_terms})

    # Persist payment to MongoDB loan_applications_collection
    try:
        from db.database import loan_applications_collection
        await loan_applications_collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "payments_made": new_payments_made,
                    "remaining_balance": round(remaining_balance, 2),
                    "last_payment_date": updated_terms["last_payment_date"],
                    "next_emi_date": updated_terms["next_emi_date"]
                }
            }
        )
        print(f"📊 Persisted EMI payment in MongoDB for session {session_id}")
    except Exception as e:
        print(f"⚠️ Failed to update DB loan record on payment: {e}")

    # Broadcast update to frontend
    asyncio.create_task(manager.broadcast_to_session(session_id, {
        "type": "PHASE_UPDATE",
        "phase": state.get("current_phase", "payment")
    }))

    payment_method = "via Razorpay" if razorpay_payment_id else "direct"
    return {
        "success": True,
        "message": f"Payment of ₹{emi:,.2f} successful {payment_method}!",
        "loan_terms": updated_terms,
        "razorpay": {
            "order_id": next((k for k, v in _razorpay_orders.items() if v.get("notes", {}).get("session_id") == session_id), None),
            "payment_id": razorpay_payment_id
        } if razorpay_payment_id else None,
    }


async def initiate_razorpay_payment(session_id: str) -> dict:
    """Start a Razorpay payment flow for the current EMI.

    Creates a Razorpay order and returns the necessary details
    for the frontend to open the Razorpay checkout.

    Args:
        session_id: Current session ID

    Returns: Razorpay order creation response with checkout details
    """
    state = await get_session(session_id)
    if not state:
        return {"success": False, "message": "Session not found."}

    terms = state.get("loan_terms", {})
    emi = terms.get("emi", 0)
    payments_made = terms.get("payments_made", 0)
    tenure = terms.get("tenure", 0)

    if payments_made >= tenure:
        return {"success": False, "message": "Loan is already fully repaid."}

    if emi <= 0:
        return {"success": False, "message": "No active EMI found."}

    amount_paise = int(emi * 100)
    order = await create_razorpay_order(session_id, amount_paise)

    return {
        "success": True,
        "razorpay_key": RAZORPAY_KEY_ID,
        "amount": amount_paise,
        "currency": "INR",
        "order_id": order["id"],
        "prefill": {
            "contact": state.get("customer_data", {}).get("phone", ""),
            "name": state.get("customer_data", {}).get("name", ""),
            "email": state.get("customer_data", {}).get("email", ""),
        },
        "notes": {
            "session_id": session_id,
            "emi_number": payments_made + 1,
            "total_emis": tenure,
        },
        "message": f"Razorpay order created for ₹{emi:,.2f}. Open checkout to complete payment.",
    }


# ─── COOLING-OFF SETTLEMENT ──────────────────────────────────────────────────


def calculate_cooling_off_settlement(principal: float, annual_rate: float, days_held: int, processing_fee: float) -> float:
    """Apply cooling-off formula: P + (P * R/365 * t) + PF."""
    from utils.financial_rules import calculate_cooling_off_settlement as cooling_func
    return cooling_func(principal, annual_rate, days_held, processing_fee)
