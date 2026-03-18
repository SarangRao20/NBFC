"""NBFC Loan Processing — Streamlit UI

Flow:  Sales Agent (chat) → Registration Agent (form wizard)
"""

import streamlit as st
import hashlib
import time

from mock_apis.otp_service import send_otp, verify_otp
from mock_apis.digilocker_api import initiate_digilocker_session, verify_digilocker_otp
from mock_apis.bank_details_api import get_bank_details
from mock_apis.loan_products import LOAN_PRODUCTS, calculate_emi
from utils.validators import validate_phone, validate_email, validate_pan, validate_pin, validate_positive_number

# ─── Page Config ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="NBFC Loan — FinServe", page_icon="🏦", layout="centered")

# ─── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Pipeline progress bar */
    .pipeline-bar {
        display: flex;
        gap: 0;
        margin: 1rem 0 2rem 0;
    }
    .pipeline-step {
        flex: 1;
        text-align: center;
        padding: 0.6rem 0.2rem;
        font-size: 0.8rem;
        font-weight: 600;
        border-bottom: 4px solid #333;
        color: #888;
        transition: all 0.3s ease;
    }
    .pipeline-step.active {
        border-bottom-color: #4CAF50;
        color: #4CAF50;
    }
    .pipeline-step.done {
        border-bottom-color: #2196F3;
        color: #2196F3;
    }

    /* Chat message styling */
    .sales-chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        border-radius: 12px;
        background: #0E1117;
        margin-bottom: 1rem;
    }

    /* Summary cards */
    .summary-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #2a3a5c;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }
    .summary-card h4 {
        color: #4CAF50;
        margin-bottom: 0.5rem;
    }

    /* Hide default streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── Session State Init ─────────────────────────────────────────────────────────
def init_session():
    defaults = {
        # Pipeline control
        "current_phase": "sales",       # "sales" or "registration"
        "reg_step": 0,                  # Registration sub-step (0-7)

        # Sales Agent state
        "sales_chat_history": [],       # [{"role": ..., "content": ...}]
        "sales_complete": False,
        "loan_type": "",
        "loan_amount": 0.0,
        "tenure": 0,
        "interest_rate": 0.0,

        # Registration Agent state
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


# ─── Pipeline Progress Bar ──────────────────────────────────────────────────────
def render_pipeline_bar():
    """Show overall pipeline progress."""
    phase = st.session_state.current_phase
    sales_done = st.session_state.sales_complete

    steps = [
        ("💼 Sales Agent", "sales"),
        ("📋 Registration Agent", "registration"),
    ]

    cols = st.columns(len(steps))
    for i, (label, step_id) in enumerate(steps):
        with cols[i]:
            if step_id == "sales" and sales_done:
                st.markdown(f"✅ **{label}**")
            elif step_id == phase:
                st.markdown(f"🔵 **{label}**")
            else:
                st.markdown(f"⬜ {label}")

    st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
#  SALES AGENT — Chat Interface
# ═══════════════════════════════════════════════════════════════════════════════

def render_sales_agent():
    st.header("💼 Sales Agent")
    st.caption("Chat with our sales advisor to find the perfect loan product for you.")

    # Show product catalog in an expander
    with st.expander("📦 View Available Loan Products", expanded=False):
        for key, prod in LOAN_PRODUCTS.items():
            st.markdown(f"""
**{prod['name']}** (`{key}`)
- Amount: ₹{prod['min_amount']:,} – ₹{prod['max_amount']:,}
- Tenure: {prod['min_tenure']} – {prod['max_tenure']} months
- Rate: {prod['base_rate']}% p.a.
- {prod['description']}
""")
            st.markdown("---")

    # Render chat history
    for msg in st.session_state.sales_chat_history:
        role = msg["role"]
        with st.chat_message("assistant" if role == "assistant" else "user",
                             avatar="💼" if role == "assistant" else "👤"):
            st.markdown(msg["content"])

    # If no history yet, show a greeting
    if not st.session_state.sales_chat_history:
        greeting = (
            "Hello! 👋 Welcome to **FinServe NBFC**. I'm your loan sales advisor.\n\n"
            "I'd love to help you find the right loan. Could you tell me **what you "
            "need the loan for**? For example:\n"
            "- 🏠 Buying or renovating a home\n"
            "- 🎓 Education / tuition fees\n"
            "- 💼 Business expansion\n"
            "- 💰 Personal needs (wedding, travel, medical)\n\n"
            "Just tell me your needs and I'll guide you through!"
        )
        st.session_state.sales_chat_history.append({"role": "assistant", "content": greeting})
        st.rerun()

    # Chat input
    if user_input := st.chat_input("Type your message...", key="sales_chat_input"):
        # Add user message
        st.session_state.sales_chat_history.append({"role": "user", "content": user_input})

        # Get LLM response
        with st.spinner("Sales Agent is thinking..."):
            from agents.sales_agent import sales_chat_response
            result = sales_chat_response(user_input, st.session_state.sales_chat_history[:-1])

        assistant_reply = result["reply"]
        extracted = result.get("extracted")

        st.session_state.sales_chat_history.append({"role": "assistant", "content": assistant_reply})

        # If the LLM confirmed loan details, finalize
        if extracted and extracted.get("confirmed"):
            st.session_state.loan_type = extracted.get("loan_type", "personal")
            st.session_state.loan_amount = float(extracted.get("loan_amount", 0))
            st.session_state.tenure = int(extracted.get("tenure", 0))
            st.session_state.interest_rate = float(extracted.get("interest_rate", 0))
            st.session_state.sales_complete = True

        st.rerun()

    # If sales is done, show confirmation + proceed button
    if st.session_state.sales_complete:
        st.success("✅ Loan details confirmed!")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Loan Type", st.session_state.loan_type.title())
        col2.metric("Amount", f"₹{st.session_state.loan_amount:,.0f}")
        col3.metric("Tenure", f"{st.session_state.tenure} months")
        col4.metric("Rate", f"{st.session_state.interest_rate}% p.a.")

        # EMI calculation
        if st.session_state.loan_amount > 0 and st.session_state.tenure > 0:
            emi_data = calculate_emi(
                st.session_state.loan_amount,
                st.session_state.interest_rate,
                st.session_state.tenure,
            )
            if "emi" in emi_data:
                st.info(f"📊 **Estimated EMI: ₹{emi_data['emi']:,.2f}/month** | "
                        f"Total Interest: ₹{emi_data['total_interest']:,.2f} | "
                        f"Total Payment: ₹{emi_data['total_payment']:,.2f}")

        st.divider()

        col_left, col_right = st.columns(2)
        with col_left:
            if st.button("🔄 Modify Loan Details", use_container_width=True):
                st.session_state.sales_complete = False
                st.session_state.sales_chat_history.append(
                    {"role": "user", "content": "I want to change my loan details."}
                )
                st.rerun()
        with col_right:
            if st.button("➡️ Proceed to Registration", type="primary", use_container_width=True):
                st.session_state.current_phase = "registration"
                st.session_state.reg_step = 1
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  REGISTRATION AGENT — Form Wizard
# ═══════════════════════════════════════════════════════════════════════════════

def render_registration_agent():
    step = st.session_state.reg_step

    st.header("📋 Registration Agent")

    # Show loan info summary from sales
    with st.expander("📦 Your Loan Details (from Sales Agent)", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Type", st.session_state.loan_type.title())
        c2.metric("Amount", f"₹{st.session_state.loan_amount:,.0f}")
        c3.metric("Tenure", f"{st.session_state.tenure} mo")
        c4.metric("Rate", f"{st.session_state.interest_rate}%")

    # Progress indicator
    total_steps = 7
    st.progress(min(step / total_steps, 1.0), text=f"Step {step} of {total_steps}")

    # ── Step 1: Personal Info ────────────────────────────────────────────────
    if step == 1:
        st.subheader("Step 1: Personal Information")
        full_name = st.text_input("Full Name", value=st.session_state.full_name)
        phone = st.text_input("Phone Number (10 digits)", value=st.session_state.phone)
        email = st.text_input("Email (optional)", value=st.session_state.email)
        address = st.text_area("Current Address", value=st.session_state.address)

        if st.button("Next ➡️"):
            errors = []
            if not full_name.strip():
                errors.append("Name cannot be empty.")
            if not address.strip():
                errors.append("Address cannot be empty.")
            import re
            if not re.fullmatch(r"\d{10}", phone.strip()):
                errors.append("Phone must be exactly 10 digits.")
            if email.strip():
                is_valid_email, email_err = validate_email(email)
                if not is_valid_email:
                    errors.append(email_err)

            if errors:
                for e in errors:
                    st.error(e)
            else:
                st.session_state.full_name = full_name.strip()
                st.session_state.phone = phone.strip()
                st.session_state.email = email.strip()
                st.session_state.address = address.strip()
                st.session_state.reg_step = 2
                st.rerun()

    # ── Step 2: OTP Verification ─────────────────────────────────────────────
    elif step == 2:
        st.subheader("Step 2: OTP Verification")
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
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Verify"):
                    res = verify_otp(st.session_state.phone, user_otp)
                    if res["verified"]:
                        st.session_state.otp_verified = True
                        st.success(res["message"])
                        st.session_state.reg_step = 3
                        st.rerun()
                    else:
                        st.error(res["message"])
            with col2:
                if st.button("Resend OTP"):
                    st.session_state.otp_sent = False
                    st.rerun()

    # ── Step 3: Employment Info ──────────────────────────────────────────────
    elif step == 3:
        st.subheader("Step 3: Employment Information")
        emp_type = st.selectbox(
            "Employment Type",
            ["salaried", "self-employed"],
            index=0 if st.session_state.employment_type == "salaried" else 1,
        )
        income = st.number_input(
            "Monthly Income (₹)",
            min_value=0.0,
            value=st.session_state.monthly_income,
            step=1000.0,
        )

        if st.button("Next ➡️"):
            st.session_state.employment_type = emp_type
            st.session_state.monthly_income = float(income)
            st.session_state.reg_step = 4
            st.rerun()

    # ── Step 4: DigiLocker KYC (Aadhaar) ─────────────────────────────────────
    elif step == 4:
        st.subheader("Step 4: DigiLocker KYC (Aadhaar)")
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

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Verify & Fetch Documents"):
                    res = verify_digilocker_otp(
                        st.session_state.dl_session_id, dl_otp, st.session_state.aadhaar
                    )
                    if res["success"]:
                        fetched_pan = (
                            res["documents"]
                            .get("pan_record", {})
                            .get("pan_number", "NOT_FOUND")
                        )
                        st.session_state.kyc_verified = True
                        st.session_state.pan = fetched_pan
                        st.success("Documents fetched successfully from DigiLocker!")
                        st.session_state.reg_step = 5
                        st.rerun()
                    else:
                        st.error(res["message"])
            with col2:
                if st.button("Cancel & Try Another Aadhaar"):
                    st.session_state.dl_otp_sent = False
                    st.rerun()

    # ── Step 5: Bank Details ─────────────────────────────────────────────────
    elif step == 5:
        st.subheader("Step 5: Bank Details")
        bank_name = st.text_input(
            "Bank Name (e.g., SBI, HDFC, ICICI)", value=st.session_state.bank_name
        )

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
                    st.session_state.reg_step = 6
                    st.rerun()
                else:
                    st.error(res.get("error", "Bank not found."))

    # ── Step 6: Set Security PIN ─────────────────────────────────────────────
    elif step == 6:
        st.subheader("Step 6: Set Security PIN")
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
                    st.session_state.reg_step = 7
                    st.rerun()
        else:
            pin = st.text_input("Enter your Bank Account PIN (4 digits)", type="password")
            if st.button("Complete Registration ➡️"):
                is_valid, err = validate_pin(pin)
                if not is_valid:
                    st.error(err)
                else:
                    st.session_state.pin_hash = hashlib.sha256(pin.encode()).hexdigest()
                    st.session_state.reg_step = 7
                    st.rerun()

    # ── Step 7: Complete ─────────────────────────────────────────────────────
    elif step == 7:
        st.header("🎉 Registration Complete!")
        st.balloons()

        # Loan Details
        st.subheader("📦 Loan Details")
        lc1, lc2, lc3, lc4 = st.columns(4)
        lc1.metric("Type", st.session_state.loan_type.title())
        lc2.metric("Amount", f"₹{st.session_state.loan_amount:,.0f}")
        lc3.metric("Tenure", f"{st.session_state.tenure} months")
        lc4.metric("Rate", f"{st.session_state.interest_rate}% p.a.")

        if st.session_state.loan_amount > 0 and st.session_state.tenure > 0:
            emi_data = calculate_emi(
                st.session_state.loan_amount,
                st.session_state.interest_rate,
                st.session_state.tenure,
            )
            if "emi" in emi_data:
                st.info(
                    f"📊 **Monthly EMI: ₹{emi_data['emi']:,.2f}** | "
                    f"Total Interest: ₹{emi_data['total_interest']:,.2f} | "
                    f"Total Payment: ₹{emi_data['total_payment']:,.2f}"
                )

        st.divider()

        # Profile Summary
        st.subheader("👤 Profile Summary")
        st.write(f"**Name:** {st.session_state.full_name}")
        st.write(f"**Phone:** {st.session_state.phone}")
        st.write(f"**Email:** {st.session_state.email or 'N/A'}")
        st.write(f"**Address:** {st.session_state.address}")
        st.write(f"**Employment:** {st.session_state.employment_type.title()}")
        st.write(f"**Income:** ₹{st.session_state.monthly_income:,.0f}")
        st.write(f"**PAN (Auto-fetched):** {st.session_state.pan}")

        st.subheader("🔒 KYC Details")
        st.write(f"**Aadhaar:** {st.session_state.aadhaar}")
        st.write(
            f"**Digilocker Status:** "
            f"{'✅ Verified' if st.session_state.kyc_verified else '❌ Failed'}"
        )

        st.subheader("🏦 Bank Details")
        st.write(f"**Bank:** {st.session_state.bank_name}")
        st.write(f"**Account:** {st.session_state.bank_account_number}")
        st.write(f"**IFSC:** {st.session_state.bank_ifsc}")

        st.divider()
        st.success(
            "✅ You are successfully registered. "
            "Ready for the next agent in the pipeline!"
        )

        if st.button("🔄 Start Over"):
            st.session_state.clear()
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

st.title("🏦 FinServe NBFC — Loan Processing")

render_pipeline_bar()

if st.session_state.current_phase == "sales":
    render_sales_agent()
elif st.session_state.current_phase == "registration":
    render_registration_agent()

# Sidebar info
with st.sidebar:
    st.markdown("### 🔄 Pipeline Status")
    st.markdown(
        f"**Current Phase:** {st.session_state.current_phase.title()}"
    )

    if st.session_state.sales_complete:
        st.markdown("---")
        st.markdown("### 📦 Selected Loan")
        st.write(f"**Type:** {st.session_state.loan_type.title()}")
        st.write(f"**Amount:** ₹{st.session_state.loan_amount:,.0f}")
        st.write(f"**Tenure:** {st.session_state.tenure} months")
        st.write(f"**Rate:** {st.session_state.interest_rate}% p.a.")

    st.markdown("---")
    if st.button("🔄 Reset Everything", use_container_width=True):
        st.session_state.clear()
        st.rerun()
