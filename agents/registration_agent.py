"""Registration Agent — collects user profile, verifies OTP, sets PIN, fetches bank details."""

import hashlib

from mock_apis.otp_service import send_otp, verify_otp
from mock_apis.digilocker_api import initiate_digilocker_session, verify_digilocker_otp
from mock_apis.bank_details_api import get_bank_details
from utils.validators import validate_phone, validate_email, validate_pin, validate_positive_number
from state import LoanState


def _prompt_with_validation(prompt_text: str, validator_fn, allow_empty: bool = False) -> str:
    """Keep asking until valid input is received."""
    while True:
        value = input(prompt_text).strip()
        if allow_empty and value == "":
            return value
        is_valid, error = validator_fn(value)
        if is_valid:
            return value
        print(f"  ⚠️  {error}")


def _collect_personal_info() -> dict:
    """Step 1: Collect name, phone, email."""
    print("\n╔══════════════════════════════════════╗")
    print("║       📋 PERSONAL INFORMATION        ║")
    print("╚══════════════════════════════════════╝\n")

    full_name = ""
    while not full_name:
        full_name = input("  Full Name: ").strip()
        if not full_name:
            print("  ⚠️  Name cannot be empty.")

    phone = _prompt_with_validation("  Phone Number (10 digits): ", validate_phone)
    email = _prompt_with_validation("  Email (optional, press Enter to skip): ", validate_email, allow_empty=True)

    address = ""
    while not address:
        address = input("  Current Address: ").strip()
        if not address:
            print("  ⚠️  Address cannot be empty.")

    return {"full_name": full_name, "phone": phone, "email": email, "address": address}


def _do_otp_verification(phone: str) -> bool:
    """Step 2: Send OTP and verify."""
    print("\n╔══════════════════════════════════════╗")
    print("║         📱 OTP VERIFICATION          ║")
    print("╚══════════════════════════════════════╝\n")

    while True:
        result = send_otp(phone)
        if not result["sent"]:
            print(f"  ❌ {result['message']}")
            return False

        for _ in range(3):
            user_otp = input("  Enter the OTP: ").strip()
            verify_result = verify_otp(phone, user_otp)
            print(f"  {verify_result['message']}")
            if verify_result["verified"]:
                return True

        retry = input("\n  OTP verification failed. Resend OTP? (yes/no): ").strip().lower()
        if retry not in ("yes", "y"):
            return False


def _collect_employment_info() -> dict:
    """Step 3: Collect employment type and income."""
    print("\n╔══════════════════════════════════════╗")
    print("║       💼 EMPLOYMENT INFORMATION      ║")
    print("╚══════════════════════════════════════╝\n")

    employment_type = ""
    while employment_type not in ("salaried", "self-employed"):
        employment_type = input("  Employment Type (salaried / self-employed): ").strip().lower()
        if employment_type not in ("salaried", "self-employed"):
            print("  ⚠️  Please enter 'salaried' or 'self-employed'.")

    income_str = _prompt_with_validation(
        "  Monthly Income (₹): ",
        lambda v: validate_positive_number(v, "Monthly income"),
    )
    return {"employment_type": employment_type, "monthly_income": float(income_str)}


def _prompt_aadhaar() -> str:
    """Prompt for a 12 digit Aadhaar."""
    while True:
        aadhaar = input("  Aadhaar Number (12 digits): ").strip()
        if len(aadhaar) == 12 and aadhaar.isdigit():
            return aadhaar
        print("  ⚠️  Aadhaar must be exactly 12 digits.")
    return ""

def _do_digilocker_kyc() -> dict:
    """Step 4: Fetch KYC via DigiLocker using Aadhaar."""
    print("\n╔══════════════════════════════════════╗")
    print("║     🔒 DIGILOCKER E-KYC (AADHAAR)    ║")
    print("╚══════════════════════════════════════╝\n")

    while True:
        aadhaar = _prompt_aadhaar()
        res = initiate_digilocker_session(aadhaar)
        
        if not res["success"]:
            print(f"  ❌ {res['message']}")
            continue
            
        print(f"  {res['message']}")
        session_id = res["session_id"]
        
        for _ in range(3):
            otp = input(f"  Enter UIDAI OTP sent to linked mobile: ").strip()
            verify_res = verify_digilocker_otp(session_id, otp, aadhaar)
            
            if verify_res["success"]:
                print(f"  ✅ {verify_res['message']}")
                docs = verify_res["documents"]
                
                # Extract PAN from the fetched digilocker documents
                fetched_pan = docs.get("pan_record", {}).get("pan_number", "NOT_FOUND")
                print(f"  ✅ Auto-fetched PAN from DigiLocker: {fetched_pan}")
                
                return {
                    "aadhaar": aadhaar,
                    "kyc_verified": True,
                    "pan": fetched_pan
                }
            else:
                print(f"  ❌ {verify_res['message']}")
        
        retry = input("\n  DigiLocker KYC failed. Try another Aadhaar? (yes/no): ").strip().lower()
        if retry not in ("yes", "y"):
            return {
                "aadhaar": aadhaar,
                "kyc_verified": False,
                "pan": ""
            }


