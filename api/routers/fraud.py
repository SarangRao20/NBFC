"""Fraud Router — Step 10."""

from fastapi import APIRouter
from api.schemas.fraud import FraudCheckResponse
from api.services import fraud_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Fraud Detection"])


@router.post("/{session_id}/fraud-check", response_model=FraudCheckResponse,
             summary="Step 10: Fraud Detection (6-Signal Analysis)")
async def fraud_check(session_id: str):
    """Run 6 independent fraud detection signals:
    1. Name mismatch, 2. Income inflation, 3. Tampered document,
    4. Low OCR confidence, 5. CRM risk flags, 6. Abnormal loan ratio.
    Score >= 0.7 triggers mandatory escalation.
    """
    result = await fraud_service.fraud_check(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result
