"""Pydantic schemas for Sales/Ingestion endpoints (Steps 2, 3)."""

from pydantic import BaseModel, Field
from typing import Optional


# ── Step 2: POST /session/{id}/identify-customer ──────────────────────────────
class IdentifyCustomerRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=13, description="Customer phone (10 digits, optionally +91)")
    email: Optional[str] = Field(None, description="Optional email for lookup")
    password: Optional[str] = Field(None, description="Optional password for email-based login")

class CustomerProfileOut(BaseModel):
    name: str
    phone: str
    city: str
    salary: float
    credit_score: int
    pre_approved_limit: float
    existing_emi_total: float = 0
    current_loans: list[str] = []

class IdentifyCustomerResponse(BaseModel):
    is_existing_customer: bool
    customer_data: Optional[CustomerProfileOut] = None
    message: str


# ── Step 3: POST /session/{id}/capture-loan ───────────────────────────────────
class CaptureLoanRequest(BaseModel):
    loan_type: str = Field(..., description="personal / student / business / home")
    loan_amount: float = Field(..., gt=0, description="Requested loan amount in INR")
    tenure_months: int = Field(..., gt=0, le=360, description="Loan tenure in months")

class CaptureLoanResponse(BaseModel):
    loan_terms: dict
    emi: float
    total_interest: float
    total_repayment: float
    message: str
