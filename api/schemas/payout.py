"""Pydantic schemas for RazorpayX Payout (Disbursement) endpoints."""

from pydantic import BaseModel
from typing import Optional


class DisbursementRequest(BaseModel):
    """Request to initiate loan disbursement via RazorpayX."""
    account_number: str
    ifsc: str
    account_holder_name: str
    amount: Optional[float] = None  # If None, uses net_disbursement_amount from session


class DisbursementResponse(BaseModel):
    """Response from disbursement initiation."""
    success: bool
    message: str
    payout_id: str = ""
    contact_id: str = ""
    fund_account_id: str = ""
    amount: float = 0.0
    status: str = ""  # "processing", "processed", "reversed", "queued"
    utr: str = ""     # Unique Transaction Reference from bank
    mode: str = ""    # "IMPS", "NEFT", "RTGS"


class PayoutStatusResponse(BaseModel):
    """Response for checking payout status."""
    payout_id: str
    status: str
    amount: float
    utr: str = ""
    failure_reason: str = ""
