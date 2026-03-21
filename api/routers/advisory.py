"""Advisory Router — Step 17."""

from fastapi import APIRouter
from api.schemas.advisory import AdvisoryResponse
from api.services import advisory_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Advisory"])


@router.post("/{session_id}/advisory", response_model=AdvisoryResponse,
             summary="Step 17: Advisory Agent — Personalized Financial Advice")
async def generate_advisory(session_id: str):
    """Generate personalized financial advice based on the loan decision.
    Approved: congratulations + cross-sell.
    Rejected (credit): 90-day CIBIL improvement plan.
    Rejected (DTI): restructuring suggestions.
    Rejected (fraud): branch visit instructions.
    """
    result = await advisory_service.generate_advisory(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result
