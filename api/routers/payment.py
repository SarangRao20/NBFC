"""Payment Router — handles EMI payment and Razorpay requests."""

from fastapi import APIRouter, HTTPException
from api.services import payment_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Payment"])

@router.post("/{session_id}/pay-emi", summary="Pay the next EMI")
async def pay_emi(session_id: str):
    """Processes the next EMI payment for the active loan in the session."""
    result = await payment_service.process_emi_payment(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@router.post("/{session_id}/razorpay/initiate", summary="Initiate Razorpay payment")
async def initiate_razorpay(session_id: str):
    """Create a Razorpay order for the next EMI payment."""
    result = await payment_service.initiate_razorpay_payment(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@router.post("/{session_id}/razorpay/verify", summary="Verify Razorpay payment")
async def verify_razorpay(order_id: str, payment_id: str, signature: str):
    """Verify Razorpay payment signature and process EMI payment."""
    verification = await payment_service.verify_razorpay_payment(order_id, payment_id, signature)
    if not verification.get("verified"):
        raise HTTPException(status_code=400, detail="Payment verification failed.")
    return verification

@router.post("/{session_id}/pay-emi-razorpay", summary="Pay EMI via Razorpay")
async def pay_emi_razorpay(session_id: str, razorpay_payment_id: str):
    """Process EMI payment with verified Razorpay payment ID."""
    result = await payment_service.process_emi_payment(session_id, razorpay_payment_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result
