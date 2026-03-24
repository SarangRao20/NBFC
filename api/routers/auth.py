"""Authentication Router - Enhanced with OTP bypass and profile completeness check."""

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Form
from pydantic import BaseModel
from api.schemas.auth import OTPVerify, LoginResponse, ProfileCheckResponse
from api.services.auth_service import auth_service
from api.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


class DevOTPRequest(BaseModel):
    """Development OTP request model"""
    phone: str
    use_dev_otp: bool = False  # Toggle for development


@router.post("/send-otp", response_model=dict,
             summary="Send OTP with Development Bypass Option")
async def send_otp(
    phone: str = Form(...),
    email: Optional[str] = Form(None)
):
    """Send OTP to customer's email with development bypass option."""
    try:
        # Check if OTP is disabled for development
        if settings.DISABLE_OTP:
            dev_otp = settings.DEV_OTP
            success = await auth_service.generate_dev_otp(phone, dev_otp)
            
            return {
                "success": success,
                "message": f"Development mode: OTP set to {dev_otp}",
                "otp_sent": False,
                "dev_mode": True,
                "dev_otp": dev_otp
            }
        
        # Normal OTP flow
        result = await auth_service.send_otp(phone, email)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {str(e)}"
        )


@router.post("/verify-otp", response_model=OTPVerify,
             summary="Verify OTP with Development Bypass")
async def verify_otp(
    phone: str = Form(...),
    otp: str = Form(...),
    use_dev_otp: bool = Form(False)
):
    """Verify OTP with development bypass option."""
    try:
        # Check if using development OTP
        if settings.DISABLE_OTP and use_dev_otp:
            if otp == settings.DEV_OTP:
                return {
                    "success": True,
                    "message": "Development OTP verified successfully",
                    "dev_mode": True
                }
            else:
                return {
                    "success": False,
                    "message": f"Invalid OTP. Development OTP is {settings.DEV_OTP}",
                    "dev_mode": True
                }
        
        # Normal OTP verification
        result = await auth_service.verify_otp(phone, otp)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify OTP: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse,
             summary="Login with phone and password")
async def login(
    phone: str = Form(...),
    password: str = Form(...)
):
    """Login with phone and password using mock customers database."""
    try:
        result = await auth_service.login_with_password(phone, password)
        
        if result["success"]:
            return LoginResponse(
                success=True,
                message=result["message"],
                session_id=result["session_id"],
                profile_complete=True,
                customer_data=result["customer_data"],
                requires_profile_update=False
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result["message"]
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/register", response_model=dict,
             summary="Register new customer")
async def register(
    phone: str = Form(...),
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    city: Optional[str] = Form(None),
    salary: Optional[float] = Form(None),
    dob: Optional[str] = Form(None),
    profession: Optional[str] = Form(None),
    address: Optional[str] = Form(None)
):
    """Register new customer with OTP verification."""
    try:
        user_data = {
            "phone": phone,
            "email": email,
            "name": name,
            "password": password,
            "city": city,
            "salary": salary,
            "dob": dob,
            "profession": profession,
            "address": address
        }
        
        result = await auth_service.register_customer(user_data)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Registration successful",
                "customer_data": result["customer_data"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/credit-score/{phone}", response_model=dict,
            summary="Fetch Mock CIBIL/Credit Score")
async def get_credit_score(phone: str, persist: bool = False):
    """Fetch credit score for a phone number and optionally persist it to profile."""
    try:
        result = await auth_service.fetch_credit_score(phone=phone, persist=persist)
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch credit score")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Credit score fetch failed: {str(e)}"
        )


@router.post("/fetch-credit-score", response_model=dict,
             summary="Fetch Mock CIBIL/Credit Score with Identity Inputs")
async def fetch_credit_score(
    phone: str = Form(...),
    pan: Optional[str] = Form(None),
    full_name: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    persist: bool = Form(False),
):
    """Fetch score using optional PAN/name/DOB and optionally persist to user profile."""
    try:
        result = await auth_service.fetch_credit_score(
            phone=phone,
            pan=pan,
            full_name=full_name,
            dob=dob,
            persist=persist,
        )
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch credit score")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Credit score fetch failed: {str(e)}"
        )


@router.post("/login-otp", response_model=LoginResponse,
             summary="Enhanced Login with OTP and Profile Check")
async def login_otp(
    phone: str = Form(...),
    otp: str = Form(...),
    use_dev_otp: bool = Form(False)
):
    """Enhanced login that checks profile completeness."""
    try:
        # Verify OTP first
        if settings.DISABLE_OTP and use_dev_otp:
            if otp != settings.DEV_OTP:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid development OTP. Use {settings.DEV_OTP}"
                )
            otp_verified = True
        else:
            otp_result = await auth_service.verify_otp(phone, otp)
            if not otp_result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid OTP"
                )
            otp_verified = True
        
        # Check profile completeness
        profile_check = await auth_service.check_profile_completeness(phone)
        
        if not profile_check["is_complete"]:
            return LoginResponse(
                success=True,
                message="Login successful but profile incomplete",
                session_id=profile_check.get("session_id"),
                profile_complete=False,
                missing_fields=profile_check["missing_fields"],
                requires_profile_update=True
            )
        
        # Complete profile - create session
        session_data = await auth_service.create_login_session(phone)
        
        return LoginResponse(
            success=True,
            message="Login successful",
            session_id=session_data["session_id"],
            profile_complete=True,
            customer_data=session_data.get("customer_data"),
            requires_profile_update=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/check-profile/{phone}", response_model=ProfileCheckResponse,
            summary="Check Profile Completeness")
async def check_profile(phone: str):
    """Check if customer profile is complete."""
    try:
        result = await auth_service.check_profile_completeness(phone)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile check failed: {str(e)}"
        )


@router.post("/update-profile", summary="Update Missing Profile Fields")
async def update_profile(
    phone: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    city: Optional[str] = None,
    salary: Optional[float] = None,
    credit_score: Optional[int] = None,
    existing_emi_total: Optional[float] = None
):
    """Update missing profile fields."""
    try:
        updates = {}
        if name is not None:
            updates["name"] = name
        if email is not None:
            updates["email"] = email
        if city is not None:
            updates["city"] = city
        if salary is not None:
            updates["salary"] = salary
        if credit_score is not None:
            updates["credit_score"] = credit_score
        if existing_emi_total is not None:
            updates["existing_emi_total"] = existing_emi_total
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        result = await auth_service.update_customer_profile(phone, updates)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )


@router.get("/dev-status", summary="Get Development Mode Status")
async def get_dev_status():
    """Get current development mode settings."""
    return {
        "otp_disabled": settings.DISABLE_OTP,
        "dev_otp": settings.DEV_OTP if settings.DISABLE_OTP else None,
        "debug_mode": settings.DEBUG,
        "message": "Development features are enabled" if settings.DISABLE_OTP else "Production mode"
    }


@router.post("/toggle-otp", summary="Toggle OTP Mode (Development Only)")
async def toggle_otp(disable: bool = True, dev_otp: str = "123456"):
    """Toggle OTP mode for development (WARNING: Use only in development)."""
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in debug mode"
        )
    
    try:
        # This would typically update environment variables
        # For now, just return the current state
        return {
            "otp_disabled": disable,
            "dev_otp": dev_otp if disable else None,
            "message": f"OTP {'disabled' if disable else 'enabled'} for development"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle OTP: {str(e)}"
        )


@router.get("/verify", summary="Verify Session")
async def verify_session(session_id: str):
    """Verify if a session is still valid and return customer data."""
    result = await auth_service.verify_session(session_id)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    return result
