"""Session Service — manages session lifecycle (Steps 1, 4, 18)."""

from api.core.state_manager import create_session, get_session, end_session, advance_phase
from api.core.redis_cache import get_cache


async def start_new_session() -> dict:
    """Step 1: User Enters Chat → Master Router creates a new session."""
    cache = await get_cache()
    
    state = await create_session()
    
    # Cache the session for performance
    await cache.set_session(state["session_id"], state)
    
    return {
        "session_id": state["session_id"],
        "status": state["status"],
        "current_phase": state["current_phase"],
        "message": "Session started. Proceed to POST /session/{id}/identify-customer."
    }


def _clean_dict(d):
    """Recursively removes _id and other non-JSON-serializable types."""
    if isinstance(d, list):
        return [_clean_dict(v) for v in d]
    if isinstance(d, dict):
        return {k: _clean_dict(v) for k, v in d.items() if k != "_id"}
    return d

def _deep_merge(base: dict, update: dict) -> dict:
    """Recursively merges two dictionaries."""
    for key, value in update.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base

async def get_session_state(session_id: str) -> dict:
    """Step 4: Return full current session state (Bypassing Redis for Sidebar Sync)."""
    # Always read from database to ensure sidebar is live
    state = await get_session(session_id)
    if not state:
        return None
        
    # Merge with default state to ensure all Pydantic fields are present
    from api.core.state_manager import _default_state
    full_state = _default_state()
    
    # Use deep merge to preserve nested fields like customer_data.name
    merged = _deep_merge(full_state, state)
    # Sanitize for JSON
    return _clean_dict(merged)





async def end_active_session(session_id: str) -> dict:
    """Step 18: End session and return summary. Persists outcome to MongoDB CRM."""
    from db.database import users_collection
    cache = await get_cache()
    
    # Pre-fetch state to know outcome before closing
    pre_state = await get_session_state(session_id)
    
    state = await end_session(session_id)
    
    # Clear from cache
    await cache.delete_session(session_id)
    
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
    """Search for all sessions associated with a phone number (No Cache)."""
    from db.database import sessions_collection
    from api.services.sales_service import _normalize_phone
    
    clean_phone = _normalize_phone(phone)
    # results = await cache.get(f"sessions_by_phone:{clean_phone}")
    # if results: return results
    
    # In a real MongoDB this would be a find() query. 
    # Our MockCollection find() returns all, so we filter.
    all_sessions = await sessions_collection.find()
    
    results = []
    for s in all_sessions:
        if s.get("customer_data", {}).get("phone") == clean_phone:
            # Clean for JSON serialization (remove ObjectId)
            s_clean = s.copy()
            if "_id" in s_clean: s_clean["_id"] = str(s_clean["_id"])
            
            results.append({
                "session_id": s_clean["session_id"],
                "created_at": s_clean.get("created_at"),
                "status": s_clean.get("status"),
                "current_phase": s_clean.get("current_phase"),
                "last_message": s_clean.get("messages", [-1])[-1] if s_clean.get("messages") else None,
                "state": s_clean 
            })

    
    # Sort by created_at descending
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Cache for 15 minutes
    await cache.set(cache_key, results, ttl=900)
    
    return results