def _collect_bank_details() -> dict:
    """Step 6: Collect bank name and fetch details."""
    print("\n╔══════════════════════════════════════╗")
    print("║        🏦 BANK DETAILS               ║")
    print("╚══════════════════════════════════════╝\n")

    while True:
        bank_name = input("  Enter your Bank Name (e.g., SBI, HDFC, ICICI): ").strip()
        if not bank_name:
            print("  ⚠️  Bank name cannot be empty.")
            continue

        result = get_bank_details(bank_name)
        if result["found"]:
            return {
                "bank_name": result["bank_name"],
                "bank_account_number": result["account_number"],
                "bank_ifsc": result["ifsc"],
            }
        else:
            print(f"  ❌ {result['error']}")
            print("  Please try again.\n")


def _set_pin() -> str:
    """Step 7: Set 4-digit PIN. Returns SHA-256 hash."""
    print("\n╔══════════════════════════════════════╗")
    print("║         🔐 SET SECURITY PIN          ║")
    print("╚══════════════════════════════════════╝\n")

    choice = ""
    while choice not in ("new", "bank"):
        choice = input("  Set a new PIN or use your bank account PIN? (new/bank): ").strip().lower()
        if choice not in ("new", "bank"):
            print("  ⚠️  Please enter 'new' or 'bank'.")

    if choice == "bank":
        pin = _prompt_with_validation("  Enter your Bank Account PIN (4 digits): ", validate_pin)
    else:
        while True:
            pin = _prompt_with_validation("  Create a 4-digit PIN: ", validate_pin)
            confirm = input("  Confirm PIN: ").strip()
            if pin == confirm:
                break
            print("  ⚠️  PINs do not match. Try again.\n")

    pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    print("  ✅ PIN set successfully!\n")
    return pin_hash


def registration_node(state: LoanState) -> dict:
    """
    LangGraph node — Registration Agent.

    Flow: Personal Info → OTP → Employment → DigiLocker KYC → Bank → PIN
    """
    print("\n" + "=" * 50)
    print("  🏢 REGISTRATION AGENT")
    print("  Register your profile to proceed with the loan")
    print("=" * 50)

    updates: dict = {"current_agent": "registration", "errors": state.get("errors", [])}

    # Step 1: Personal Info
    personal = _collect_personal_info()
    updates.update(personal)

    # Step 2: OTP Verification
    otp_ok = _do_otp_verification(personal["phone"])
    updates["otp_verified"] = otp_ok
    if not otp_ok:
        updates["errors"] = updates["errors"] + ["OTP verification failed"]
        print("\n  ❌ OTP verification failed. Registration incomplete.")
        return updates

    # Step 3: Employment Info
    employment = _collect_employment_info()
    updates.update(employment)

    # Step 4: DigiLocker KYC (Replaces manual PAN & ABC ID)
    kyc_update = _do_digilocker_kyc()
    updates.update(kyc_update)
    if not kyc_update.get("kyc_verified"):
        updates["errors"] = updates["errors"] + ["DigiLocker KYC failed"]

    # Step 6: Bank Details
    bank = _collect_bank_details()
    updates.update(bank)

    # Step 7: Set PIN
    updates["pin_hash"] = _set_pin()

    # Summary
    print("\n" + "=" * 50)
    print("  ✅ REGISTRATION COMPLETE")
    print("=" * 50)
    print(f"  Name:        {updates['full_name']}")
    print(f"  Phone:       {updates['phone']}")
    print(f"  Email:       {updates.get('email') or 'N/A'}")
    print(f"  Address:     {updates['address']}")
    print(f"  Employment:  {updates['employment_type']}")
    print(f"  Income:      ₹{updates['monthly_income']:,.0f}")
    print(f"  PAN:         {updates['pan']}")
    print(f"  Bank:        {updates['bank_name']}")
    print(f"  Account:     {updates['bank_account_number']}")
    print(f"  IFSC:        {updates['bank_ifsc']}")
    print(f"  OTP:         ✅ Verified")
    print(f"  Aadhaar / KYC:  {'✅ Verified (DigiLocker)' if updates.get('kyc_verified') else '❌ Not Verified'}")
    print(f"  PIN:         ✅ Set (hashed)")
    print("=" * 50 + "\n")

    return updates
