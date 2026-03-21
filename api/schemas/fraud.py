"""Pydantic schemas for Fraud Detection endpoint (Step 10)."""

from pydantic import BaseModel


class FraudSignal(BaseModel):
    signal_name: str
    weight: float
    triggered: bool
    detail: str = ""

class FraudCheckResponse(BaseModel):
    fraud_score: float
    risk_level: str  # "LOW" | "MEDIUM" | "HIGH"
    signals_triggered: int
    signals: list[FraudSignal]
    escalation_required: bool
    message: str
