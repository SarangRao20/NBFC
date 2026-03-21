"""Sanction Router — Step 16 (Closing & Generation)."""

from fastapi import APIRouter
from api.schemas.sanction import SanctionResponse
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
