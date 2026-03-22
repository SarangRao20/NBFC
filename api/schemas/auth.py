"""Pydantic schemas for Authentication endpoints."""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any


class OTPRequest(BaseModel):
    """OTP request model."""
    phone: str
    email: EmailStr


class OTPVerify(BaseModel):
    """OTP verification response model."""
    success: bool
    message: str
    dev_mode: bool = False


class LoginResponse(BaseModel):
    """Login response model."""
    success: bool
    message: str
    session_id: Optional[str] = None
    profile_complete: bool = True
    customer_data: Optional[Dict[str, Any]] = None
    missing_fields: Optional[List[str]] = []
    requires_profile_update: bool = False


class ProfileCheckResponse(BaseModel):
    """Profile completeness check response."""
    is_complete: bool
    missing_fields: List[str] = []
    completeness_percentage: float = 0.0
    session_id: Optional[str] = None
    message: str = ""


class CustomerProfileUpdate(BaseModel):
    """Customer profile update model."""
    phone: str
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    city: Optional[str] = None
    salary: Optional[float] = None
    credit_score: Optional[int] = None
    existing_emi_total: Optional[float] = None


class DevStatusResponse(BaseModel):
    """Development mode status response."""
    otp_disabled: bool
    dev_otp: Optional[str] = None
    debug_mode: bool
    message: str
