"""
Comparison API Schemas — Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


# ============================================================================
# REQUEST MODELS
# ============================================================================

class GetLoansRequest(BaseModel):
    """Request to compare loans from multiple lenders."""
    
    loan_amount: float = Field(..., description="Loan amount in INR", gt=0)
    tenure_months: int = Field(..., description="Tenure in months", gt=0, le=360)
    credit_score: int = Field(default=700, description="CIBIL credit score", ge=600, le=900)
    monthly_salary: float = Field(..., description="Monthly salary in INR", gt=0)
    age: int = Field(default=35, description="Age in years", ge=18, le=80)
    existing_obligations: float = Field(default=0, description="Monthly EMI of other loans", ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "loan_amount": 500000,
                "tenure_months": 60,
                "credit_score": 750,
                "monthly_salary": 50000,
                "age": 35,
                "existing_obligations": 5000
            }
        }


class SelectLoanRequest(BaseModel):
    """Request to select a loan from comparison results."""
    
    session_id: Optional[str] = Field(default=None, description="Session ID from comparison")
    selected_lender_id: str = Field(..., description="Lender ID to select")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "selected_lender_id": "bank_a"
            }
        }


class WhatIfRequest(BaseModel):
    """Request for what-if simulation."""
    
    session_id: str = Field(..., description="Session ID from comparison")
    new_loan_amount: Optional[float] = Field(default=None, description="New loan amount to simulate")
    new_tenure_months: Optional[int] = Field(default=None, description="New tenure to simulate")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "new_loan_amount": 600000,
                "new_tenure_months": 72
            }
        }


class EligibilityCheckRequest(BaseModel):
    """Request for quick eligibility check."""
    
    loan_amount: float = Field(..., description="Loan amount in INR", gt=0)
    tenure_months: int = Field(..., description="Tenure in months", gt=0)
    credit_score: int = Field(default=700, description="Credit score", ge=600, le=900)
    monthly_salary: float = Field(..., description="Monthly salary in INR", gt=0)
    age: int = Field(default=35, description="Age in years", ge=18, le=80)
    existing_obligations: float = Field(default=0, description="Monthly EMI of other loans", ge=0)


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class LoanOptionResponse(BaseModel):
    """Individual loan offer in comparison results."""
    
    lender_id: str
    lender_name: str
    lender_type: str
    interest_rate: float = Field(..., description="Interest rate %")
    emi: float = Field(..., description="Monthly EMI amount")
    total_cost: float = Field(..., description="Total cost of loan (principal + interest)")
    approval_probability: float = Field(..., description="Approval probability (0-1)")
    approval_percentage: float = Field(..., description="Approval percentage (0-100)")
    composite_score: float = Field(..., description="Weighted comparison score (0-100)")
    rank_badge: str = Field(..., description="Rank badge emoji")
    recommendation_rank: int = Field(..., description="Recommendation rank (1=best)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "lender_id": "bank_a",
                "lender_name": "Bank A",
                "lender_type": "BANK",
                "interest_rate": 9.5,
                "emi": 9735.45,
                "total_cost": 584107.00,
                "approval_probability": 0.98,
                "approval_percentage": 98.0,
                "composite_score": 94.8,
                "rank_badge": "🥇 BEST",
                "recommendation_rank": 1
            }
        }


class GetLoansResponse(BaseModel):
    """Response with loan comparison results."""
    
    status: str = Field(..., description="success or no_eligible_offers")
    eligible_count: int = Field(..., description="Number of eligible offers")
    ineligible_count: int = Field(..., description="Number of ineligible offers")
    eligible_offers: List[LoanOptionResponse] = Field(..., description="All eligible loans")
    best_offer: Optional[LoanOptionResponse] = Field(None, description="Best recommendation")
    alternatives: List[LoanOptionResponse] = Field(default_factory=list, description="2 alternatives")
    recommendation_reason: str = Field(..., description="Why this offer is best")
    smart_suggestions: List[str] = Field(default_factory=list, description="Suggestions if ineligible")
    applied_weights: Dict[str, float] = Field(..., description="Weights used in ranking")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "eligible_count": 4,
                "ineligible_count": 1,
                "eligible_offers": [],
                "best_offer": {
                    "lender_id": "bank_a",
                    "lender_name": "Bank A",
                    "lender_type": "BANK",
                    "interest_rate": 9.5,
                    "emi": 9735.45,
                    "total_cost": 584107.00,
                    "approval_probability": 0.98,
                    "approval_percentage": 98.0,
                    "composite_score": 94.8,
                    "rank_badge": "🥇 BEST",
                    "recommendation_rank": 1
                },
                "alternatives": [],
                "recommendation_reason": "Best balance of low interest rate and high approval probability",
                "smart_suggestions": [],
                "applied_weights": {"emi_factor": 0.40, "approval_factor": 0.35, "cost_factor": 0.25}
            }
        }


class SelectLoanResponse(BaseModel):
    """Response after loan selection."""
    
    success: bool
    message: str
    selected_lender: str
    selected_interest_rate: float
    selected_emi: float
    next_step: str = Field(..., description="Next step in workflow")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Loan from Bank A selected successfully",
                "selected_lender": "Bank A",
                "selected_interest_rate": 9.5,
                "selected_emi": 9735.45,
                "next_step": "underwriting"
            }
        }


class WhatIfResponse(BaseModel):
    """Response for what-if simulation."""
    
    original: Dict[str, Any] = Field(..., description="Original comparison results")
    simulated: Dict[str, Any] = Field(..., description="Simulated results with new parameters")
    differences: Dict[str, Any] = Field(..., description="Differences between original and simulated")
    
    class Config:
        json_schema_extra = {
            "example": {
                "original": {
                    "loan_amount": 500000,
                    "tenure_months": 60,
                    "emi": 9735.45,
                    "best_rate": 9.5,
                    "total_cost": 584107.00
                },
                "simulated": {
                    "loan_amount": 600000,
                    "tenure_months": 72,
                    "emi": 9865.30,
                    "best_rate": 9.5,
                    "total_cost": 711101.60
                },
                "differences": {
                    "emi_change": 129.85,
                    "total_cost_change": 126994.60,
                    "interest_savings": 0
                }
            }
        }


class EligibilityCheckResponse(BaseModel):
    """Response for eligibility check."""
    
    overall_eligible: bool
    eligible_count: int
    ineligible_count: int
    eligible_lenders: List[str] = Field(..., description="List of eligible lender IDs")
    recommendations: List[str] = Field(default_factory=list, description="Improvement suggestions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "overall_eligible": True,
                "eligible_count": 4,
                "ineligible_count": 1,
                "eligible_lenders": ["bank_a", "bank_b", "fintech_y", "credit_union_z"],
                "recommendations": []
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str
    service: str
    version: str


class LenderInfoResponse(BaseModel):
    """Information about a single lender."""
    
    name: str
    type: str
    jurisdiction: str
    base_rate: float
    min_loan_amount: float
    max_loan_amount: float
    approval_probability: float


class LendersListResponse(BaseModel):
    """Response with list of available lenders."""
    
    count: int
    lenders: Dict[str, LenderInfoResponse]


# ============================================================================
# SESSION MODELS
# ============================================================================

class SessionData(BaseModel):
    """Session data model."""
    
    session_id: str
    created_at: datetime
    loan_amount: float
    tenure_months: int
    credit_score: int
    monthly_salary: float
    age: int
    existing_obligations: float
    comparison_result: Optional[GetLoansResponse] = None
    selected_lender: Optional[str] = None


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    
    loan_amount: float
    tenure_months: int
    credit_score: int
    monthly_salary: float
    age: int = 35
    existing_obligations: float = 0


class CreateSessionResponse(BaseModel):
    """Response after session creation."""
    
    session_id: str
    created_at: datetime
    message: str


# ============================================================================
# ERROR MODELS
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.now)


class ValidationErrorResponse(BaseModel):
    """Validation error response."""
    
    error: str = "Validation Error"
    details: List[Dict[str, Any]] = Field(..., description="Validation error details")
    status_code: int = 422
