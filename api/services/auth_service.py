"""Authentication Service - Enhanced with Redis caching, OTP management, and profile completeness."""

import random
import string
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from api.core.redis_cache import get_cache
from api.core.email_service import get_email_service
from api.core.state_manager import get_session, update_session
from api.config import get_settings

settings = get_settings()


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
    
    async def send_otp(self, phone: str, email: str) -> Dict[str, Any]:
        """Send OTP to customer's email or use dev mode"""
        await self._get_services()
        
        # Priority: Development mode toggle
        if settings.DISABLE_OTP:
            await self.generate_dev_otp(phone, settings.DEV_OTP)
            return {
                "success": True,
                "message": f"Development mode: Your OTP is {settings.DEV_OTP}",
                "phone": phone,
                "email": email,
                "otp_sent": False,
                "dev_otp": settings.DEV_OTP
            }

        try:
            # Get customer data to personalize email

            customer_data = await self.cache.get_customer(phone)
            customer_name = customer_data.get('name', 'Customer') if customer_data else 'Customer'
            
            # Generate OTP
            otp = await self.generate_otp(phone)
            
            # Send email
            email_sent = await self.email_service.send_otp_email(email, customer_name, otp)
            
            if email_sent:
                return {
                    "success": True,
                    "message": "OTP sent to your registered email address",
                    "phone": phone,
                    "email": email,
                    "otp_sent": True
                }
            else:
                # Fallback: show OTP in development mode
                if settings.DISABLE_OTP:
                    return {
                        "success": True,
                        "message": f"Development mode: Your OTP is {settings.DEV_OTP}",
                        "phone": phone,
                        "email": email,
                        "otp_sent": False,
                        "dev_otp": settings.DEV_OTP
                    }
                else:
                    return {
                        "success": False,
                        "message": "Failed to send OTP email. Please try again.",
                        "phone": phone,
                        "email": email,
                        "otp_sent": False
                    }
        
        except Exception as e:
            print(f"❌ OTP send failed: {e}")
            return {
                "success": False,
                "message": f"Failed to send OTP: {str(e)}",
                "phone": phone,
                "email": email,
                "otp_sent": False
            }
    
    async def verify_otp(self, phone: str, otp: str) -> Dict[str, Any]:
        """Verify OTP against cached value"""
        await self._get_services()
        
        try:
            # In development mode, accept dev OTP
            if settings.DISABLE_OTP and otp == settings.DEV_OTP:
                await self.cache.delete_otp(phone)
                return {
                    "success": True,
                    "message": "Development OTP verified successfully",
                    "phone": phone,
                    "dev_mode": True
                }
            
            # Normal OTP verification
            cached_otp = await self.cache.get_otp(phone)
            
            if not cached_otp:
                return {
                    "success": False,
                    "message": "OTP expired or not found. Please request a new OTP.",
                    "phone": phone
                }
            
            if otp == cached_otp:
                # Delete OTP after successful verification
                await self.cache.delete_otp(phone)
                return {
                    "success": True,
                    "message": "OTP verified successfully",
                    "phone": phone
                }
            else:
                return {
                    "success": False,
                    "message": "Invalid OTP. Please check and try again.",
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
                customer_data = await users_collection.find_one({"phone": phone})
                
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
                customer_data = await users_collection.find_one({"phone": phone})
                
                if customer_data:
                    await self.cache.set_customer(phone, customer_data)
            
            if not customer_data:
                raise Exception("Customer not found")
            
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
                customer_data = await users_collection.find_one({"phone": phone})
                
                if not customer_data:
                    return {
                        "success": False,
                        "message": "Customer not found"
                    }
            
            # Update customer data
            updated_data = {**customer_data, **updates}
            
            # Update in database
            from db.database import users_collection
            await users_collection.update_one(
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
            applications = await loan_applications_collection.find({"phone": phone})
            
            # Convert to list and sort
            history = []
            async for app in applications:
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
    
    async def logout(self, session_id: str) -> bool:
        """Logout and clean up session"""
        await self._get_services()
        
        try:
            # Delete session from cache
            await self.cache.delete_session(session_id)
            
            # Mark session as ended in database
            from api.core.state_manager import end_session
            await end_session(session_id)
            
            print(f"✅ Logout successful for session: {session_id}")
            return True
        
        except Exception as e:
            print(f"❌ Logout failed: {e}")
            return False

# Global auth service instance
auth_service = AuthService()


async def get_auth_service() -> AuthService:
    """Get the global auth service instance"""
    return auth_service
