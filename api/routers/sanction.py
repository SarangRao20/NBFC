"""Sanction Router — Step 16 (Closing & Generation)."""

import base64
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from api.schemas.sanction import SanctionResponse, ESignResponse
from api.services import sanction_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Closing & Sanction"])


@router.post("/{session_id}/sanction", response_model=SanctionResponse,
             summary="Step 16: Sanction Agent — Compile Terms + Generate PDF")
async def generate_sanction(session_id: str):
    """Compile final loan terms and generate a PDF sanction letter.
    For approved loans: generates Sanction Letter.
    For rejected loans: generates Rejection Letter.
    """
    result = await sanction_service.generate_sanction(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.post("/{session_id}/esign-accept", response_model=ESignResponse,
             summary="Step 17: E-Sign Acceptance — Route to Advisory")
async def accept_esign(session_id: str):
    """Handle e-sign acceptance and route to advisory agent.
    This endpoint should be called after user accepts and e-signs the sanction letter.
    """
    result = await sanction_service.process_esign_acceptance(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.get("/{session_id}/download-letter",
            summary="Download Sanction/Rejection Letter")
async def download_letter(session_id: str):
    """Download the generated sanction or rejection letter PDF from MongoDB."""
    result = await sanction_service.get_letter_file(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)

    pdf_b64 = result.get("pdf_b64", "")
    if not pdf_b64:
        raise HTTPException(status_code=404, detail="Letter not yet generated")

    filename = result.get("filename", f"letter_{session_id}.pdf")
    pdf_bytes = base64.b64decode(pdf_b64)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
        }
    )


@router.post("/{session_id}/disburse", summary="Trigger IMPS Disbursal of Loan Funds")
async def disburse_funds(session_id: str):
    """Initiates instant IMPS transfer for e-signed loan facility."""
    from api.services.disbursement_service import initiate_imps_transfer
    result = await initiate_imps_transfer(session_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Disbursement failed"))
    return result

