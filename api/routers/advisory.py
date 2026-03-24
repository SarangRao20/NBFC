"""Advisory Router — Step 17 + Smart Loan Queries."""

from fastapi import APIRouter, Query
from typing import Optional, List
from api.schemas.advisory import AdvisoryResponse
from api.services import advisory_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/advisory", tags=["Advisory"])


@router.post("/session/{session_id}/advisory", response_model=AdvisoryResponse,
             summary="Step 17: Advisory Agent — Personalized Financial Advice")
async def generate_advisory(session_id: str):
    """Generate personalized financial advice based on the loan decision.
    Approved: congratulations + cross-sell.
    Rejected (credit): 90-day CIBIL improvement plan.
    Rejected (DTI): restructuring suggestions.
    Rejected (fraud): branch visit instructions.
    """
    result = await advisory_service.generate_advisory(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.get("/loans/{phone}",
            summary="Get Customer Loans with Smart Filtering")
async def get_loans(
    phone: str,
    intent: Optional[str] = Query(None, description="Query intent: 'next_emi', 'loan_details', 'payment_status', 'all'"),
    fields: Optional[str] = Query(None, description="Comma-separated field names to return")
):
    """
    Smart loan query endpoint with flexible field filtering.
    
    Query intents:
    - next_emi: Get next EMI due date + amount + remaining
    - loan_details: Full loan details including interest, tenure
    - payment_status: Payment schedule + due dates
    - all: Return all available fields
    
    Example:
    GET /advisory/loans/9421140800?intent=next_emi
    GET /advisory/loans/9421140800?fields=loan_id,emi,next_emi_due_date
    """
    field_list = fields.split(",") if fields else None
    result = await advisory_service.get_loans_smart(phone, intent, field_list)
    return result


@router.get("/loans/{phone}/message",
            summary="Get Natural Language Loan Summary")
async def get_loan_message(
    phone: str,
    intent: Optional[str] = Query("general", description="Message intent: 'next_emi', 'status', 'approval', 'general'")
):
    """
    Get natural language advisory message by analyzing loan data.
    
    The agent reads loan tables and generates human-friendly responses.
    
    Intents:
    - next_emi: When is my next EMI due?
    - status: Show me all my loans
    - approval: Congratulations message (use with context)
    - general: General loan overview
    """
    message = await advisory_service.generate_advisory_message(phone, intent)
    return {
        "success": True,
        "phone": phone,
        "intent": intent,
        "message": message
    }
