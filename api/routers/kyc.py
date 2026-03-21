"""KYC Router — Step 9."""

from fastapi import APIRouter
from api.schemas.kyc import KYCVerifyResponse
from api.services import kyc_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["KYC Verification"])


@router.post("/{session_id}/kyc-verify", response_model=KYCVerifyResponse,
             summary="Step 9: KYC Verification")
async def kyc_verify(session_id: str):
    """Cross-check customer name against document-extracted name.
    Checks for: name mismatch, tampered documents, unverified documents.
    """
    result = await kyc_service.kyc_verify(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result
