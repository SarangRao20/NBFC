"""Core State Manager — MongoDB session store for the NBFC loan workflow.

Each session maintains a complete state dict tracking progress through all workflow phases,
persisted in MongoDB Atlas.
"""

import uuid
from datetime import datetime
from typing import Optional
from db.database import sessions_collection


def _default_state() -> dict:
    """Returns a fresh session state with all fields initialized."""
    return {
        # Session metadata
        "session_id": "",
        "created_at": "",
        "current_phase": "init",
        "phase_history": [],

        # Customer profile (Phase 1: Ingestion)
        "customer_id": "",
        "customer_data": {
            "name": "",
            "phone": "",
            "email": "",
            "city": "",
            "salary": 0,
            "credit_score": 0,
            "pre_approved_limit": 0,
            "existing_emi_total": 0,
            "current_loans": [],
            "risk_flags": [],
            "past_records": "",
            "drop_off_history": "",
        },
        "is_existing_customer": False,

        # Loan terms (Phase 1 → Phase 2)
        "loan_terms": {
            "loan_type": "",
            "principal": 0,
            "rate": 0.0,
            "tenure": 0,
            "emi": 0.0,
        },

        # Document verification (Phase 3)
        "documents": {
            "salary_slip_path": "",
            "salary_extracted": 0.0,
            "gross_salary_extracted": 0.0,
            "employer_name": "",
            "document_type": "",
            "document_number": "",
            "confidence": 0.0,
            "verified": False,
            "tampered": False,
            "tamper_reason": "",
            "name_extracted": "",
        },

        # KYC (Phase 4)
        "kyc_status": "",
        "kyc_issues": [],

        # Fraud (Phase 5)
        "fraud_score": -1.0,
        "fraud_signals": 0,
        "fraud_details": [],

        # Underwriting / Decision Engine (Phase 6)
        "decision": "",
        "dti_ratio": 0.0,
        "risk_level": "",
        "alternative_offer": 0.0,
        "reasons": [],
        "is_authenticated": False,
        "otp_sent": False,
        "intent": "none",
        "next_agent": "registration_agent",

        # Persuasion Loop (Phase 7)
        "negotiation_round": 0,
        "persuasion_options": [],
        "persuasion_status": "",

        # Sanction (Phase 8)
        "sanction_pdf": "",

        # Advisory (Phase 9)
        "advisory_message": "",

        "action_log": [],
        "options": [],

        # Session status
        "status": "active",
    }


async def create_session() -> dict:
    """Create a new session, persist to MongoDB, and return its state."""
    session_id = str(uuid.uuid4())
    state = _default_state()
    state["_id"] = session_id  # MongoDB primary key
    state["session_id"] = session_id
    state["created_at"] = datetime.utcnow().isoformat()
    state["current_phase"] = "session_started"
    state["phase_history"].append({
        "phase": "session_started",
        "timestamp": state["created_at"],
    })
    
    await sessions_collection.insert_one(state)
    return state


async def get_session(session_id: str) -> Optional[dict]:
    """Retrieve a session by ID from MongoDB. Returns None if not found."""
    return await sessions_collection.find_one({"_id": session_id})


def _sanitize_state(state: dict) -> dict:
    """Recursively converts LangChain message objects to BSON-serializable dicts."""
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    
    new_state = {}
    for k, v in state.items():
        if k == "messages" and isinstance(v, list):
            new_msgs = []
            for m in v:
                if isinstance(m, (HumanMessage, AIMessage, BaseMessage)):
                    role = "user" if isinstance(m, HumanMessage) else "assistant"
                    new_msgs.append({"role": role, "content": m.content})
                elif isinstance(m, dict):
                    new_msgs.append(m)
                else:
                    new_msgs.append({"role": "system", "content": str(m)})
            new_state[k] = new_msgs
        elif isinstance(v, dict):
            new_state[k] = _sanitize_state(v)
        elif isinstance(v, list):
            new_list = []
            for item in v:
                if isinstance(item, dict):
                    new_list.append(_sanitize_state(item))
                else:
                    new_list.append(item)
            new_state[k] = new_list
        else:
            new_state[k] = v
    return new_state


async def update_session(session_id: str, updates: dict) -> dict:
    """Merge updates into session state and persist to MongoDB. Returns updated state."""
    state = await get_session(session_id)
    if not state:
        raise KeyError(f"Session {session_id} not found")

    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(state.get(key), dict):
            state[key].update(value)
        else:
            state[key] = value

    # Sanitize before persisting to MongoDB Atlas
    sanitized = _sanitize_state(state)
    await sessions_collection.replace_one({"_id": session_id}, sanitized)
    return sanitized


async def advance_phase(session_id: str, phase: str) -> dict:
    """Move session to the next workflow phase and persist to MongoDB."""
    state = await get_session(session_id)
    if not state:
        raise KeyError(f"Session {session_id} not found")

    state["current_phase"] = phase
    state["phase_history"].append({
        "phase": phase,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    sanitized = _sanitize_state(state)
    await sessions_collection.replace_one({"_id": session_id}, sanitized)
    return sanitized


async def end_session(session_id: str) -> dict:
    """Mark session as ended in MongoDB."""
    state = await get_session(session_id)
    if not state:
        raise KeyError(f"Session {session_id} not found")

    state["status"] = "ended"
    state["current_phase"] = "session_ended"
    state["phase_history"].append({
        "phase": "session_ended",
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    sanitized = _sanitize_state(state)
    await sessions_collection.replace_one({"_id": session_id}, sanitized)
    return sanitized


async def delete_session(session_id: str) -> bool:
    """Remove session from MongoDB."""
    result = await sessions_collection.delete_one({"_id": session_id})
    return result.deleted_count > 0
