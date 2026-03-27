"""Pydantic schemas for Sanction / Closing endpoint (Step 16)."""

from pydantic import BaseModel


class SanctionResponse(BaseModel):
    sanction_pdf_path: str
    letter_type: str  # "Sanction" | "Rejection"
    loan_terms: dict
    message: str


class ESignResponse(BaseModel):
    success: bool
    message: str
    next_step: str  # "advisory" | "disbursement" | "end"
    advisory_message: str = ""  # Message from advisory agent if routed there
    disbursement_step: str = ""  # "ui_paused" when disbursement UI should show
    net_disbursement_amount: float = 0.0  # Net amount after deductions

