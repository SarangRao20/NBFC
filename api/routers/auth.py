"""Authentication Router — Password & Google OAuth only. OTP removed."""

import jwt
import secrets
import time
import httpx
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, status, Form, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from api.schemas.auth import LoginResponse, ProfileCheckResponse
from api.services.auth_service import auth_service
from api.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])




@router.post("/send-otp", response_model=dict, summary="[REMOVED] OTP Auth")
async def send_otp():
    """OTP authentication has been removed. Use /auth/login (password) or /auth/google/login."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="OTP authentication removed. Use password login or Google OAuth.")


@router.post("/verify-otp", response_model=dict, summary="[REMOVED] OTP Verify")
async def verify_otp():
    """OTP verification has been removed."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="OTP authentication removed. Use password login or Google OAuth.")


@router.post("/login", response_model=LoginResponse,
             summary="Login with email or phone and password")
async def login(
    phone: str = Form(..., description="Email or Phone number"),
    password: str = Form(...)
):
    """Login with email/phone and password using MongoDB database."""
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
                "customer_data": result["customer_data"],
                "session_id": result.get("session_id")
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


@router.post("/login-otp", response_model=dict, summary="[REMOVED] OTP Login")
async def login_otp():
    """OTP login has been removed. Use /auth/login (password) or /auth/google/login."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="OTP login removed. Use password login or Google OAuth.")


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


@router.post("/toggle-otp", summary="[REMOVED] Toggle OTP Mode")
async def toggle_otp():
    """OTP mode toggle removed. OTP authentication no longer exists."""
    raise HTTPException(status_code=status.HTTP_410_GONE, detail="OTP removed from this system.")


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


# ─── Google OAuth Integration ────────────────────────────────────────────────
def generate_app_jwt(payload_data: dict) -> str:
    """Generate JWT token for authenticated application users."""
    payload = {
        **payload_data,
        "exp": int(time.time()) + (7 * 24 * 3600),  # 7 days expiration
        "iat": int(time.time()),
        "iss": "nbfc-advocate"
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


OAUTH_STATES: Dict[str, float] = {}


@router.get("/google/login", summary="Initiate Google OAuth Login")
async def google_login(request: Request):
    """Initiates Google OAuth 2.0 flow and redirects user to Google Consent screen."""
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        # Development fallback redirect if Client ID is not configured yet
        redirect_url = f"{settings.FRONTEND_URL}/?error=google_client_id_missing"
        return RedirectResponse(url=redirect_url)
    
    state = secrets.token_urlsafe(32)
    OAUTH_STATES[state] = time.time()
    
    # Cleanup expired states (> 10 mins old)
    now = time.time()
    for k in list(OAUTH_STATES.keys()):
        if now - OAUTH_STATES[k] > 600:
            OAUTH_STATES.pop(k, None)
            
    redirect_uri = f"{settings.BACKEND_URL.rstrip('/')}/auth/google/callback"
    
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        "&prompt=select_account"
    )
    
    return RedirectResponse(url=google_auth_url)


@router.get("/google/callback", summary="Google OAuth Callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """Callback endpoint for Google OAuth authorization code exchange."""
    if error:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?error={error}")
        
    if not state or state not in OAUTH_STATES:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=invalid_csrf_state")
        
    OAUTH_STATES.pop(state, None)
    
    if not code:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=missing_code")
        
    redirect_uri = f"{settings.BACKEND_URL.rstrip('/')}/auth/google/callback"
    
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            
            if token_response.status_code != 200:
                print("⚠️ [GOOGLE OAUTH ERROR]", token_response.text)
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=token_exchange_failed")
                
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=failed_userinfo")
                
            from urllib.parse import quote
            from db.database import users_collection
            from datetime import datetime

            existing_user = await users_collection.find_one({"$or": [{"email": email}, {"_id": email}]})
            
            if existing_user:
                user_phone = existing_user.get("phone", "")
                updates = {"picture": picture or existing_user.get("picture", "")}
                if name and not existing_user.get("name"):
                    updates["name"] = name
                await users_collection.update_one({"_id": existing_user["_id"]}, {"$set": updates})
                lookup_key = existing_user.get("phone") or email
            else:
                user_phone = ""
                new_user_doc = {
                    "_id": email,
                    "email": email,
                    "name": name,
                    "phone": "",
                    "picture": picture,
                    "salary": 75000,
                    "credit_score": 750,
                    "pre_approved_limit": 500000,
                    "created_at": datetime.utcnow().isoformat()
                }
                await users_collection.update_one({"_id": email}, {"$set": new_user_doc}, upsert=True)
                lookup_key = email

            session_data = await auth_service.create_login_session(lookup_key)
            session_id = session_data.get("session_id")
            
            app_token = generate_app_jwt({
                "sub": email,
                "name": name,
                "picture": picture,
                "session_id": session_id
            })
            
            redirect_target = f"{settings.FRONTEND_URL}/?session_id={session_id}&token={app_token}&name={quote(name)}&email={quote(email)}&picture={quote(picture)}&phone={quote(user_phone)}"
            return RedirectResponse(url=redirect_target)
            
    except Exception as e:
        print("❌ [GOOGLE OAUTH EXCEPTION]", e)
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/?error=oauth_internal_error")

