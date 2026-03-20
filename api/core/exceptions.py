"""Custom exceptions for the NBFC FastAPI backend."""

from fastapi import HTTPException, status


class SessionNotFoundError(HTTPException):
    def __init__(self, session_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found. Start a new session via POST /session/start."
        )


class PhaseSequenceError(HTTPException):
    def __init__(self, current_phase: str, required_phase: str, endpoint: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Workflow sequence violation at '{endpoint}'. "
                f"Current phase: '{current_phase}', required: '{required_phase}'. "
                f"Complete prior steps first."
            )
        )


class DocumentNotUploadedError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document uploaded. Upload a document via POST /session/{id}/extract-ocr first."
        )


class InvalidDecisionError(HTTPException):
    def __init__(self, decision: str, expected: list[str]):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Decision is '{decision}', expected one of {expected}."
        )
