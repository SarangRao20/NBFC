"""Payment Router — handles EMI payment requests via Razorpay."""

from fastapi import APIRouter, HTTPException
from api.services import payment_service
from api.schemas.payment import (
    CreateOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Payment"])


@router.post("/{session_id}/create-emi-order", response_model=CreateOrderResponse,
             summary="Create Razorpay Order for EMI payment")
async def create_emi_order(session_id: str):
    """Creates a Razorpay Order for the next EMI.
    
    Returns the order_id and key_id needed to open Razorpay Checkout on the frontend.
    """
    result = await payment_service.create_emi_order(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/{session_id}/verify-emi-payment", response_model=VerifyPaymentResponse,
             summary="Verify Razorpay payment after checkout")
async def verify_emi_payment(session_id: str, body: VerifyPaymentRequest):
    """Verify the payment signature returned by Razorpay Checkout and process the EMI.
    
    Called by the frontend after the user completes the Razorpay Checkout flow.
    """
    result = await payment_service.verify_emi_payment(
        session_id=session_id,
        razorpay_payment_id=body.razorpay_payment_id,
        razorpay_order_id=body.razorpay_order_id,
        razorpay_signature=body.razorpay_signature,
    )
    if result is None:
        raise SessionNotFoundError(session_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/{session_id}/pay-emi", summary="Pay the next EMI (legacy/fallback)")
async def pay_emi(session_id: str):
    """Processes the next EMI payment using the legacy simulated flow.
    
    For the Razorpay flow, use POST /create-emi-order + POST /verify-emi-payment instead.
    """
    result = await payment_service.process_emi_payment(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
