from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class User(BaseModel):
    name: str
    email: str
    age: int


# Lender Offer Schemas
class LenderOffer(BaseModel):
    """Represents a loan offer from a single lender."""
    lender_id: str
    lender_name: str
    lender_type: str  # "bank", "nbfc", "fintech", "cooperative"
    interest_rate: float = Field(..., description="Annual interest rate percentage")
    processing_fee: float = Field(..., description="Processing fee in INR")
    max_loan_amount: float
    tenure_options: List[int]
    risk_profile: str  # "low", "medium", "high"
    approval_probability: float = Field(..., ge=0, le=1, description="Probability of approval (0-1)")
    settlement_days: int
    characteristics: str


class LoanComparison(BaseModel):
    """Complete comparison with EMI and cost calculations for a single lender."""
    lender_id: str
    lender_name: str
    lender_type: str
    interest_rate: float
    emi: float = Field(..., description="Monthly EMI in INR")
    total_repayment: float = Field(..., description="Total amount to be repaid")
    total_interest: float = Field(..., description="Total interest payable")
    processing_fee: float
    total_cost: float = Field(..., description="Processing fee + Total interest")
    approval_probability: float
    approval_percentage: float = Field(..., description="Approval probability as percentage")
    risk_profile: str
    settlement_days: int
    tenure_months: int
    loan_amount: float
    recommendation_score: Optional[float] = Field(default=None, ge=0, le=100)
    recommendation_reason: Optional[str] = None


class AggregatedLoansResponse(BaseModel):
    """Response containing all eligible loan offers with calculations."""
    request_params: dict
    total_offers: int
    offers: List[LoanComparison]
    applied_on: str
    best_offer: Optional[LoanComparison] = None
    alternatives: Optional[List[LoanComparison]] = None


class LoanSelectionRequest(BaseModel):
    """User's selection of a specific loan offer."""
    session_id: str
    selected_lender_id: str
    selected_interest_rate: float
    selected_emi: float
    selected_tenure_months: int


class LoanSelectionResponse(BaseModel):
    """Confirmation of loan selection."""
    success: bool
    message: str
    selected_lender: str
    next_step: str  # "kyc", "underwriting", etc.