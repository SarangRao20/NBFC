"""Payment Router — handles EMI payment requests."""

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
