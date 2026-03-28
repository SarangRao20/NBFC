"""Authentication Service — Customer identification and session management."""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from api.core.redis_cache import get_cache, RedisCache
from api.core.email_service import get_email_service, EmailService
from api.core.state_manager import get_session, update_session
from api.config import get_settings
from utils.validators import normalize_phone
from mock_apis.otp_service import send_otp as mock_send_otp, verify_otp as mock_verify_otp
from mock_apis.cibil_api import get_cibil_score as mock_get_cibil_score

settings = get_settings()

# Only use mock customers in development/mock mode
CUSTOMERS_FILE = os.path.join("mock_apis", "customers.json")

def load_mock_customers() -> List[Dict]:
    """Load mock customers only in development mode"""
    if settings.APP_ENV == "production":
        return []
    if os.path.exists(CUSTOMERS_FILE):
        with open(CUSTOMERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_mock_customers(customers: List[Dict]):
    """Save mock customers only in development mode"""
    if settings.APP_ENV == "production":
        return
    with open(CUSTOMERS_FILE, "w") as f:
        json.dump(customers, f, indent=4)


def find_mock_customer_by_phone(customers: List[Dict], phone: str) -> Optional[Dict[str, Any]]:
    """Find a customer from customers.json using normalized phone comparison."""
    normalized = normalize_phone(phone)
    if len(normalized) != 10:
        return None
    return next(
        (c for c in customers if normalize_phone(c.get("phone", "")) == normalized),
        None,
    )


class AuthService:
    """Enhanced authentication service with caching and profile management"""
    
    def __init__(self):
        self.cache: Optional[RedisCache] = None
        self.email_service: Optional[EmailService] = None
    
    async def _get_services(self):
        """Initialize services if not already done"""
        if not self.cache:
            self.cache = await get_cache()
        if not self.email_service:
            self.email_service = await get_email_service()

    def _cache_service(self) -> RedisCache:
        """Return initialized cache service as non-optional for type checkers."""
        if self.cache is None:
            raise RuntimeError("Cache initialization failed")
        return self.cache

    def _email_service_client(self) -> EmailService:
        """Return initialized email service as non-optional for type checkers."""
        if self.email_service is None:
            raise RuntimeError("Email service initialization failed")
        return self.email_service

    @staticmethod
    def _derive_pre_approved_limit(credit_score: int, salary: Optional[float]) -> int:
        """Derive a simple mock pre-approved limit using score and salary."""
        monthly_salary = float(salary or 0)

        if credit_score >= 800:
            multiplier = 6.0
        elif credit_score >= 750:
            multiplier = 5.0
        elif credit_score >= 700:
            multiplier = 4.0
        elif credit_score >= 650:
            multiplier = 3.0
        else:
            multiplier = 2.0

        base_limit = int(monthly_salary * multiplier) if monthly_salary > 0 else 100000
        base_limit = max(base_limit, 100000)

        # Soft caps by risk band for a realistic mock profile.
        if credit_score < 650:
            return min(base_limit, 200000)
        if credit_score < 700:
            return min(base_limit, 400000)
        if credit_score < 750:
            return min(base_limit, 800000)
        return min(base_limit, 1500000)

    async def fetch_credit_score(
        self,
        phone: str,
        pan: Optional[str] = None,
        full_name: Optional[str] = None,
        dob: Optional[str] = None,
        persist: bool = False,
    ) -> Dict[str, Any]:
        """Fetch mock CIBIL/credit score and optionally persist it to customer profile."""
        await self._get_services()
        cache = self._cache_service()
        phone = normalize_phone(phone)

        try:
            result = mock_get_cibil_score(phone=phone, pan=pan, full_name=full_name, dob=dob)
            if not result.get("success"):
                return result

            score = int(result.get("credit_score", 0))

            if persist:
                customers = load_mock_customers()
                customer = find_mock_customer_by_phone(customers, phone)

                updates: Dict[str, Any] = {"credit_score": score}
                if customer:
                    derived_limit = self._derive_pre_approved_limit(score, customer.get("salary"))
                    updates["pre_approved_limit"] = derived_limit
                    customer.update(updates)
                    save_mock_customers(customers)

                try:
                    from db.database import users_collection
                    await users_collection.update_one({"phone": phone}, {"$set": updates})
                except Exception as db_err:
                    print(f"⚠️ Failed to persist credit score to MongoDB: {db_err}")

                cached_customer = await cache.get_customer(phone)
                if cached_customer:
                    cached_customer.update(updates)
                    await cache.set_customer(phone, cached_customer)

                result["persisted"] = True
                result["profile_updates"] = updates
            else:
                result["persisted"] = False

            return result
        except Exception as e:
            print(f"❌ Credit score fetch failed: {e}")
            return {
                "success": False,
                "message": f"Failed to fetch credit score: {str(e)}",
                "phone": phone,
            }
    
    async def generate_otp(self, phone: str) -> str:
        """Generate 6-digit OTP"""
        await self._get_services()
        cache = self._cache_service()
        
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Cache OTP with 5-minute expiry
        await cache.set_otp(phone, otp)
        
        print(f"🔐 OTP generated for {phone}: {otp}")
        return otp
    
    async def generate_dev_otp(self, phone: str, dev_otp: str) -> bool:
        """Generate development OTP"""
        await self._get_services()
        cache = self._cache_service()
        
        # Cache development OTP with longer expiry for testing
        await cache.set_otp(phone, dev_otp)
        
        print(f"🛠️ Development OTP set for {phone}: {dev_otp}")
        return True
    
    async def send_otp(self, phone: str, email: Optional[str] = None) -> Dict[str, Any]:
        """Send OTP using mock_apis/otp_service.py"""
        await self._get_services()
        cache = self._cache_service()
        email_service = self._email_service_client()
        phone = normalize_phone(phone)
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
                    customer = await cache.get_customer(phone) or {}
                    customer_name = customer.get("name", "Customer")
                    email_sent = await email_service.send_otp_email(email, customer_name, otp)
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
        phone = normalize_phone(phone)
        
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
        cache = self._cache_service()
        phone = normalize_phone(phone)
        
        try:
            # Get customer data from cache first, then DB
            customer_data = await cache.get_customer(phone)
            
            if not customer_data:
                # Try to get from database
                from db.database import users_collection
                customer_data = await users_collection.find_one({"phone": phone})
                
                if customer_data:
                    # Cache for future use
                    await cache.set_customer(phone, customer_data)
            
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
        cache = self._cache_service()
        phone = normalize_phone(phone)
        
        try:
            # Get customer data
            customer_data = await cache.get_customer(phone)
            
            if not customer_data:
                from db.database import users_collection
                customer_data = await users_collection.find_one({"phone": phone})
                
                if customer_data:
                    await cache.set_customer(phone, customer_data)
            
            if not customer_data:
                customers = load_mock_customers()
                customer_data = find_mock_customer_by_phone(customers, phone)
                if customer_data:
                    # Keep DB in sync for future DB-first lookups.
                    try:
                        from db.database import users_collection
                        db_user = await users_collection.find_one({"phone": phone})
                        if db_user:
                            await users_collection.update_one({"phone": phone}, {"$set": customer_data})
                        else:
                            await users_collection.insert_one({"_id": phone, **customer_data, "phone": phone})
                    except Exception as sync_err:
                        print(f"⚠️ Failed to backfill MongoDB user during login session creation: {sync_err}")
                    await cache.set_customer(phone, customer_data)
            
            if not customer_data:
                raise Exception("Customer not found")

            # Ensure credit score is available for underwriting.
            score_missing = not isinstance(customer_data.get("credit_score"), (int, float)) or customer_data.get("credit_score", 0) <= 0
            if score_missing:
                credit_result = await self.fetch_credit_score(
                    phone=phone,
                    full_name=customer_data.get("name"),
                    dob=customer_data.get("dob"),
                    persist=True,
                )
                if credit_result.get("success"):
                    customer_data["credit_score"] = credit_result.get("credit_score", customer_data.get("credit_score", 700))
                    profile_updates = credit_result.get("profile_updates", {})
                    if "pre_approved_limit" in profile_updates:
                        customer_data["pre_approved_limit"] = profile_updates["pre_approved_limit"]
                    print(f"✅ Auto-fetched credit score for {phone}: {customer_data.get('credit_score')}")
                else:
                    print(f"⚠️ Credit score auto-fetch failed for {phone}: {credit_result.get('message')}")
            
            # Get loan history to enrich profile
            history_result = await self.get_customer_loan_history(phone)
            past_loans = history_result.get("history", [])
            customer_data["past_loans"] = past_loans
            customer_data["is_new_customer"] = len(past_loans) == 0
            
            # Aggregate active EMI from historical loans (Exclude Closed/Rejected)
            active_emi = sum(loan.get("emi", 0) for loan in past_loans 
                            if loan.get("status") == "Approved" and not loan.get("is_closed"))
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
            await cache.set_session(session_id, session)
            
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
        cache = self._cache_service()
        phone = normalize_phone(phone)
        
        try:
            # Get existing customer data
            customer_data = await cache.get_customer(phone)
            
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
            await cache.set_customer(phone, updated_data)
            
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
        cache = self._cache_service()
        phone = normalize_phone(phone)
        
        try:
            # Try cache first
            cached_history = await cache.get_loan_history(phone)
            if cached_history:
                print(f"🎯 Loan history cache HIT for {phone}")
                return {
                    "history": cached_history,
                    "cached": True
                }
            
            # Get from database
            from db.database import loan_applications_collection
            cursor = loan_applications_collection.find({"phone": phone})
            applications = await cursor.to_list(length=100)
            
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
            await cache.set_loan_history(phone, history)
            
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
        """Login with phone and password using MongoDB database with safe fallback."""
        phone = normalize_phone(phone)
        if len(phone) != 10:
            return {"success": False, "message": "Invalid phone number"}
        
        await self._get_services()
        
        try:
            # First check MongoDB
            from db.database import users_collection
            user = await users_collection.find_one({"phone": phone})
            if not user:
                user = await users_collection.find_one({"_id": phone})
            
            # If not found in MongoDB and in development mode, check mock customers
            if not user and get_settings().APP_ENV != "production":
                customers = load_mock_customers()
                user = find_mock_customer_by_phone(customers, phone)
                if user:
                    user["phone"] = phone
                    # Backfill to DB
                    try:
                        db_user = await users_collection.find_one({"phone": phone})
                        if db_user:
                            await users_collection.update_one({"phone": phone}, {"$set": user})
                        else:
                            await users_collection.insert_one({"_id": phone, **user})
                    except Exception as sync_err:
                        print(f"⚠️ Failed to backfill MongoDB user during login fallback: {sync_err}")
            
            if not user:
                return {
                    "success": False,
                    "message": "User not found"
                }
            
            # Check password
            if user.get("password") != password:
                return {
                    "success": False,
                    "message": "Invalid password"
                }
            
            # Create session
            session_result = await self.create_login_session(phone)
            
            return {
                "success": True,
                "message": "Login successful",
                "user": user,
                "customer_data": session_result.get("customer_data", user),
                "session_id": session_result["session_id"]
            }
            
        except Exception as e:
            print(f"❌ Login error: {e}")
            return {
                "success": False,
                "message": f"Login failed: {str(e)}"
            }

    async def register_customer(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register new customer with DB-first persistence and mock sync fallback."""
        phone = normalize_phone(user_data.get("phone", ""))
        if len(phone) != 10:
            return {"success": False, "message": "Phone number required"}

        user_data = {**user_data, "phone": phone}
        if user_data.get("email"):
            user_data["email"] = str(user_data["email"]).strip().lower()

        # Check existence in DB first to avoid split-brain records.
        try:
            from db.database import users_collection
            existing_db_user = await users_collection.find_one({"phone": phone})
            if existing_db_user:
                return {"success": False, "message": "User already exists"}
        except Exception as e:
            return {"success": False, "message": f"Registration failed: database unavailable ({str(e)})"}
            
        customers = load_mock_customers()
        if any(normalize_phone(c.get("phone", "")) == phone for c in customers):
            return {"success": False, "message": "User already exists"}

        # Fetch mock CIBIL score if missing from input.
        requested_score = user_data.get("credit_score")
        resolved_credit_score = requested_score if isinstance(requested_score, (int, float)) and requested_score > 0 else None
        if resolved_credit_score is None:
            cibil = mock_get_cibil_score(
                phone=phone,
                full_name=user_data.get("name"),
                dob=user_data.get("dob")
            )
            resolved_credit_score = cibil.get("credit_score", 700) if cibil.get("success") else 700

        requested_limit = user_data.get("pre_approved_limit")
        if isinstance(requested_limit, (int, float)) and requested_limit > 0:
            resolved_pre_approved_limit = int(requested_limit)
        else:
            resolved_pre_approved_limit = self._derive_pre_approved_limit(
                int(resolved_credit_score),
                user_data.get("salary")
            )
            
        # Add to mock database
        new_user = {
            "id": f"CUST{len(customers) + 1:03d}",
            **user_data,
            "credit_score": int(resolved_credit_score),
            "pre_approved_limit": resolved_pre_approved_limit,
            "existing_emi_total": user_data.get("existing_emi_total", 0),
            "current_loans": [],
            "risk_flags": [],
            "created_at": datetime.utcnow().isoformat()
        }
        try:
            # Write to DB first.
            await users_collection.insert_one({"_id": phone, **new_user})
        except Exception as e:
            return {"success": False, "message": f"Registration failed: could not persist user ({str(e)})"}

        # Sync mock JSON for legacy components that still read it.
        try:
            customers.append(new_user)
            save_mock_customers(customers)
        except Exception as sync_err:
            print(f"⚠️ Failed to sync customers.json after DB registration: {sync_err}")
            
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
