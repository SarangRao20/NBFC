"""Session Service — manages session lifecycle (Steps 1, 4, 18)."""

from api.core.state_manager import create_session, get_session, end_session, advance_phase


async def start_new_session() -> dict:
    """Step 1: User Enters Chat → Master Router creates a new session."""
    state = await create_session()
    return {
        "session_id": state["session_id"],
        "status": state["status"],
        "current_phase": state["current_phase"],
        "message": "Session started. Proceed to POST /session/{id}/identify-customer."
    }


async def get_session_state(session_id: str) -> dict:
    """Step 4: Return the full current session state."""
    state = await get_session(session_id)
    if not state:
        return None
    return state


async def end_active_session(session_id: str) -> dict:
    """Step 18: End the session and return summary."""
    state = await end_session(session_id)
    return {
        "session_id": state["session_id"],
        "status": state["status"],
        "message": "Session ended successfully.",
        "phase_history": state["phase_history"]
    }
