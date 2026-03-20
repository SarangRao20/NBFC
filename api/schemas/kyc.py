"""Pydantic schemas for KYC Verification endpoint (Step 9)."""

from pydantic import BaseModel


class KYCVerifyResponse(BaseModel):
    kyc_status: str  # "verified" | "failed"
    issues: list[str]
    message: str
