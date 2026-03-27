"""Pydantic schemas for Session endpoints (Steps 1, 4, 18)."""

from pydantic import BaseModel
from typing import Optional


# ── Step 1: POST /session/start ───────────────────────────────────────────────
class SessionStartResponse(BaseModel):
    session_id: str
    status: str
    current_phase: str
    message: str


# ── Step 4: GET /session/{id}/state ───────────────────────────────────────────
class CustomerDataOut(BaseModel):
    name: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    city: Optional[str] = ""
    salary: Optional[float] = 0.0
    credit_score: Optional[int] = 0
    pre_approved_limit: Optional[float] = 0.0
    existing_emi_total: Optional[float] = 0.0
    current_loans: Optional[list[str]] = []
    past_loans: Optional[list[dict]] = []
    past_records: Optional[str] = ""

class LoanTermsOut(BaseModel):
    loan_type: Optional[str] = ""
    principal: Optional[float] = 0.0
    rate: Optional[float] = 0.0
    tenure: Optional[int] = 0
    emi: Optional[float] = 0.0
    loan_purpose: Optional[str] = ""
    payments_made: Optional[int] = 0
    remaining_balance: Optional[float] = 0.0
    next_emi_date: Optional[str] = ""

class EligibleOfferOut(BaseModel):
    lender_id: Optional[str] = ""
    lender_name: Optional[str] = ""
    interest_rate: Optional[float] = 0.0
    emi: Optional[float] = 0.0
    tenure: Optional[int] = 0

class DocumentsOut(BaseModel):
    verified: Optional[bool] = False
    document_type: Optional[str] = ""
    salary_extracted: Optional[float] = 0.0
    confidence: Optional[float] = 0.0
    tampered: Optional[bool] = False
    name_extracted: Optional[str] = ""

class SessionStateResponse(BaseModel):
    session_id: str
    status: str
    current_phase: str
    customer_data: Optional[CustomerDataOut] = None
    loan_terms: Optional[LoanTermsOut] = None
    documents: Optional[DocumentsOut] = None
    eligible_offers: Optional[list[EligibleOfferOut]] = []
    kyc_status: Optional[str] = ""
    fraud_score: Optional[float] = -1.0
    decision: Optional[str] = ""
    dti_ratio: Optional[float] = 0.0
    risk_level: Optional[str] = ""
    negotiation_round: Optional[int] = 0
    sanction_pdf: Optional[str] = ""
    action_log: Optional[list[str]] = []
    options: Optional[list[str]] = []
    phase_history: Optional[list[dict]] = []



# ── Step 18: POST /session/{id}/end ───────────────────────────────────────────
class SessionEndResponse(BaseModel):
    session_id: str
    status: str
    message: str
    phase_history: list[dict]
