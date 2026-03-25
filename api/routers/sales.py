"""Sales Router — Steps 2, 3 (Ingestion & Profiling)."""

from fastapi import APIRouter
from api.schemas.sales import (
    IdentifyCustomerRequest, IdentifyCustomerResponse,
    CaptureLoanRequest, CaptureLoanResponse,
)
from api.services import sales_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Sales / Ingestion"])


@router.post("/{session_id}/identify-customer", response_model=IdentifyCustomerResponse,
             summary="Step 2: Identify Existing vs New User")
async def identify_customer(session_id: str, req: IdentifyCustomerRequest):
    """Look up the customer in the CRM database by phone number.
    Returns customer profile if existing, or creates a new profile.
    """
    result = await sales_service.identify_customer(
        session_id, req.phone, req.email, req.password
    )
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.post("/{session_id}/capture-loan", response_model=CaptureLoanResponse,
             summary="Step 3: Capture Loan Requirement + EMI Calculation")
async def capture_loan(session_id: str, req: CaptureLoanRequest):
    """Capture the loan type, amount, and tenure. Automatically calculates
    EMI, total interest, and total repayment.
    State Update: Profile & Intent.
    """
    result = await sales_service.capture_loan_requirement(
        session_id, req.loan_type, req.loan_amount, req.tenure_months
    )
    if result is None:
        raise SessionNotFoundError(session_id)
    return result
@router.post("/{session_id}/chat", summary="Conversational interface with Sales/Registration Agent")
async def chat(session_id: str, req: dict):
    """General chat endpoint that routes to Sales or Registration agents.
    Expects {"message": "user message", "history": []}
    """
    # History is now persisted automatically via update_session in sales_service.
    result = await sales_service.chat_with_agent(
        session_id, req.get("message", ""), req.get("history", [])
    )
    if result is None:
        raise SessionNotFoundError(session_id)
    return result

@router.get("/{session_id}/history", summary="Retrieve Chat History for a Session")
async def get_chat_history(session_id: str):
    """Returns the persisted chat history for a given session from the master state."""
    import logging
    from db.database import sessions_collection
    try:
        state_doc = await sessions_collection.find_one({"_id": session_id})
        if state_doc:
            return {"history": state_doc.get("messages", [])}
    except Exception as e:
        logging.error(f"Error fetching chat history: {e}")
    return {"history": []}
