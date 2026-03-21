"""Persuasion Router — Steps 12, 13, 14, 15 (Persuasion Loop / Closer Mode)."""

from fastapi import APIRouter
from api.schemas.persuasion import (
    PersuasionAnalyzeResponse, PersuasionSuggestResponse,
    PersuasionRespondRequest, PersuasionRespondResponse,
    RecalculateTermsRequest, RecalculateTermsResponse,
)
from api.services import persuasion_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Persuasion Loop"])


@router.post("/{session_id}/persuasion/analyze", response_model=PersuasionAnalyzeResponse,
             summary="Step 12: Analyze Reason for Rejection")
async def analyze_rejection(session_id: str):
    """Parse the soft rejection to identify what can be fixed.
    Shows current DTI vs threshold and confirms credit eligibility.
    """
    result = await persuasion_service.analyze_rejection(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.post("/{session_id}/persuasion/suggest", response_model=PersuasionSuggestResponse,
             summary="Step 13: Suggest Fix — Reduce Amount or Increase Tenure")
async def suggest_fix(session_id: str):
    """Generate restructured loan options:
    - Option A: Reduce amount (same tenure)
    - Option B/C: Extend tenure (same amount)
    Capped at MAX_NEGOTIATION_ROUNDS.
    """
    result = await persuasion_service.suggest_fix(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.post("/{session_id}/persuasion/respond", response_model=PersuasionRespondResponse,
             summary="Step 14: User Accepts Modified Offer?")
async def respond_to_offer(session_id: str, req: PersuasionRespondRequest):
    """Process user's response:
    - 'accept_option_a', 'accept_option_b': Select a specific option
    - 'accept': Accept the recommended (first) option
    - 'decline': Decline all → route to Advisory

    On accept: resets decision and returns to Underwriting for re-evaluation.
    """
    result = await persuasion_service.process_response(
        session_id, req.action, req.custom_amount, req.custom_tenure
    )
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.post("/{session_id}/recalculate-terms", response_model=RecalculateTermsResponse,
             summary="Step 15: Recalculate Loan Terms")
async def recalculate_terms(session_id: str, req: RecalculateTermsRequest):
    """Recalculate EMI and DTI with new principal/tenure.
    Used after accepting a modified offer.
    """
    result = await persuasion_service.recalculate_terms(
        session_id, req.principal, req.tenure_months, req.rate
    )
    if result is None:
        raise SessionNotFoundError(session_id)
    return result
