"""Shared state schema for the NBFC loan processing pipeline."""

from typing import TypedDict


class LoanState(TypedDict, total=False):
    # ── Loan Info ──
    loan_type: str                 # personal / student / business / home
    loan_amount: float
    tenure: int
    interest_rate: float

    # ── Registration ──
    full_name: str
    phone: str
    email: str
    address: str
    employment_type: str           # salaried / self-employed
    monthly_income: float
    pan: str
    otp_verified: bool
    pin_hash: str
    bank_name: str
    bank_account_number: str
    bank_ifsc: str
    abc_id: str
    abc_verified: bool

    # ── Control ──
    current_agent: str
    errors: list
