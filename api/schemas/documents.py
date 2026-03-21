"""Pydantic schemas for Document endpoints (Steps 5, 6, 7, 8)."""

from pydantic import BaseModel, Field
from typing import Optional


# ── Step 5: POST /session/{id}/request-documents ──────────────────────────────
class RequestDocumentsResponse(BaseModel):
    required_documents: list[str]
    message: str


# ── Step 6: POST /session/{id}/extract-ocr ────────────────────────────────────
# Note: This endpoint accepts file upload (multipart/form-data), no request body schema.
class OCRExtractionResponse(BaseModel):
    extracted_data: dict
    confidence: float
    document_id: Optional[str] = None
    message: str


# ── Step 7: POST /session/{id}/check-tampering ────────────────────────────────
class TamperCheckResponse(BaseModel):
    tampered: bool
    tamper_reason: str
    confidence: float
    risk_assessment: str
    message: str


# ── Step 8: POST /session/{id}/verify-income ──────────────────────────────────
class VerifyIncomeResponse(BaseModel):
    income_verified: bool
    salary_extracted: float
    salary_claimed: float
    income_match: bool
    variance_pct: float = 0.0
    message: str
