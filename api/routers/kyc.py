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


@router.post("/{session_id}/digilocker-fetch", summary="1-Click DigiLocker Auto-Fetch Aadhaar & PAN")
async def digilocker_fetch(session_id: str, payload: dict = None):
    """Initiates 1-click DigiLocker verification and updates document verification state."""
    from mock_apis.digilocker_api import verify_digilocker_otp
    from api.core.state_manager import get_session, update_session

    payload = payload or {}
    aadhaar = payload.get("aadhaar", "987654321012")
    otp = payload.get("otp", "123456")

    state = await get_session(session_id)
    if not state:
        raise SessionNotFoundError(session_id)

    res = verify_digilocker_otp("dl_session_1234", otp, aadhaar)
    if res.get("success"):
        docs = state.get("documents", {})
        customer = state.get("customer_data", {})
        
        updated_docs = {
            **docs,
            "verified": True,
            "document_type": "DigiLocker Aadhaar & PAN XML",
            "confidence": 0.99,
            "digilocker_data": res.get("documents")
        }
        
        await update_session(session_id, {
            "documents": updated_docs,
            "kyc_status": "verified",
            "documents_uploaded": True
        })

    return res

