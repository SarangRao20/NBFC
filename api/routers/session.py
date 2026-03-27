"""Session Router — Steps 1, 4, 18."""

from fastapi import APIRouter, HTTPException
from api.schemas.session import SessionStartResponse, SessionStateResponse, SessionEndResponse
from api.services import session_service
from api.core.exceptions import SessionNotFoundError
from api.core.state_manager import get_session, update_session

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


@router.get("/by-phone/{phone}", summary="Search Sessions by Phone Number")
async def get_sessions_by_phone(phone: str):
    """Returns all previous sessions found for this phone number."""
    return await session_service.search_sessions_by_phone(phone)


@router.get("/loan-history/{phone}", summary="Get Complete Loan History")
async def get_loan_history(phone: str):
    """Returns complete loan history for a customer including all applications and sanctions."""
    return await session_service.get_customer_loan_history(phone)


@router.get("/{session_id}/loan-details", summary="Get Detailed Loan Information")
async def get_loan_details(session_id: str):
    """Returns detailed loan information for a specific session."""
    result = await session_service.get_loan_details_by_session(session_id)
    if not result:
        raise SessionNotFoundError(session_id)
    return result
@router.delete("/{session_id}", summary="Delete Session")
async def delete_session(session_id: str):
    """Deletes the specified session from the database."""
    print(f"🗑️ [BACKEND] DELETE request received for session: {session_id}")
    success = await session_service.delete_session(session_id)
    if not success:
        print(f"❌ [BACKEND] Deletion failed for session: {session_id} (Not Found in DB)")
        raise SessionNotFoundError(session_id)
    print(f"✅ [BACKEND] Session {session_id} deleted successfully")
    return {"success": True, "message": f"Session {session_id} deleted."}


@router.post("/{session_id}/select-lender", summary="Select a lender for the session")
async def select_lender(session_id: str, payload: dict):
    """Persist the user's chosen lender into the session state and update loan terms where available."""
    state = await session_service.get_session_state(session_id)
    if not state:
        raise SessionNotFoundError(session_id)

    selected = payload.get("selected_lender_id") or payload.get("lender_id")
    if not selected:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="selected_lender_id is required")

    # Find offer in stored eligible offers
    eligible = state.get("eligible_offers") or state.get("comparison", {}).get("eligible_offers") or []
    chosen = None
    for o in eligible:
        if o.get("lender_id") == selected or o.get("lender_id") == selected.lower():
            chosen = o
            break

    if not chosen:
        # fallback: accept the id but record minimal info
        await update_session(session_id, {
            "selected_lender_id": selected,
            "selected_lender_name": None
        })
        return {"success": True, "message": f"Selected lender {selected} saved (no offer details found)."}

    # Update session with selection and loan terms from offer
    loan_terms = state.get("loan_terms", {})
    updated_terms = {
        **loan_terms, 
        "rate": chosen.get("interest_rate"), 
        "emi": chosen.get("emi"),
        "selected_lender": chosen.get("lender_name")
    }
    
    # ─── PRE-UNDERWRITING CHECK (Soft Reject Detection) ───
    # We run underwriting now to see if this specific lender's rate/EMI triggers a reject
    from agents.underwriting import underwriting_agent_node
    
    # Prepare virtual state for underwriting
    check_state = {
        **state,
        "loan_terms": updated_terms,
        "selected_lender_id": chosen.get("lender_id"),
        "selected_lender_name": chosen.get("lender_name"),
        "selected_interest_rate": chosen.get("interest_rate")
    }
    
    underwriting_result = await underwriting_agent_node(check_state)
    decision = underwriting_result.get("decision", "approve")
    
    # Determine next steps based on decision
    if decision == "soft_reject":
        # If soft-rejected, route back to ARJUN for negotiation immediately
        current_phase = "sales"
        next_agent = "sales_agent"
        action_msg = f"⚠️ [PRE-CHECK] Soft rejected for {chosen.get('lender_name')}. Routing to navigation."
    else:
        # Otherwise proceed to documents
        current_phase = "document"
        next_agent = "document_agent"
        action_msg = f"✅ [PRE-CHECK] Approved for {chosen.get('lender_name')}. Proceeding to documents."

    await update_session(session_id, {
        "selected_lender_id": chosen.get("lender_id"),
        "selected_lender_name": chosen.get("lender_name"),
        "loan_terms": updated_terms,
        "loan_confirmed": True,
        "decision": decision,
        "current_phase": current_phase,
        "next_agent": next_agent,
        "action_log": state.get("action_log", []) + [action_msg]
    })

    return {
        "success": True, 
        "message": f"Selected lender {chosen.get('lender_name')} saved. Output: {decision}", 
        "selected": chosen,
        "decision": decision,
        "next_agent": next_agent
    }