async def get_customer_loan_history(phone: str) -> dict:
    """Get complete loan history for a customer including past applications and sanctions."""
    from db.database import loan_applications_collection, users_collection
    from api.services.sales_service import _normalize_phone
    cache = await get_cache()
    
    clean_phone = _normalize_phone(phone)
    
    # Check cache first
    cache_key = f"loan_history:{clean_phone}"
    cached_history = await cache.get(cache_key)
    
    if cached_history:
        print(f"🎯 Loan history cache HIT for {phone}")
        return cached_history
    
    print(f"⚡ Loan history cache MISS for {phone}")
    
    # Get customer profile
    customer = await users_collection.find_one({"phone": clean_phone})
    
    # Get all loan applications
    all_applications = await loan_applications_collection.find()
    customer_applications = []
    
    for app in all_applications:
        if app.get("phone") == clean_phone:
            customer_applications.append({
                "session_id": app.get("session_id"),
                "amount": app.get("amount", 0),
                "loan_type": app.get("loan_type", ""),
                "interest_rate": app.get("interest_rate", 0),
                "tenure": app.get("tenure", 0),
                "emi": app.get("emi", 0),
                "status": app.get("status", "Unknown"),
                "reasons": app.get("reasons", []),
                "created_at": app.get("created_at", ""),
                "pdf_path": app.get("pdf_path", ""),
                "email_sent": app.get("email_sent", False)
            })
    
    # Sort by created_at descending
    customer_applications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Get session history
    sessions = await search_sessions_by_phone(phone)
    
    result = {
        "customer": customer,
        "loan_applications": customer_applications,
        "session_history": sessions,
        "total_applications": len(customer_applications),
        "approved_loans": len([a for a in customer_applications if a.get("status") == "Approved"]),
        "rejected_applications": len([a for a in customer_applications if a.get("status") == "Rejected"]),
        "summary": {
            "has_approved_loans": any(a.get("status") == "Approved" for a in customer_applications),
            "has_rejections": any(a.get("status") == "Rejected" for a in customer_applications),
            "last_application": customer_applications[0] if customer_applications else None,
            "past_records": customer.get("past_records", "") if customer else "",
            "drop_off_history": customer.get("drop_off_history", "") if customer else ""
        }
    }
    
    # Cache for 30 minutes
    await cache.set(cache_key, result, ttl=1800)
    
    return result


async def get_loan_details_by_session(session_id: str) -> dict:
    """Get detailed loan information for a specific session with cache."""
    cache = await get_cache()
    
    # Check cache first
    cache_key = f"loan_details:{session_id}"
    cached_details = await cache.get(cache_key)
    
    if cached_details:
        print(f"🎯 Loan details cache HIT for {session_id}")
        return cached_details
    
    print(f"⚡ Loan details cache MISS for {session_id}")
    
    state = await get_session(session_id)
    if not state:
        return None
    
    # Get corresponding loan application record
    from db.database import loan_applications_collection
    loan_app = await loan_applications_collection.find_one({"session_id": session_id})
    
    result = {
        "session_state": state,
        "loan_application": loan_app,
        "customer_data": state.get("customer_data", {}),
        "loan_terms": state.get("loan_terms", {}),
        "decision": state.get("decision", ""),
        "sanction_pdf": state.get("sanction_pdf", ""),
        "phase_history": state.get("phase_history", []),
        "documents": state.get("documents", {}),
        "dti_ratio": state.get("dti_ratio", 0),
        "reasons": state.get("reasons", [])
    }
    
    # Cache for 1 hour
    await cache.set(cache_key, result, ttl=3600)
    
    return result


async def check_existing_customer(phone: str) -> dict:
    """Check if customer exists and return their basic info with cache."""
    from db.database import users_collection
    from api.services.sales_service import _normalize_phone
    cache = await get_cache()
    
    clean_phone = _normalize_phone(phone)
    
    # Check cache first
    cache_key = f"customer_exists:{clean_phone}"
    cached_customer = await cache.get(cache_key)
    
    if cached_customer:
        print(f"🎯 Customer exists cache HIT for {phone}")
        return cached_customer
    
    print(f"⚡ Customer exists cache MISS for {phone}")
    
    customer = await users_collection.find_one({"phone": clean_phone})
    
    if customer:
        result = {
            "exists": True,
            "customer_data": customer,
            "message": "Existing customer found"
        }
    else:
        result = {
            "exists": False,
            "customer_data": None,
            "message": "New customer - registration required"
        }
    
    # Cache for 2 hours
    await cache.set(cache_key, result, ttl=7200)
    
    return result
