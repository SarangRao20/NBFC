"""Mock OTP Service — simulates SMS OTP verification."""

import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

_otp_store: dict = {}
_send_count: dict = {}

MAX_ATTEMPTS = 3
MAX_RESENDS = 5
OTP_EXPIRY_MINUTES = 5


def send_otp(phone: str) -> dict:
    """Generate 6-digit OTP, print to console (simulated SMS)."""
    _send_count.setdefault(phone, 0)
    if _send_count[phone] >= MAX_RESENDS:
        return {"sent": False, "message": f"Max OTP limit reached ({MAX_RESENDS})."}

    otp = str(random.randint(100000, 999999))
    _otp_store[phone] = {
        "otp": otp,
        "expires_at": datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "attempts": 0,
    }
    _send_count[phone] += 1

    # check environment dynamically
    load_dotenv(override=True)
    tw_sid = os.getenv("TWILIO_ACCOUNT_SID")
    tw_auth = os.getenv("TWILIO_AUTH_TOKEN")
    tw_phone = os.getenv("TWILIO_PHONE_NUMBER")
    
    use_twilio = bool(tw_sid and tw_auth and tw_phone)
    twilio_client = None
    if use_twilio:
        try:
            from twilio.rest import Client
            twilio_client = Client(tw_sid, tw_auth)
        except Exception:
            use_twilio = False

    # Send Real SMS via Twilio if configured
    if use_twilio and twilio_client:
        try:
            # Assuming Indian phone numbers format (+91...)
            formatted_phone = f"+91{phone}" if len(phone) == 10 else phone
            
            message = twilio_client.messages.create(
                body=f"Your NBFC Loan Registration OTP is: {otp}. Valid for {OTP_EXPIRY_MINUTES} mins.",
                from_=tw_phone,
                to=formatted_phone
            )
            print(f"  [Twilio] Sent real SMS OTP to {formatted_phone} (SID: {message.sid})")
        except Exception as e:
            error_msg = str(e)
            print(f"  ⚠️ Twilio Error: {error_msg}")
            
            # Delete the local OTP cache so they can actually retry properly
            if phone in _otp_store:
                del _otp_store[phone]
            _send_count[phone] -= 1
            
            return {"sent": False, "message": f"Twilio blocked the SMS: {error_msg}"}
    else:
        # Mock behavior
        print(f"\n{'='*40}")
        print(f"  📱 (Mock) OTP sent to {phone}: {otp}")
        print(f"  (Valid for {OTP_EXPIRY_MINUTES} minutes)")
        print(f"{'='*40}\n")

    return {"sent": True, "message": "OTP sent successfully.", "otp": otp}


def verify_otp(phone: str, user_otp: str) -> dict:
    """Check OTP match, expiry, and attempt count."""
    if phone not in _otp_store:
        return {"verified": False, "message": "No OTP sent to this number."}

    record = _otp_store[phone]

    if datetime.now() > record["expires_at"]:
        del _otp_store[phone]
        return {"verified": False, "message": "OTP expired. Request a new one."}

    if record["attempts"] >= MAX_ATTEMPTS:
        del _otp_store[phone]
        return {"verified": False, "message": f"Too many wrong attempts ({MAX_ATTEMPTS}). Request a new OTP."}

    record["attempts"] += 1
    if user_otp.strip() == record["otp"]:
        del _otp_store[phone]
        return {"verified": True, "message": "✅ OTP verified successfully!"}
    else:
        remaining = MAX_ATTEMPTS - record["attempts"]
        return {"verified": False, "message": f"❌ Wrong OTP. {remaining} attempt(s) remaining."}
