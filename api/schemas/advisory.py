"""Pydantic schemas for Advisory endpoint (Step 17)."""

from pydantic import BaseModel


class AdvisoryResponse(BaseModel):
    decision: str
    advisory_message: str
    cross_sell_suggestion: str = ""
    next_steps: list[str] = []
    message: str
