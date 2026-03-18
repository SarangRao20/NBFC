import streamlit as st
import hashlib

from mock_apis.otp_service import send_otp, verify_otp
from mock_apis.digilocker_api import initiate_digilocker_session, verify_digilocker_otp
from mock_apis.bank_details_api import get_bank_details
from utils.validators import validate_phone, validate_email, validate_pan, validate_pin, validate_positive_number

st.set_page_config(page_title="NBFC Registration", page_icon="🏦", layout="centered")

def init_session():
    defaults = {
        "step": 0,
        "loan_type": "personal",
        "full_name": "",
        "phone": "",
        "email": "",
        "address": "",
        "otp_sent": False,
        "otp_verified": False,
        "employment_type": "salaried",
        "monthly_income": 50000.0,
        "pan": "",
        "aadhaar": "",
        "kyc_verified": False,
        "dl_session_id": "",
        "dl_otp_sent": False,
        "bank_name": "",
        "bank_account_number": "",
        "bank_ifsc": "",
        "pin_hash": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

st.title("🏦 NBFC Loan Registration")

if st.session_state.step == 0:
    st.header("Step 0: Choose Loan Type")
    loan_type = st.selectbox(
        "Select Loan Type", 
        ["personal", "student", "business", "home"], 
        index=["personal", "student", "business", "home"].index(st.session_state.loan_type)
    )
    
    if st.button("Next ➡️"):
        st.session_state.loan_type = loan_type
        st.session_state.step = 1
        st.rerun()

elif st.session_state.step == 1:
    st.header("Step 1: Personal Information")
    full_name = st.text_input("Full Name", value=st.session_state.full_name)
    phone = st.text_input("Phone Number (10 digits)", value=st.session_state.phone)
    email = st.text_input("Email (optional)", value=st.session_state.email)
    address = st.text_area("Current Address", value=st.session_state.address)
    
    if st.button("Next ➡️"):
        errors = []
        if not full_name.strip(): errors.append("Name cannot be empty.")
        if not address.strip(): errors.append("Address cannot be empty.")
        import re
        if not re.fullmatch(r"\d{10}", phone.strip()):
            is_valid_phone, phone_err = False, "Phone must be exactly 10 digits."
            errors.append(phone_err)
        if email.strip():
            is_valid_email, email_err = validate_email(email)
            if not is_valid_email: errors.append(email_err)
        
        if errors:
            for e in errors: st.error(e)
        else:
            st.session_state.full_name = full_name.strip()
            st.session_state.phone = phone.strip()
            st.session_state.email = email.strip()
            st.session_state.address = address.strip()
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    st.header("Step 2: OTP Verification")
    st.write(f"Phone Number: **{st.session_state.phone}**")
    
    if not st.session_state.otp_sent:
        if st.button("Send OTP"):
            res = send_otp(st.session_state.phone)
            if res["sent"]:
                st.session_state.otp_sent = True
                st.session_state.current_otp = res.get("otp")
                st.success("OTP sent!")
                st.rerun()
            else:
                st.error(res["message"])
    else:
        if st.session_state.get("current_otp"):
            st.info(f"*(Development Mode) Your OTP is: **{st.session_state.current_otp}***")
        
        user_otp = st.text_input("Enter the OTP")
        if st.button("Verify"):
            res = verify_otp(st.session_state.phone, user_otp)
            if res["verified"]:
                st.session_state.otp_verified = True
                st.success(res["message"])
                st.session_state.step = 3
                st.rerun()
            else:
                st.error(res["message"])
                
        if st.button("Resend OTP"):
            st.session_state.otp_sent = False
            st.rerun()

elif st.session_state.step == 3:
    st.header("Step 3: Employment Information")
    emp_type = st.selectbox("Employment Type", ["salaried", "self-employed"], index=0 if st.session_state.employment_type == "salaried" else 1)
    income = st.number_input("Monthly Income (₹)", min_value=0.0, value=st.session_state.monthly_income, step=1000.0)
    
    if st.button("Next ➡️"):
        st.session_state.employment_type = emp_type
        st.session_state.monthly_income = float(income)
        st.session_state.step = 4
        st.rerun()

elif st.session_state.step == 4:
    st.header("Step 4: DigiLocker KYC (Aadhaar)")
    aadhaar = st.text_input("Aadhaar Number (12 digits)", value=st.session_state.aadhaar)
    
    if not st.session_state.dl_otp_sent:
        if st.button("Send UIDAI OTP"):
            if not aadhaar.isdigit() or len(aadhaar) != 12:
                st.error("Aadhaar must be exactly 12 digits.")
            else:
                res = initiate_digilocker_session(aadhaar)
                if res["success"]:
                    st.session_state.dl_otp_sent = True
                    st.session_state.dl_session_id = res["session_id"]
                    st.session_state.aadhaar = aadhaar
                    st.success(res["message"])
                    st.rerun()
                else:
                    st.error(res["message"])
    else:
        st.info("*(Development Mode) Use OTP: 123456*")
        dl_otp = st.text_input("Enter UIDAI OTP")
        
        if st.button("Verify & Fetch Documents"):
            res = verify_digilocker_otp(st.session_state.dl_session_id, dl_otp, st.session_state.aadhaar)
            if res["success"]:
                # Extract PAN dynamically
                fetched_pan = res["documents"].get("pan_record", {}).get("pan_number", "NOT_FOUND")
                
                st.session_state.kyc_verified = True
                st.session_state.pan = fetched_pan
                st.success("Documents fetched successfully from DigiLocker!")
                st.session_state.step = 5
                st.rerun()
            else:
                st.error(res["message"])
                
        if st.button("Cancel & Try Another Aadhaar"):
            st.session_state.dl_otp_sent = False
            st.rerun()

elif st.session_state.step == 5:
    st.header("Step 5: Bank Details")
    bank_name = st.text_input("Bank Name (e.g., SBI, HDFC, ICICI)", value=st.session_state.bank_name)
    
    if st.button("Verify & Next ➡️"):
        if not bank_name.strip():
            st.error("Bank name cannot be empty.")
        else:
            res = get_bank_details(bank_name)
            if res.get("found"):
                st.session_state.bank_name = res["bank_name"]
                st.session_state.bank_account_number = res["account_number"]
                st.session_state.bank_ifsc = res["ifsc"]
                st.success("Bank details fetched successfully!")
                st.session_state.step = 6
                st.rerun()
            else:
                st.error(res.get("error", "Bank not found."))

elif st.session_state.step == 6:
    st.header("Step 6: Set Security PIN")
    choice = st.radio("PIN Options", ("Set a new PIN", "Use Bank Account PIN"))
    
    if choice == "Set a new PIN":
        pin = st.text_input("Create a 4-digit PIN", type="password")
        confirm = st.text_input("Confirm PIN", type="password")
        
        if st.button("Complete Registration ➡️"):
            is_valid, err = validate_pin(pin)
            if not is_valid:
                st.error(err)
            elif pin != confirm:
                st.error("PINs do not match.")
            else:
                st.session_state.pin_hash = hashlib.sha256(pin.encode()).hexdigest()
                st.session_state.step = 7
                st.rerun()
                
    else:
        pin = st.text_input("Enter your Bank Account PIN (4 digits)", type="password")
        if st.button("Complete Registration ➡️"):
            is_valid, err = validate_pin(pin)
            if not is_valid:
                st.error(err)
            else:
                st.session_state.pin_hash = hashlib.sha256(pin.encode()).hexdigest()
                st.session_state.step = 7
                st.rerun()


elif st.session_state.step == 7:
    st.header("🎉 Registration Complete!")
    st.balloons()
    
    st.subheader("Your Profile Summary")
    st.write(f"**Name:** {st.session_state.full_name}")
    st.write(f"**Phone:** {st.session_state.phone}")
    st.write(f"**Email:** {st.session_state.email or 'N/A'}")
    st.write(f"**Address:** {st.session_state.address}")
    st.write(f"**Employment:** {st.session_state.employment_type.title()}")
    st.write(f"**Income:** ₹{st.session_state.monthly_income:,.0f}")
    st.write(f"**PAN (Auto-fetched):** {st.session_state.pan}")
    
    st.subheader("KYC Details")
    st.write(f"**Aadhaar:** {st.session_state.aadhaar}")
    st.write(f"**Digilocker Status:** {'✅ Verified' if st.session_state.kyc_verified else '❌ Failed'}")
    
    st.subheader("Bank Details")

    st.success("You are successfully registered. Ready for the next agent in the pipeline!")

    if st.button("Start Over"):
        st.session_state.clear()
        st.rerun()
