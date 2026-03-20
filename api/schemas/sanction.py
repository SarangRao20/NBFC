"""Pydantic schemas for Sanction / Closing endpoint (Step 16)."""

from pydantic import BaseModel


class SanctionResponse(BaseModel):
    sanction_pdf_path: str
    letter_type: str  # "Sanction" | "Rejection"
    loan_terms: dict
    message: str
