"""Persuasion Router — Counter-offer generation for soft-rejected loans (Steps 12-15)."""

from fastapi import APIRouter, HTTPException
from api.schemas.persuasion import (
    PersuasionAnalyzeResponse,
    PersuasionSuggestResponse,
    PersuasionRespondRequest,
    PersuasionRespondResponse,
    RecalculateTermsRequest,
    RecalculateTermsResponse,
)
from api.services import persuasion_service
from api.core.exceptions import SessionNotFoundError
from api.core.state_manager import get_session

router = APIRouter(prefix="/session", tags=["Persuasion"])


@router.post("/{session_id}/persuasion/analyze", response_model=PersuasionAnalyzeResponse,
             summary="Step 12: Analyze Rejection Reasons")
async def analyze_rejection(session_id: str):
    """
    Analyze why the loan was soft-rejected.
    Returns rejection reasons, credit score status, and DTI analysis.
    """
    session = await get_session(session_id)
    if not session:
        raise SessionNotFoundError(session_id)
    
    try:
        result = await persuasion_service.analyze_rejection(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return PersuasionAnalyzeResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/persuasion/suggest", response_model=PersuasionSuggestResponse,
             summary="Step 13: Suggest Counter-Offer Options")
async def suggest_fix(session_id: str):
    """
    Generate counter-offer options for soft-rejected loans.
    Returns 3 alternative loan structures (different amount/tenure combinations).
    """
    session = await get_session(session_id)
    if not session:
        raise SessionNotFoundError(session_id)
    
    try:
        result = await persuasion_service.suggest_fix(session_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return PersuasionSuggestResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/persuasion/respond", response_model=PersuasionRespondResponse,
             summary="Step 14: User Accepts/Rejects Counter-Offer")
async def respond_to_offer(session_id: str, request: PersuasionRespondRequest):
    """
    Handle user response to counter-offer:
    - Accept one of the predefined options (accept_option_a/b/c)
    - Decline all offers
    - Propose custom amount/tenure
    """
    session = await get_session(session_id)
    if not session:
        raise SessionNotFoundError(session_id)
    
    try:
        result = await persuasion_service.respond_to_offer(
            session_id,
            request.action,
            request.custom_amount,
            request.custom_tenure
        )
        
        return PersuasionRespondResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/persuasion/recalculate-terms",
             summary="Step 15: Recalculate EMI for Custom Terms")
async def recalculate_terms(session_id: str, request: RecalculateTermsRequest):
    """
    Recalculate EMI and total interest for custom loan amount and tenure.
    Used when user adjusts EMI slider or enters custom values.
    """
    session = await get_session(session_id)
    if not session:
        raise SessionNotFoundError(session_id)
    
    try:
        result = await persuasion_service.recalculate_terms(
            session_id,
            request.principal,
            request.tenure_months
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return RecalculateTermsResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
