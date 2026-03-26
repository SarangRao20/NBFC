"""
Comparison API Router — REST endpoints for loan comparison and selection.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from api.services.comparison_service import ComparisonService

router = APIRouter(
    prefix="/api/comparison",
    tags=["loan-comparison"],
    responses={404: {"description": "Not found"}}
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class GetLoansRequest(BaseModel):
    """Request model for fetching loan comparisons."""
    loan_amount: float = Field(..., description="Loan amount in INR", gt=0)
    tenure_months: int = Field(..., description="Tenure in months", gt=0)
    credit_score: int = Field(default=700, description="CIBIL credit score", ge=600, le=900)
    monthly_salary: float = Field(..., description="Monthly salary in INR", gt=0)
    age: int = Field(default=35, description="Age in years", ge=18, le=80)
    existing_obligations: float = Field(default=0, description="Monthly EMI of other loans", ge=0)


class LoanOptionResponse(BaseModel):
    """Response model for individual loan option."""
    lender_id: str
    lender_name: str
    lender_type: str
    interest_rate: float
    emi: float
    total_cost: float
    approval_probability: float
    approval_percentage: float
    composite_score: float
    rank_badge: str
    recommendation_rank: int


class GetLoansResponse(BaseModel):
    """Response model for loan comparison."""
    status: str = Field(..., description="success or no_eligible_offers")
    eligible_count: int
    ineligible_count: int
    eligible_offers: List[LoanOptionResponse]
    best_offer: Optional[LoanOptionResponse] = None
    alternatives: List[LoanOptionResponse] = []
    recommendation_reason: str
    smart_suggestions: List[str] = []
    applied_weights: Dict[str, float]


class SelectLoanRequest(BaseModel):
    """Request model for loan selection."""
    session_id: Optional[str] = Field(default=None, description="Session ID from comparison")
    selected_lender_id: str = Field(..., description="Lender ID to select")


class SelectLoanResponse(BaseModel):
    """Response model for loan selection."""
    success: bool
    message: str
    selected_lender: str
    selected_interest_rate: float
    selected_emi: float
    next_step: str


class WhatIfRequest(BaseModel):
    """Request model for what-if simulation."""
    session_id: str
    new_loan_amount: Optional[float] = None
    new_tenure_months: Optional[int] = None


class WhatIfResponse(BaseModel):
    """Response model for what-if simulation."""
    original: Dict[str, Any]
    simulated: Dict[str, Any]
    differences: Dict[str, Any]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/get-loans",
    response_model=GetLoansResponse,
    summary="Compare loans from multiple lenders",
    description="Fetch and compare loan offers from 5 different lenders based on user input"
)
async def get_loans(request: GetLoansRequest) -> GetLoansResponse:
    """
    Compare loans from multiple lenders.
    
    **Parameters:**
    - **loan_amount**: Amount to borrow (₹)
    - **tenure_months**: Repayment period (months)
    - **credit_score**: CIBIL/Credit score (600-900)
    - **monthly_salary**: Monthly income (₹)
    - **age**: Applicant age (18-80, default 35)
    - **existing_obligations**: Other monthly EMI (default 0)
    
    **Returns:**
    - List of eligible loan offers ranked by composite score
    - Best recommendation with explanation
    - 2 alternative options
    - Smart suggestions if ineligible
    
    **Example:**
    ```json
    {
        "loan_amount": 500000,
        "tenure_months": 60,
        "credit_score": 750,
        "monthly_salary": 50000
    }
    ```
    """
    try:
        # Call comparison service
        result = ComparisonService.get_loan_comparisons(
            loan_amount=request.loan_amount,
            tenure_months=request.tenure_months,
            credit_score=request.credit_score,
            monthly_salary=request.monthly_salary,
            age=request.age,
            existing_obligations=request.existing_obligations
        )
        
        # Transform result to response format
        return GetLoansResponse(
            status=result["status"],
            eligible_count=result["eligible_count"],
            ineligible_count=result["ineligible_count"],
            eligible_offers=result["eligible_offers"],
            best_offer=result["best_offer"],
            alternatives=result["alternatives"],
            recommendation_reason=result["recommendation_reason"],
            smart_suggestions=result["smart_suggestions"],
            applied_weights=result["applied_weights"]
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/select-loan",
    response_model=SelectLoanResponse,
    summary="Select a loan and proceed to next step",
    description="User selects a loan from comparison results"
)
async def select_loan(request: SelectLoanRequest) -> SelectLoanResponse:
    """
    Process user's loan selection.
    
    **Parameters:**
    - **session_id**: Session ID (optional, for tracking)
    - **selected_lender_id**: ID of selected lender (e.g., "bank_a", "nbfc_x")
    
    **Returns:**
    - Confirmation of selection
    - Selected loan details
    - Next step in workflow
    
    **Example:**
    ```json
    {
        "session_id": "sess_12345",
        "selected_lender_id": "bank_a"
    }
    ```
    """
    try:
        result = ComparisonService.process_loan_selection(
            selected_lender_id=request.selected_lender_id
        )
        
        return SelectLoanResponse(
            success=result["success"],
            message=result["message"],
            selected_lender=result["selected_lender"],
            selected_interest_rate=result["selected_interest_rate"],
            selected_emi=result["selected_emi"],
            next_step=result["next_step"]
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/what-if",
    response_model=WhatIfResponse,
    summary="Run what-if simulation",
    description="Recalculate loans with different parameters"
)
async def what_if_simulation(request: WhatIfRequest) -> WhatIfResponse:
    """
    Run what-if simulation.
    
    Allows users to see how changing loan amount or tenure affects options.
    
    **Parameters:**
    - **session_id**: Session ID from comparison
    - **new_loan_amount**: New amount to compare (optional)
    - **new_tenure_months**: New tenure to compare (optional)
    
    **Returns:**
    - Original comparison results
    - New simulated results
    - Differences (savings/losses)
    """
    try:
        result = ComparisonService.run_what_if_simulation(
            session_id=request.session_id,
            new_loan_amount=request.new_loan_amount,
            new_tenure_months=request.new_tenure_months
        )
        
        return WhatIfResponse(
            original=result["original"],
            simulated=result["simulated"],
            differences=result["differences"]
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/health",
    summary="Health check",
    description="Check if comparison service is operational"
)
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    **Returns:**
    - Status of comparison service
    """
    return {
        "status": "operational",
        "service": "loan-comparison",
        "version": "2.0"
    }


@router.get(
    "/lenders",
    summary="List available lenders",
    description="Get information about all available lenders"
)
async def list_lenders() -> Dict[str, Any]:
    """
    List all available lenders.
    
    **Returns:**
    - List of lenders with key characteristics
    """
    return ComparisonService.get_lenders_info()


@router.post(
    "/eligibility-check",
    summary="Check eligibility only",
    description="Check if user is eligible without full comparison"
)
async def check_eligibility(request: GetLoansRequest) -> Dict[str, Any]:
    """
    Quick eligibility check without full comparison.
    
    **Parameters:**
    Same as /get-loans
    
    **Returns:**
    - Eligible: bool
    - Eligible lenders: list
    - Failed checks: dict
    """
    try:
        result = ComparisonService.check_eligibility_only(
            loan_amount=request.loan_amount,
            tenure_months=request.tenure_months,
            credit_score=request.credit_score,
            monthly_salary=request.monthly_salary,
            age=request.age,
            existing_obligations=request.existing_obligations
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
