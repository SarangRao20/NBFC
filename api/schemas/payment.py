"""Pydantic schemas for Razorpay Payment endpoints."""

from pydantic import BaseModel
from typing import Optional


class CreateOrderResponse(BaseModel):
    """Response from creating a Razorpay order for EMI payment."""
    success: bool = True
    order_id: str
    amount: float          # Amount in INR
    amount_paise: int      # Amount in paise (for Razorpay Checkout)
    currency: str = "INR"
    key_id: str            # Razorpay Key ID for frontend checkout
    customer_name: str = ""
    customer_email: str = ""
    customer_phone: str = ""
    session_id: str = ""
    description: str = ""
    message: str = ""
    mock: bool = False


class VerifyPaymentRequest(BaseModel):
    """Request body for verifying a Razorpay payment after checkout."""
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    """Response from payment verification."""
    success: bool
    message: str
    payment_id: str = ""
    loan_terms: Optional[dict] = None


class PaymentStatusResponse(BaseModel):
    """Response for checking payment status."""
    payment_id: str
    status: str  # "authorized", "captured", "failed", "refunded"
    amount: float
    method: str = ""  # "card", "upi", "netbanking", etc.
    captured_at: str = ""
