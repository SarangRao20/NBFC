"""Shared state schema for the NBFC loan processing pipeline."""

from typing import TypedDict, List, Dict, Optional


class LoanState(TypedDict, total=False):
    # ── Loan Info (Sales Agent fills these) ──
    loan_type: str                 # personal / student / business / home
    loan_amount: float
    tenure: int                    # months
    interest_rate: float           # annual %

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
    aadhaar: str
    kyc_verified: bool

    # ── Control ──
    current_agent: str
    errors: list

    # ── User & Conversational ──
    user_id: str
    is_existing: bool
    customer_name: str
    requested_amount: float
    underwriting_status: str       # Pending, Approved, Soft-Rejected
    rejection_reason: Optional[str]
    negotiation_count: int
    chat_history: List[Dict[str, str]]