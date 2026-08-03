"""Advisory Router — Step 17 + Smart Loan Queries."""

from fastapi import APIRouter, Query, HTTPException
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
            summary="Get Natural Language Loan Summary or Answer Query")
async def get_loan_message(
    phone: str,
    intent: Optional[str] = Query("general", description="Message intent: 'next_emi', 'status', 'approval', 'general'"),
    query: Optional[str] = Query(None, description="Optional user question for contextual response"),
):
    """
    Get natural language advisory message by analyzing loan data.
    
    If `query` is provided, generates a contextual response to the user's question
    using their profile data (CIBIL, salary, loans).
    
    Intents:
    - next_emi: When is my next EMI due?
    - status: Show me all my loans
    - approval: Congratulations message (use with context)
    - general: General loan overview
    """
    if query:
        message = await advisory_service.generate_contextual_response(phone, query)
    else:
        message = await advisory_service.generate_advisory_message(phone, intent)
    return {
        "success": True,
        "phone": phone,
        "intent": intent,
        "message": message
    }


@router.get("/loans/{phone}/health-score",
            summary="Get Financial Health Score")
async def get_health_score(phone: str):
    """Compute financial health score (0-100) using CIBIL, DTI, stability, loan history.
    Returns overall score with component breakdown for dashboard visualization.
    """
    result = await advisory_service.get_health_score(phone)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "User not found"))
    return result


@router.get("/loans/{phone}/emi-calculator",
            summary="Calculate EMI with Amortization Schedule")
async def get_emi_calculator(
    phone: str,
    amount: float = Query(..., description="Loan amount"),
    rate: float = Query(..., description="Annual interest rate in %"),
    tenure: int = Query(..., description="Tenure in months"),
):
    """Calculate EMI, generate amortization schedule, and compare tenure options.
    Returns monthly EMI, total interest, amortization table, and DTI impact.
    """
    result = await advisory_service.get_emi_calculator(phone, amount, rate, tenure)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Calculation failed"))
    return result


@router.get("/loans/{phone}/lender-comparison",
            summary="Get Structured Lender Comparison Data")
async def get_lender_comparison(phone: str):
    """Return structured lender comparison data for dashboard.
    Shows each lender's eligibility status, rates, fees, and rejection reasons.
    """
    result = await advisory_service.get_lender_comparison(phone)
    return result
