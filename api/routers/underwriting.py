"""Underwriting Router — Step 11 (Decision Engine)."""

from fastapi import APIRouter
from api.schemas.underwriting import UnderwritingResponse
from api.services import underwriting_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Underwriting / Decision Engine"])


@router.post("/{session_id}/underwrite", response_model=UnderwritingResponse,
             summary="Step 11: Underwriting Agent — Full Decision Engine")
async def underwrite(session_id: str):
    """Evaluates loan eligibility via the decision tree:
    1. Credit Score >= 700?
    2. Check Loan Limit (Low/Medium/High exposure)
    3. Calculate DTI ratio
    4. Decision: approve / soft_reject / reject / pending_docs

    soft_reject triggers the Persuasion Loop (Steps 12-15).
    reject routes to Advisory (Step 17).
    approve routes to Sanction (Step 16).
    """
    result = await underwriting_service.underwrite(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result
