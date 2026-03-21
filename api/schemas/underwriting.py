"""Pydantic schemas for Underwriting / Decision Engine endpoint (Step 11)."""

from pydantic import BaseModel
from typing import Optional


class UnderwritingResponse(BaseModel):
    decision: str  # "approve" | "soft_reject" | "reject" | "pending_docs"
    risk_level: str  # "low" | "medium" | "high"
    dti_ratio: float
    reasons: list[str]
    alternative_offer: Optional[float] = None
    message: str
