"""Session Router — Steps 1, 4, 18."""

from fastapi import APIRouter, HTTPException
from api.schemas.session import SessionStartResponse, SessionStateResponse, SessionEndResponse
from api.services import session_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Session"])


@router.post("/start", response_model=SessionStartResponse,
             summary="Step 1: User Enters Chat → Create Session")
async def start_session():
    """Creates a new loan processing session. This is the entry point of the workflow.
    Returns a session_id to use in all subsequent calls.
    """
    result = await session_service.start_new_session()
    return result


@router.get("/{session_id}/state", response_model=SessionStateResponse,
            summary="Step 4: State Update — Get Full Session State")
async def get_state(session_id: str):
    """Returns the complete current state of the session, including all data
    collected and decisions made so far.
    """
    state = await session_service.get_session_state(session_id)
    if not state:
        raise SessionNotFoundError(session_id)
    return state


@router.post("/{session_id}/end", response_model=SessionEndResponse,
             summary="Step 18: End Session")
async def end_session(session_id: str):
    """Ends the session and returns the complete phase history."""
    state = await session_service.get_session_state(session_id)
    if not state:
        raise SessionNotFoundError(session_id)
    return await session_service.end_active_session(session_id)
