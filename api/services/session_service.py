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
    """Step 18: End the session and return summary. Persists outcome to MongoDB CRM."""
    from db.database import users_collection
    
    # Pre-fetch state to know outcome before closing
    pre_state = await get_session(session_id)
    
    state = await end_session(session_id)
    
    if pre_state and pre_state.get("customer_id"):
        customer_id = pre_state["customer_id"]
        customer = pre_state.get("customer_data", {})
        decision = pre_state.get("decision", "incomplete")
        intent = pre_state.get("intent", "checking options")
        phase = pre_state.get("current_phase", "unknown")
        
        # Determine CRM strings
        if decision == "approve":
            principal = pre_state.get("loan_terms", {}).get("principal", 0)
            new_record = f"Sanctioned ₹{principal:,} loan."
            drop_off = ""
        else:
            new_record = f"Inquired about {intent} but didn't conclude."
            drop_off = f"Dropped off at phase: {phase}. Reason: {pre_state.get('reasons', ['User abandoned the flow.'])[0]}"
            
        try:
            # We don't overwrite all past records; we format a clean string
            await users_collection.update_one(
                {"phone": customer.get("phone")},
                {"$set": {
                    "past_records": new_record,
                    "drop_off_history": drop_off
                }}
            )
            print(f"✅ CRM updated for {customer.get('phone')}")
        except Exception as e:
            print(f"⚠️ Failed to update CRM: {e}")

    return {
        "session_id": state["session_id"],
        "status": state["status"],
        "message": "Session ended successfully.",
        "phase_history": state["phase_history"]
    }
async def search_sessions_by_phone(phone: str) -> list:
    """Search for all sessions associated with a phone number."""
    from db.database import sessions_collection
    from api.services.sales_service import _normalize_phone
    
    clean_phone = _normalize_phone(phone)
    # In a real MongoDB this would be a find() query. 
    # Our MockCollection find() returns all, so we filter.
    all_sessions = await sessions_collection.find()
    
    results = []
    for s in all_sessions:
        if s.get("customer_data", {}).get("phone") == clean_phone:
            results.append({
                "session_id": s["session_id"],
                "created_at": s.get("created_at"),
                "status": s.get("status"),
                "current_phase": s.get("current_phase"),
                "last_message": s.get("messages", [-1])[-1] if s.get("messages") else None,
                "state": s # Pass the full document as 'state' for compatibility with sales_service
            })
    
    # Sort by created_at descending
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results
