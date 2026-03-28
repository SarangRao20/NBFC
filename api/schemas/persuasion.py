"""Pydantic schemas for Persuasion Loop endpoints (Steps 12, 13, 14, 15)."""

from pydantic import BaseModel, Field
from typing import Optional


class LoanOption(BaseModel):
    label: str
    amount: float
    tenure: int
    emi: float

# ── Step 12: POST /session/{id}/persuasion/analyze ────────────────────────────
class PersuasionAnalyzeResponse(BaseModel):
    rejection_reasons: list[str]
    credit_score_ok: bool
    dti_current: float
    dti_threshold: float = 0.50
    message: str


# ── Step 13: POST /session/{id}/persuasion/suggest ────────────────────────────
class PersuasionSuggestResponse(BaseModel):
    options: list[LoanOption]
    max_approvable_amount: float
    negotiation_round: int
    max_rounds: int
    requires_salary: bool = False
    requires_rejection_letter_consent: bool = False
    rejection_reasons: list[str] = []
    message: str


# ── Step 14: POST /session/{id}/persuasion/respond ────────────────────────────
class PersuasionRespondRequest(BaseModel):
    action: str = Field(..., description="'accept_option_a' | 'accept_option_b' | 'accept' | 'decline'")
    custom_amount: Optional[float] = Field(None, description="Custom amount if user specifies one")
    custom_tenure: Optional[int] = Field(None, description="Custom tenure if user specifies one")

class PersuasionRespondResponse(BaseModel):
    action: str  # "accepted" | "declined" | "invalid"
    revised_loan_terms: Optional[dict] = None
    next_step: str  # "underwriting" | "advisory"
    message: str


# ── Step 15: POST /session/{id}/recalculate-terms ─────────────────────────────
class RecalculateTermsRequest(BaseModel):
    principal: float = Field(..., gt=0)
    tenure_months: int = Field(..., gt=0, le=360)
    rate: Optional[float] = None  # Use existing rate if not provided

class RecalculateTermsResponse(BaseModel):
    loan_terms: dict
    emi: float
    total_interest: float
    total_repayment: float
    dti_estimate: float
    within_threshold: bool
    message: str
