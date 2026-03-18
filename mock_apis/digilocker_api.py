"""Mock DigiLocker API — simulates document fetching for KYC."""

import time

def initiate_digilocker_session(aadhaar_number: str) -> dict:
    """Mock sending OTP from UIDAI to start a DigiLocker session."""
    aadhaar_number = str(aadhaar_number).strip()
    
    # We only accept valid 12 digit inputs for the mock
    if len(aadhaar_number) != 12 or not aadhaar_number.isdigit():
        return {
            "success": False, 
            "message": "Invalid Aadhaar. Must be exactly 12 digits."
        }
    
    # Simulate API delay
    time.sleep(1)
    last_four = aadhaar_number[-4:] if len(aadhaar_number) >= 4 else "0000"
    
    return {
        "success": True,
        "message": "DigiLocker consent OTP sent to Aadhaar-linked mobile.",
        "session_id": f"dl_session_{last_four}8a2c",
        "aadhaar": aadhaar_number
    }

def verify_digilocker_otp(session_id: str, otp: str, aadhaar: str) -> dict:
    """Mock verifying the Aadhaar OTP and pulling documents from DigiLocker."""
    
    if otp != "123456": # Hardcoded mock pass-OTP
        return {
            "success": False,
            "message": "Invalid UIDAI OTP. (Use 123456 for testing)"
        }
        
    time.sleep(1.5) # Simulate document download time
    
    last_four = aadhaar[-4:] if len(aadhaar) >= 4 else "0000"
    # Return mock fetched documents from DigiLocker
    return {
        "success": True,
        "message": "DigiLocker documents fetched successfully.",
        "documents": {
            "aadhaar_kyc": {
                "name": "MOCK USER SURNAME",
                "gender": "M",
                "dob": "1995-08-15",
                "address": "123 Fake Street, Mumbai, 400001",
                "verified": True
            },
            "pan_record": {
                "pan_number": f"ABCD{last_four}F", # Generates a dynamic looking PAN based on Aadhaar
                "name": "MOCK USER SURNAME",
                "status": "VALID",
                "issuing_authority": "Income Tax Department"
            }
        }
    }
