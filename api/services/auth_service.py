"""Authentication Service - Enhanced with Redis caching, OTP management, and profile completeness."""

import json
import os
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from api.core.redis_cache import get_cache
from api.core.email_service import get_email_service
from api.core.state_manager import get_session, update_session
from api.config import get_settings
from mock_apis.otp_service import send_otp as mock_send_otp, verify_otp as mock_verify_otp

settings = get_settings()

CUSTOMERS_FILE = os.path.join("mock_apis", "customers.json")

def load_mock_customers() -> List[Dict]:
    if os.path.exists(CUSTOMERS_FILE):
        with open(CUSTOMERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_mock_customers(customers: List[Dict]):
    with open(CUSTOMERS_FILE, "w") as f:
        json.dump(customers, f, indent=4)


class AuthService:
    """Enhanced authentication service with caching and profile management"""
    
    def __init__(self):
        self.cache = None
        self.email_service = None
    
    async def _get_services(self):
        """Initialize services if not already done"""
        if not self.cache:
            self.cache = await get_cache()
        if not self.email_service:
            self.email_service = await get_email_service()
    
    async def generate_otp(self, phone: str) -> str:
        """Generate 6-digit OTP"""
        await self._get_services()
        
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Cache OTP with 5-minute expiry
        await self.cache.set_otp(phone, otp)
        
        print(f"🔐 OTP generated for {phone}: {otp}")
        return otp
    
    async def generate_dev_otp(self, phone: str, dev_otp: str) -> bool:
        """Generate development OTP"""
        await self._get_services()
        
        # Cache development OTP with longer expiry for testing
        await self.cache.set_otp(phone, dev_otp)
        
        print(f"🛠️ Development OTP set for {phone}: {dev_otp}")
        return True
    
    async def send_otp(self, phone: str, email: str = None) -> Dict[str, Any]:
        """Send OTP using mock_apis/otp_service.py"""
        await self._get_services()
        try:
            # Generate and cache OTP centrally so both SMS and email use same code
            otp = await self.generate_otp(phone)

            # Send SMS (mock or real via Twilio)
            sms_result = mock_send_otp(phone, otp)

            # Send email OTP if email provided and email service available
            email_sent = False
            if email:
                try:
                    # try to get customer's name for personalization
                    customer = await self.cache.get_customer(phone) or {}
                    customer_name = customer.get("name", "Customer")
                    email_sent = await self.email_service.send_otp_email(email, customer_name, otp)
                except Exception as ie:
                    print(f"❌ Email send failed: {ie}")

            return {
                "success": sms_result.get("sent", False) or email_sent,
                "message": "OTP sent via SMS and/or Email",
                "phone": phone,
                "email": email,
                "otp_sent": sms_result.get("sent", False),
                "email_sent": email_sent,
                "dev_mode": "otp" in sms_result,
                "dev_otp": sms_result.get("otp")
            }
        except Exception as e:
            print(f"❌ OTP send failed: {e}")
            return {
                "success": False,
                "message": f"Failed to send OTP: {str(e)}",
                "phone": phone,
                "otp_sent": False,
                "email_sent": False
            }
    
    async def verify_otp(self, phone: str, otp: str) -> Dict[str, Any]:
        """Verify OTP using mock_apis/otp_service.py"""
        await self._get_services()
        
        try:
            result = mock_verify_otp(phone, otp)
            return {
                "success": result.get("verified", False),
                "message": result.get("message", "Verification finished"),
                "phone": phone
            }
        except Exception as e:
            print(f"❌ OTP verification failed: {e}")
            return {
                "success": False,
                "message": f"OTP verification failed: {str(e)}",
                "phone": phone
            }
    
    async def check_profile_completeness(self, phone: str) -> Dict[str, Any]:
        """Check if customer profile is complete"""
        await self._get_services()
        
        try:
            # Get customer data from cache first, then DB
            customer_data = await self.cache.get_customer(phone)
            
            if not customer_data:
                # Try to get from database
                from db.database import users_collection
                customer_data = users_collection.find_one({"phone": phone})
                
                if customer_data:
                    # Cache for future use
                    await self.cache.set_customer(phone, customer_data)
            
            if not customer_data:
                return {
                    "is_complete": False,
                    "missing_fields": settings.REQUIRED_PROFILE_FIELDS,
                    "completeness_percentage": 0.0,
                    "message": "Customer not found. Please register first."
                }
            
            # Check required fields
            missing_fields = []
            filled_fields = 0
            
            for field in settings.REQUIRED_PROFILE_FIELDS:
                value = customer_data.get(field)
                if value is None or value == "" or (isinstance(value, (int, float)) and value <= 0):
                    missing_fields.append(field)
                else:
                    filled_fields += 1
            
            total_fields = len(settings.REQUIRED_PROFILE_FIELDS)
            completeness = (filled_fields / total_fields) * 100 if total_fields > 0 else 0
            
            is_complete = len(missing_fields) == 0
            
            # Create temporary session for incomplete profiles
            session_id = None
            if not is_complete:
                from api.core.state_manager import create_session
                session = await create_session()
                session_id = session["session_id"]
                
                # Update session with partial customer data
                await update_session(session_id, {
                    "customer_data": customer_data,
                    "current_phase": "profile_incomplete"
                })
            
            return {
                "is_complete": is_complete,
                "missing_fields": missing_fields,
                "completeness_percentage": completeness,
                "session_id": session_id,
                "message": (
                    f"Profile is {'complete' if is_complete else 'incomplete'} "
                    f"({completeness:.1f}% complete)"
                ),
                "customer_data": customer_data
            }
        
        except Exception as e:
            print(f"❌ Profile completeness check failed: {e}")
            return {
                "is_complete": False,
                "missing_fields": settings.REQUIRED_PROFILE_FIELDS,
                "completeness_percentage": 0.0,
                "message": f"Profile check failed: {str(e)}"
            }
    
    async def create_login_session(self, phone: str) -> Dict[str, Any]:
        """Create session after successful login"""
        await self._get_services()
        
        try:
            # Get customer data
            customer_data = await self.cache.get_customer(phone)
            
            if not customer_data:
                from db.database import users_collection
                customer_data = users_collection.find_one({"phone": phone})
                
                if customer_data:
                    await self.cache.set_customer(phone, customer_data)
            
            if not customer_data:
                customers = load_mock_customers()
                customer_data = next((c for c in customers if c.get("phone") == phone), None)
                if customer_data:
                    await self.cache.set_customer(phone, customer_data)
            
            if not customer_data:
                raise Exception("Customer not found")
            
            # Get loan history to enrich profile
            history_result = await self.get_customer_loan_history(phone)
            past_loans = history_result.get("history", [])
            customer_data["past_loans"] = past_loans
            customer_data["is_new_customer"] = len(past_loans) == 0
            
            # Aggregate active EMI from historical loans
            active_emi = sum(loan.get("emi", 0) for loan in past_loans if loan.get("status") == "Approved")
            customer_data["existing_emi_total"] = active_emi
            print(f"💰 Aggregated active EMI for {phone}: ₹{active_emi:,.2f}")
            
            # Create new session
            from api.core.state_manager import create_session
            session = await create_session()
            session_id = session["session_id"]
            
            # Update session with customer data
            await update_session(session_id, {
                "customer_data": customer_data,
                "customer_id": str(customer_data.get("_id", phone)),
                "current_phase": "logged_in",
                "login_time": datetime.utcnow().isoformat()
            })
            
            # Cache session for performance
            await self.cache.set_session(session_id, session)
            
            print(f"✅ Login session created for {phone}: {session_id}")
            
            return {
                "session_id": session_id,
                "customer_data": customer_data,
                "login_time": session.get("login_time")
            }
        
        except Exception as e:
            print(f"❌ Login session creation failed: {e}")
            raise e
    
    async def update_customer_profile(self, phone: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update customer profile fields"""
        await self._get_services()
        
        try:
            # Get existing customer data
            customer_data = await self.cache.get_customer(phone)
            
            if not customer_data:
                from db.database import users_collection
                customer_data = users_collection.find_one({"phone": phone})
                
                if not customer_data:
                    return {
                        "success": False,
                        "message": "Customer not found"
                    }
            
            # Update customer data
            updated_data = {**customer_data, **updates}
            
            # Update in database
            from db.database import users_collection
            users_collection.update_one(
                {"phone": phone},
                {"$set": updates}
            )
            
            # Update cache
            await self.cache.set_customer(phone, updated_data)
            
            # Check if profile is now complete
            profile_check = await self.check_profile_completeness(phone)
            
            return {
                "success": True,
                "message": "Profile updated successfully",
                "updated_fields": list(updates.keys()),
                "profile_complete": profile_check["is_complete"],
                "completeness_percentage": profile_check["completeness_percentage"]
            }
        
        except Exception as e:
            print(f"❌ Profile update failed: {e}")
            return {
                "success": False,
                "message": f"Profile update failed: {str(e)}"
            }
    
    async def get_customer_loan_history(self, phone: str) -> Dict[str, Any]:
        """Get customer's loan history with caching"""
        await self._get_services()
        
        try:
            # Try cache first
            cached_history = await self.cache.get_loan_history(phone)
            if cached_history:
                print(f"🎯 Loan history cache HIT for {phone}")
                return {
                    "history": cached_history,
                    "cached": True
                }
            
            # Get from database
            from db.database import loan_applications_collection
            applications = loan_applications_collection.find({"phone": phone})
            
            # Convert to list and sort
            history = []
            for app in applications:
                history.append({
                    "session_id": app.get("session_id"),
                    "amount": app.get("amount", 0),
                    "loan_type": app.get("loan_type", ""),
                    "status": app.get("status", ""),
                    "created_at": app.get("created_at", ""),
                    "interest_rate": app.get("interest_rate", 0),
                    "tenure": app.get("tenure", 0),
                    "emi": app.get("emi", 0)
                })
            
            # Sort by created_at descending
            history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # Cache for 30 minutes
            await self.cache.set_loan_history(phone, history)
            
            print(f"⚡ Loan history cache MISS for {phone}")
            
            return {
                "history": history,
                "cached": False,
                "total_applications": len(history),
                "approved_loans": len([h for h in history if h.get("status") == "Approved"]),
                "rejected_applications": len([h for h in history if h.get("status") == "Rejected"])
            }
        
        except Exception as e:
            print(f"❌ Loan history retrieval failed: {e}")
            return {
                "history": [],
                "cached": False,
                "error": str(e)
            }
    
    async def login_with_password(self, phone: str, password: str) -> Dict[str, Any]:
        """Login with phone and password using mock customers database."""
        customers = load_mock_customers()
        user = next((c for c in customers if c.get("phone") == phone), None)
        
        if not user:
            return {"success": False, "message": "User not found"}
        
        if user.get("password") != password:
            return {"success": False, "message": "Invalid password"}
        
        # Create session
        session_data = await self.create_login_session(phone)
        
        return {
            "success": True,
            "message": "Login successful",
            "session_id": session_data["session_id"],
            "customer_data": user
        }

    async def register_customer(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register new customer and save to both mock JSON and MongoDB."""
        phone = user_data.get("phone")
        if not phone:
            return {"success": False, "message": "Phone number required"}
            
        customers = load_mock_customers()
        if any(c.get("phone") == phone for c in customers):
            return {"success": False, "message": "User already exists"}
            
        # Add to mock database
        new_user = {
            "id": f"CUST{len(customers) + 1:03d}",
            **user_data,
            "credit_score": user_data.get("credit_score", 700),
            "pre_approved_limit": user_data.get("pre_approved_limit", 100000),
            "existing_emi_total": user_data.get("existing_emi_total", 0),
            "current_loans": [],
            "risk_flags": [],
            "created_at": datetime.utcnow().isoformat()
        }
        customers.append(new_user)
        save_mock_customers(customers)
        
        # Also save to MongoDB users collection
        try:
            from db.database import users_collection
            users_collection.insert_one({"_id": phone, **new_user})
        except Exception as e:
            print(f"⚠️ Failed to save to MongoDB: {e}")
            
        return {"success": True, "message": "Registration successful", "customer_data": new_user}

    async def verify_session(self, session_id: str) -> Dict[str, Any]:
        """Verify if a session exists and return customer data."""
        await self._get_services()
        try:
            # Check MongoDB for the session
            from api.core.state_manager import get_session
            session = await get_session(session_id)
            
            if not session:
                return {"success": False, "message": "Session not found or expired"}
                
            customer_data = session.get("customer_data")
            if not customer_data:
                return {"success": False, "message": "Customer data not found in session"}
                
            return {
                "success": True,
                "customer_data": customer_data,
                "session_id": session_id
            }
        except Exception as e:
            print(f"❌ Session verification failed: {e}")
            return {"success": False, "message": str(e)}

# Global auth service instance
auth_service = AuthService()


async def get_auth_service() -> AuthService:
    """Get the global auth service instance"""
    return auth_service
