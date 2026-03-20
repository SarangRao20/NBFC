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
    name: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    salary: float = 0
    credit_score: int = 0
    pre_approved_limit: float = 0
    existing_emi_total: float = 0
    current_loans: list[str] = []

class LoanTermsOut(BaseModel):
    loan_type: str = ""
    principal: float = 0
    rate: float = 0.0
    tenure: int = 0
    emi: float = 0.0

class DocumentsOut(BaseModel):
    verified: bool = False
    document_type: str = ""
    salary_extracted: float = 0.0
    confidence: float = 0.0
    tampered: bool = False
    name_extracted: str = ""

class SessionStateResponse(BaseModel):
    session_id: str
    status: str
    current_phase: str
    customer_data: CustomerDataOut
    loan_terms: LoanTermsOut
    documents: DocumentsOut
    kyc_status: str = ""
    fraud_score: float = -1.0
    decision: str = ""
    dti_ratio: float = 0.0
    risk_level: str = ""
    negotiation_round: int = 0
    sanction_pdf: str = ""
    phase_history: list[dict] = []


# ── Step 18: POST /session/{id}/end ───────────────────────────────────────────
class SessionEndResponse(BaseModel):
    session_id: str
    status: str
    message: str
    phase_history: list[dict]
