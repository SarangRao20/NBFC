"""FinServe NBFC — Master Agent Streamlit Application.

Pages:
  1. Login (OTP-based via Registration Agent)
  2. Chat (Sales → Document Upload → Underwriting pipeline)
  3. Profile (Loan history, document history, download letters)
"""

import streamlit as st
import os
import json
import time

from config import get_master_llm, get_extraction_llm, get_vision_llm
from agents.registration import build_registration_agent, RegistrationState, pull_customer_from_db, pull_customer_by_email
from agents.sales_agent import sales_chat_response, detect_apply_intent
from agents.document_query_agent import document_query_agent_node
from agents.emi_agent import emi_agent_node
from agents.document_agent import document_agent_node
from agents.kyc_agent import verification_agent_node
from agents.fraud_agent import fraud_agent_node
from agents.underwriting import underwriting_agent_node
from agents.advisor_agent import advisor_agent_node
from agents.sanction_agent import sanction_agent_node
from db.database import (
    save_loan_application, get_loan_history,
    save_chat_session, update_chat_session, get_chat_sessions, get_chat_messages,
    save_document_record, get_document_history
)
from langchain_core.messages import HumanMessage, AIMessage

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="FinServe NBFC", page_icon="🏦", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); }
    [data-testid="stSidebar"] { background: rgba(15,12,41,0.95); border-right: 1px solid rgba(255,255,255,0.1); }
    .metric-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 16px; margin: 8px 0; backdrop-filter: blur(10px); }
    .status-approved { color: #4ade80; font-weight: 700; }
    .status-rejected { color: #f87171; font-weight: 700; }
    .status-pending { color: #fbbf24; font-weight: 700; }
    h1, h2, h3 { color: #e2e8f0 !important; }
    p, span, label, .stMarkdown { color: #cbd5e1 !important; }
    .loan-card { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); border-radius: 16px; padding: 20px; margin: 12px 0; transition: transform 0.2s; }
    .loan-card:hover { transform: translateY(-2px); }
    div[data-testid="stChatMessage"] { background: rgba(255,255,255,0.03) !important; border-radius: 12px; margin: 4px 0; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ═══════════════════════════════════════════════════════════════════════════════
def init_session():
    defaults = {
        "page": "login",  # login | chat | profile
        "logged_in": False,
        "customer": None,  # Full CRM profile dict
        "phone": None,
        # Registration Agent state
        "reg_state": {
            "messages": [], "phone": None, "otp_sent": False,
            "otp_verified": False, "customer_profile": None
        },
        # Chat pipeline state
        "chat_history": [],
        "pipeline_phase": "sales",  # sales | kyc_collection | registration | document | processing | complete
        "loan_terms": {},
        "documents": {},
        "kyc_status": None,
        "fraud_score": -1,
        "decision": None,
        "dti_ratio": 0,
        "sanction_pdf": "",
        "chat_session_id": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ═══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🏦 FinServe NBFC")
        st.caption("AI-Powered Loan Platform")
        st.divider()

        if st.session_state.logged_in and st.session_state.customer:
            c = st.session_state.customer
            st.markdown(f"👤 **{c.get('name', 'User')}**")
            st.caption(f"📱 {c.get('phone', '')}")
            st.caption(f"📍 {c.get('city', 'N/A')}")
        else:
            st.markdown("👤 **Anonymous User**")

        st.divider()

        if st.button("💬 New Loan Chat", use_container_width=True):
            # Reset chat state for new application
            for k in ["chat_history", "loan_terms", "documents", "kyc_status",
                       "fraud_score", "decision", "dti_ratio", "sanction_pdf", "chat_session_id"]:
                st.session_state[k] = [] if k == "chat_history" else ({} if k in ("loan_terms", "documents") else None)
            st.session_state.pipeline_phase = "sales"
            st.session_state.fraud_score = -1
            st.session_state.page = "chat"
            st.rerun()

        if st.button("👤 My Profile", use_container_width=True):
            st.session_state.page = "profile"
            st.rerun()

        if st.session_state.logged_in and st.session_state.customer:
            # Past chat sessions
            c = st.session_state.customer
            sessions = get_chat_sessions(c.get("phone", ""))
            if sessions:
                st.divider()
                st.markdown("**📂 Past Sessions**")
                for s in sessions[:5]:
                    if st.button(f"📝 {s['session_label']}", key=f"sess_{s['id']}", use_container_width=True):
                        msgs = get_chat_messages(s["id"])
                        st.session_state.chat_history = msgs
                        st.session_state.chat_session_id = s["id"]
                        st.session_state.page = "chat"
                        st.session_state.pipeline_phase = "complete"
                        st.rerun()

            st.divider()
            if st.button("🚪 Logout", use_container_width=True):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()





# ═══════════════════════════════════════════════════════════════════════════════
#  CHAT PAGE (9-Agent Pipeline)
# ═══════════════════════════════════════════════════════════════════════════════
def render_chat():
    customer = st.session_state.customer or {}
    phase = st.session_state.pipeline_phase

    # Pipeline progress indicator
    phases = ["sales", "kyc_collection", "registration", "document", "processing", "complete"]
    phase_labels = ["💬 Advisor", "📋 KYC Details", "🔐 Verify", "📄 Documents", "⚙️ Processing", "✅ Complete"]
    current_idx = phases.index(phase) if phase in phases else 0
    progress = (current_idx + 1) / len(phases)
    st.progress(progress, text=f"Pipeline: {phase_labels[current_idx]}")

    # Show limit state if principal is defined
    principal = st.session_state.loan_terms.get("principal", 0)
    limit = customer.get("pre_approved_limit", 0)
    if st.session_state.logged_in and principal > 0 and limit > 0:
        ratio = principal / limit
        if ratio <= 1:
            st.success(f"🟩 Safe Limit [Requested: ₹{principal:,.0f} | Pre-approved: ₹{limit:,.0f}]")
        elif ratio <= 2:
            st.warning(f"🟨 Extended Review [Requested: ₹{principal:,.0f} | Pre-approved: ₹{limit:,.0f}]")
        else:
            st.error(f"🟥 High Risk [Requested: ₹{principal:,.0f} | Pre-approved: ₹{limit:,.0f}]")

    # Render chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"], avatar="🏦" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    # ── SALES / ADVISOR PHASE ─────────────────────────────────────────────────
    if phase == "sales":
        # Show doc query uploader during sales
        with st.expander("📎 Check if a document is valid for your loan", expanded=False):
            doc_check = st.file_uploader("Upload document to verify", type=["jpg", "png", "jpeg", "pdf"], key="sales_doc_check")
            if doc_check and st.button("🔍 Validate Document", key="doc_validate_btn"):
                os.makedirs("data/uploads", exist_ok=True)
                save_path = os.path.join("data", "uploads", f"check_{doc_check.name}")
                with open(save_path, "wb") as f:
                    f.write(doc_check.getbuffer())
                with st.spinner("Analyzing document..."):
                    dq_result = document_query_agent_node({
                        "doc_path": save_path,
                        "loan_principal": st.session_state.loan_terms.get("principal", 0),
                        "pre_approved_limit": customer.get("pre_approved_limit", 100000)
                    })
                    dq_msg = dq_result["messages"][0].content
                    st.session_state.chat_history.append({"role": "assistant", "content": dq_msg})
                    st.rerun()

        if user_input := st.chat_input("Hi! Ask me anything about your finances or loans...", key="sales_input"):
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            lower_input = user_input.strip().lower()

            # Greeting bypass (zero LLM cost)
            generic = {
                "hi": None, "hello": None, "hey": None
            }
            if lower_input in generic and not st.session_state.logged_in:
                reply = "Welcome to FinServe NBFC! 👋 How can I help you today? Feel free to ask about loans, investments, or your finances."
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

            # Keyword-based apply intent — no LLM call
            if detect_apply_intent(lower_input) and st.session_state.loan_terms.get("principal"):
                transition_msg = (
                    "Great! Let's get your loan application started. 🚀\n\n"
                    "I'll now take a few KYC details to confirm your identity before we proceed."
                )
                st.session_state.chat_history.append({"role": "assistant", "content": transition_msg})
                st.session_state.pipeline_phase = "kyc_collection"
                st.rerun()

            with st.chat_message("assistant", avatar="🏦"):
                with st.spinner("Advisor thinking..."):
                    try:
                        hist = [m for m in st.session_state.chat_history[:-1]]

                        # Build past loan history context only if logged in
                        loan_hist_str = ""
                        if st.session_state.logged_in and customer:
                            past_loans = get_loan_history(customer.get("phone", ""))
                            if past_loans:
                                loan_hist_str = "\n## Customer's Past Loan History (for reference)\n"
                                for pl in past_loans[:3]:
                                    loan_hist_str += f"- {pl['created_at']}: {pl['loan_type']} ₹{pl['principal']} → {pl['decision'].upper()}\n"
                                    if pl["decision"] == "reject":
                                        loan_hist_str += f"  Rejection reasons: {pl['rejection_reasons']}\n"

                        # Pass customer profile to advisor-mode Sales Agent
                        res = sales_chat_response(
                            user_message=user_input,
                            chat_history=hist,
                            extra_context=loan_hist_str,
                            customer=customer if st.session_state.logged_in else None
                        )
                        reply = res["reply"]
                        st.markdown(reply)
                        st.session_state.chat_history.append({"role": "assistant", "content": reply})

                        if res.get("extracted") and res["extracted"].get("confirmed"):
                            ext = res["extracted"]
                            st.session_state.loan_terms = {
                                "principal": float(ext.get("loan_amount", 0)),
                                "rate": float(ext.get("interest_rate", 12)),
                                "tenure": int(ext.get("tenure", 12)),
                                "loan_type": ext.get("loan_type", "personal")
                            }
                            emi_result = emi_agent_node({"loan_terms": st.session_state.loan_terms})
                            st.session_state.loan_terms = emi_result["loan_terms"]
                            emi_msg = emi_result["messages"][0].content
                            st.markdown(emi_msg)
                            st.session_state.chat_history.append({"role": "assistant", "content": emi_msg})

                            confirm_prompt = (
                                "\n\n✅ Loan terms confirmed! Would you like to **proceed with the application**? "
                                "Just say *yes* or *apply* and I'll take your KYC details."
                            )
                            st.session_state.chat_history.append({"role": "assistant", "content": confirm_prompt})

                    except Exception as e:
                        print(f"❌ SALES AGENT ERROR: {str(e)}")
                        err_msg = f"⚠️ Service is momentarily busy. Please try again. (Error: {str(e)[:50]}...)"
                        st.markdown(err_msg)
                        st.session_state.chat_history.append({"role": "assistant", "content": err_msg})

                    if st.session_state.chat_session_id:
                        update_chat_session(st.session_state.chat_session_id, st.session_state.chat_history)
            st.rerun()

    # ── KYC COLLECTION PHASE (always collect fresh) ───────────────────────────
    elif phase == "kyc_collection":
        if not st.session_state.get("kyc_intro_sent"):
            st.session_state.kyc_intro_sent = True
            st.session_state.kyc_data = {
                "name": None, "employment": None, "income": None, "pan": None, "bank": None
            }
            intro_msg = (
                "📋 **KYC Verification**\n\n"
                "Before we submit the application, we need to re-confirm your details. "
                "What is your **Full Name** as it appears on your government ID?"
            )
            st.session_state.chat_history.append({"role": "assistant", "content": intro_msg})
            st.rerun()

        if user_input := st.chat_input("Enter your KYC details...", key="kyc_input"):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            kd = st.session_state.kyc_data
            reply = ""

            if not kd["name"]:
                kd["name"] = user_input
                reply = f"Thank you, **{kd['name']}**. What is your **Employment Type**? (e.g., Salaried, Self-Employed, Business Owner)"
            elif not kd["employment"]:
                kd["employment"] = user_input
                reply = "Got it! What is your current **Monthly Income**? (numbers only, e.g. 50000)"
            elif not kd["income"]:
                kd["income"] = user_input
                reply = "Noted. Now please provide your **PAN Number**."
            elif not kd["pan"]:
                kd["pan"] = user_input
                reply = "Almost there! Which **Bank** do you hold your salary account with? (e.g., SBI, HDFC, ICICI)"
            elif not kd["bank"]:
                kd["bank"] = user_input
                reply = (
                    "✅ KYC details collected! \n\n"
                    "🔐 For final loan confirmation, please enter your **registered mobile number** "
                    "— we'll send a verification OTP to authorise this application."
                )
                st.session_state.pipeline_phase = "registration"  # go to OTP confirmation
                st.session_state.reg_intro_sent = False  # reset so registration re-initialises

            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            if st.session_state.chat_session_id:
                update_chat_session(st.session_state.chat_session_id, st.session_state.chat_history)
            st.rerun()
            
    # ── REGISTRATION / OTP CONFIRMATION PHASE ────────────────────────────────
    elif phase == "registration":
        # State for OTP-based final loan authorization
        if not st.session_state.get("reg_intro_sent"):
            st.session_state.reg_intro_sent = True
            st.session_state.reg_data = {"phone": None, "otp_sent": False, "otp_verified": False}
            # Don't push a new message — KYC already pushed the mobile number prompt

        if user_input := st.chat_input("Enter phone number or OTP...", key="reg_input"):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            rd = st.session_state.reg_data
            reply = ""

            clean = "".join(filter(str.isdigit, user_input))

            if not rd["otp_sent"] and len(clean) == 10:
                from mock_apis.otp_service import send_otp
                from agents.registration import normalize_phone
                phone = normalize_phone(clean)
                res = send_otp(phone)
                rd["phone"] = phone
                rd["otp_sent"] = res["sent"]
                otp_display = f" (Dev OTP: {res.get('otp', 'N/A')})" if res["sent"] else ""
                reply = f"📱 {res['message']}{otp_display}\n\nPlease enter the 6-digit OTP to authorise your loan."

            elif rd["otp_sent"] and not rd["otp_verified"] and len(clean) == 6:
                from mock_apis.otp_service import verify_otp
                res = verify_otp(rd["phone"], clean)
                if res["verified"]:
                    rd["otp_verified"] = True
                    # Try to load/update customer by phone
                    db = pull_customer_from_db(rd["phone"])
                    if db and not st.session_state.logged_in:
                        st.session_state.customer = db
                        st.session_state.logged_in = True
                    st.session_state.phone = rd["phone"]

                    # Save session now that we have phone
                    if not st.session_state.chat_session_id:
                        sid = save_chat_session(rd["phone"], "Loan Application Chat", st.session_state.chat_history)
                        st.session_state.chat_session_id = sid

                    limit = (st.session_state.customer or {}).get("pre_approved_limit", 0)
                    principal = st.session_state.loan_terms.get("principal", 0)
                    doc_msg = "\n\n"
                    if limit > 0 and principal <= limit:
                        doc_msg += "✅ Your loan is within pre-approved limits — basic KYC docs required. Please upload your **PAN Card** or **Aadhaar Card**."
                    elif limit > 0 and principal <= 2 * limit:
                        doc_msg += "📄 Extended review required. Please upload your **Salary Slip**."
                    else:
                        doc_msg += "📄 Please upload your **identity and income documents** to proceed."

                    reply = f"✅ **Loan Authorised!** OTP verified successfully.{doc_msg}"
                    st.session_state.pipeline_phase = "document"

                else:
                    reply = f"❌ {res['message']} Please try again."

            elif not rd["otp_sent"]:
                reply = "⚠️ Please enter your valid **10-digit mobile number** first."
            else:
                reply = "⚠️ Please enter the **6-digit OTP** sent to your phone."

            if reply:
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
            if st.session_state.chat_session_id:
                update_chat_session(st.session_state.chat_session_id, st.session_state.chat_history)
            st.rerun()

    # ── DOCUMENT UPLOAD PHASE ────────────────────────────────────────────────
    elif phase == "document":
        uploaded = st.file_uploader("📎 Upload Document (PAN / Aadhaar / Salary Slip)", type=["jpg", "png", "jpeg", "pdf"])

        if uploaded and st.button("🔍 Submit for AI Verification", type="primary", use_container_width=True):
            # Save to data/uploads
            os.makedirs("data/uploads", exist_ok=True)
            save_path = os.path.join("data", "uploads", uploaded.name)
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())

            st.session_state.chat_history.append({"role": "user", "content": f"📎 Uploaded: {uploaded.name}"})
            st.session_state.pipeline_phase = "processing"

            with st.spinner("🤖 Running 4-Agent verification pipeline..."):
                # 1. Document Agent (Gemini Vision OCR)
                doc_state = {"documents": {"salary_slip_path": save_path}}
                doc_result = document_agent_node(doc_state)
                st.session_state.documents = doc_result.get("documents", {})
                doc_msg = doc_result["messages"][0].content
                st.session_state.chat_history.append({"role": "assistant", "content": doc_msg})

                # Save document to DB audit trail
                docs = st.session_state.documents
                save_document_record(
                    st.session_state.phone or "", docs.get("document_type", ""),
                    uploaded.name, docs.get("audit_path", ""),
                    docs.get("name_extracted", ""), docs.get("salary_extracted", 0),
                    docs.get("confidence", 0), docs.get("tampered", False)
                )

                # 2. KYC Verification Agent
                kyc_state = {"customer_data": customer, "documents": st.session_state.documents}
                kyc_result = verification_agent_node(kyc_state)
                st.session_state.kyc_status = kyc_result.get("kyc_status")
                kyc_msg = kyc_result["messages"][0].content
                st.session_state.chat_history.append({"role": "assistant", "content": kyc_msg})

                # 3. Fraud Detection Agent
                fraud_state = {
                    "customer_data": customer,
                    "documents": st.session_state.documents,
                    "loan_terms": st.session_state.loan_terms
                }
                fraud_result = fraud_agent_node(fraud_state)
                st.session_state.fraud_score = fraud_result.get("fraud_score", 0)
                fraud_msg = fraud_result["messages"][0].content
                st.session_state.chat_history.append({"role": "assistant", "content": fraud_msg})

                # 4. Underwriting Agent
                uw_state = {
                    "customer_data": customer,
                    "loan_terms": st.session_state.loan_terms,
                    "documents": st.session_state.documents,
                    "fraud_score": st.session_state.fraud_score
                }
                uw_result = underwriting_agent_node(uw_state)
                st.session_state.decision = uw_result.get("decision")
                st.session_state.dti_ratio = uw_result.get("dti_ratio", 0)
                st.session_state.reasons = uw_result.get("reasons", [])
                uw_msg = uw_result["messages"][0].content
                st.session_state.chat_history.append({"role": "assistant", "content": uw_msg})

                # 5. Generate PDFs based on Decision
                if st.session_state.decision == "approve":
                    san_state = {
                        "customer_id": customer.get("id", "NEW"),
                        "customer_data": customer,
                        "loan_terms": st.session_state.loan_terms,
                        "dti_ratio": st.session_state.dti_ratio
                    }
                    san_result = sanction_agent_node(san_state)
                    st.session_state.sanction_pdf = san_result.get("sanction_pdf", "")
                    san_msg = san_result["messages"][0].content
                    st.session_state.chat_history.append({"role": "assistant", "content": san_msg})
                elif st.session_state.decision == "reject":
                    from utils.pdf_generator import generate_rejection_letter
                    pdf_path = generate_rejection_letter(
                        customer, st.session_state.loan_terms, st.session_state.reasons, customer.get("id", "NEW")
                    )
                    st.session_state.sanction_pdf = pdf_path
                    rej_msg = f"📜 **Rejection Letter Generated**\nFile: `{pdf_path}`\nYou can download it below."
                    st.session_state.chat_history.append({"role": "assistant", "content": rej_msg})

                    # Cross-Selling logic
                    limit = customer.get("pre_approved_limit", 0)
                    if limit > 0 and st.session_state.loan_terms.get("principal", 0) > limit:
                        cross_msg = (
                            f"💡 **Alternative Offer:** While we couldn't approve ₹{st.session_state.loan_terms.get('principal'):,}, "
                            f"you do have a pre-approved limit of **₹{limit:,}**.\n"
                            f"Would you like to apply for a smaller loan within this limit?"
                        )
                        st.session_state.chat_history.append({"role": "assistant", "content": cross_msg})

                # 6. Advisor Agent (always runs — tips for both outcomes)
                adv_state = {
                    "customer_data": customer,
                    "loan_terms": st.session_state.loan_terms,
                    "decision": st.session_state.decision,
                    "dti_ratio": st.session_state.dti_ratio,
                    "fraud_score": st.session_state.fraud_score
                }
                try:
                    adv_result = advisor_agent_node(adv_state)
                    adv_msg = adv_result["messages"][0].content
                    st.session_state.chat_history.append({"role": "assistant", "content": adv_msg})
                except Exception:
                    pass

                # Save loan application to DB
                save_loan_application(
                    phone=st.session_state.phone or "",
                    name=customer.get("name", "User"),
                    terms=st.session_state.loan_terms,
                    decision=st.session_state.decision or "unknown",
                    dti=st.session_state.dti_ratio,
                    score=customer.get("credit_score", 0),
                    fraud=st.session_state.fraud_score,
                    reasons=st.session_state.reasons,
                    pdf=st.session_state.sanction_pdf
                )

                st.session_state.pipeline_phase = "complete"

                # Persist chat
                if st.session_state.chat_session_id:
                    update_chat_session(st.session_state.chat_session_id, st.session_state.chat_history)

            st.rerun()

    # ── COMPLETE PHASE ───────────────────────────────────────────────────────
    elif phase in ("complete", "processing"):
        # Show download buttons if approved
        if st.session_state.sanction_pdf and os.path.exists(st.session_state.sanction_pdf):
            with open(st.session_state.sanction_pdf, "rb") as f:
                label = "Sanction" if st.session_state.decision == "approve" else "Decision"
                name = "Sanction_Letter.pdf" if st.session_state.decision == "approve" else "Rejection_Letter.pdf"
                st.download_button(
                    f"📥 Download {label} Letter PDF",
                    data=f, file_name=name,
                    type="primary", use_container_width=True
                )

        st.info("💬 Pipeline complete! Use the sidebar to start a new loan application or view your profile.")


# ═══════════════════════════════════════════════════════════════════════════════
#  PROFILE PAGE
# ═══════════════════════════════════════════════════════════════════════════════
def render_profile():
    if not st.session_state.logged_in:
        st.markdown("# 👤 Login to View Profile")
        st.info("Please enter your FinServe email and password to access your profile and past chats.")
        st.divider()

        # Persistent mini-auth state
        if "profile_email" not in st.session_state:
            st.session_state.profile_email = None

        for msg in st.session_state.reg_state.get("messages", []):
            role = "assistant" if isinstance(msg, AIMessage) else "user"
            with st.chat_message(role, avatar="🏦" if role == "assistant" else "👤"):
                st.markdown(msg.content)

        if not st.session_state.reg_state["messages"]:
            st.session_state.reg_state["messages"].append(
                AIMessage(content="Welcome! Please enter your **Email Address** to continue.")
            )
            st.rerun()

        if user_input := st.chat_input("Enter your email or password...", key="profile_login"):
            st.session_state.reg_state["messages"].append(HumanMessage(content=user_input))

            with st.spinner("🔐 Verifying..."):
                if not st.session_state.profile_email:
                    # First input is email
                    st.session_state.profile_email = user_input.strip()
                    st.session_state.reg_state["messages"].append(
                        AIMessage(content="Got it! Now please enter your **Password**.")
                    )
                else:
                    # Second input is password
                    matched = pull_customer_by_email(st.session_state.profile_email, user_input.strip())
                    if matched:
                        st.session_state.customer = matched
                        st.session_state.logged_in = True
                        st.session_state.phone = matched.get("phone", "")
                        st.rerun()
                    else:
                        # Reset and let them try again
                        st.session_state.profile_email = None
                        st.session_state.reg_state["messages"].append(
                            AIMessage(content="❌ Email or password is incorrect. Please try again with your **Email Address**.")
                        )
            st.rerun()
        return

    customer = st.session_state.customer or {}
    phone = st.session_state.phone or ""

    st.markdown("# 👤 My Profile")

    # Profile Card
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Name", customer.get("name", "N/A"))
    col2.metric("Credit Score", customer.get("credit_score", "N/A"))
    col3.metric("Pre-approved", f"₹{customer.get('pre_approved_limit', 0):,}")
    col4.metric("Monthly Salary", f"₹{customer.get('salary', 0):,}")

    st.divider()

    # Loan History
    st.markdown("## 📋 Loan Application History")
    loans = get_loan_history(phone)

    if not loans:
        st.info("No loan applications yet. Start a new chat to apply!")
    else:
        for loan in loans:
            decision = loan.get("decision", "pending")
            if decision == "approve":
                icon, color_cls = "✅", "status-approved"
            elif decision == "reject":
                icon, color_cls = "❌", "status-rejected"
            else:
                icon, color_cls = "⏳", "status-pending"

            with st.expander(f"{icon} {loan.get('loan_type', 'Personal').title()} Loan — ₹{loan.get('principal', 0):,.0f} | {loan.get('created_at', '')}"):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Amount", f"₹{loan.get('principal', 0):,.0f}")
                c2.metric("EMI", f"₹{loan.get('emi', 0):,.2f}")
                c3.metric("Tenure", f"{loan.get('tenure', 0)} months")
                c4.metric("Rate", f"{loan.get('rate', 0)}%")

                c5, c6, c7, c8 = st.columns(4)
                c5.metric("Decision", decision.upper())
                c6.metric("Credit Score", loan.get("credit_score", "N/A"))
                c7.metric("DTI Ratio", f"{loan.get('dti_ratio', 0)*100:.1f}%")
                c8.metric("Fraud Score", f"{loan.get('fraud_score', 0):.2f}")

                # Download sanction letter
                pdf_path = loan.get("sanction_pdf", "")
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            f"📥 Download {'Sanction' if decision == 'approve' else 'Decision'} Letter",
                            data=f, file_name=os.path.basename(pdf_path),
                            key=f"dl_{loan['id']}", use_container_width=True
                        )

                if decision == "reject":
                    reasons = json.loads(loan.get("rejection_reasons", "[]"))
                    if reasons:
                        st.error("**Rejection Reasons:**\n" + "\n".join(f"• {r}" for r in reasons))

    st.divider()

    # Document Upload History
    st.markdown("## 📄 Document Upload History")
    docs = get_document_history(phone)
    if not docs:
        st.info("No documents uploaded yet.")
    else:
        for d in docs:
            tamper_badge = " 🚨 TAMPERED" if d.get("tampered") else " ✅"
            with st.expander(f"📄 {d.get('doc_type', 'Unknown')} — {d.get('uploaded_at', '')}{tamper_badge}"):
                st.write(f"**File:** {d.get('original_filename', 'N/A')}")
                st.write(f"**Name Extracted:** {d.get('name_extracted', 'N/A')}")
                st.write(f"**Salary Extracted:** ₹{d.get('salary_extracted', 0):,.0f}")
                st.write(f"**OCR Confidence:** {d.get('confidence', 0):.0%}")


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGIN / REGISTER PAGE
# ═══════════════════════════════════════════════════════════════════════════════
def render_login():
    """Full-page email + password login / registration screen."""
    st.markdown("""
    <style>
    .login-card {
        max-width: 480px; margin: 60px auto; padding: 40px;
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
        border-radius: 20px; box-shadow: 0 8px 40px rgba(0,0,0,0.4);
        border: 1px solid rgba(255,255,255,0.08);
    }
    .login-title { color: #f0f6ff; font-size: 2rem; font-weight: 700; margin-bottom: 4px; }
    .login-sub { color: #94a3b8; font-size: 0.95rem; margin-bottom: 28px; }
    </style>
    <div class="login-card">
        <div class="login-title">🏦 FinServe NBFC</div>
        <div class="login-sub">India's Smartest Loan Platform — powered by 9 AI Agents</div>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔑 Login", "✍️ New Customer? Register"])

    with tab_login:
        st.markdown("### Welcome Back")
        st.caption("Enter your registered email and password to access your profile and apply for loans.")

        email_in = st.text_input("📧 Email Address", placeholder="you@example.com", key="login_email")
        pass_in  = st.text_input("🔒 Password", type="password", placeholder="Your password", key="login_pass")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Login →", use_container_width=True, type="primary"):
                if not email_in or not pass_in:
                    st.error("Please enter both email and password.")
                else:
                    matched = pull_customer_by_email(email_in.strip(), pass_in.strip())
                    if matched:
                        st.session_state.logged_in = True
                        st.session_state.customer = matched
                        st.session_state.phone = matched.get("phone", "")
                        st.session_state.page = "chat"
                        st.success(f"✅ Welcome back, {matched['name']}! Loading your dashboard...")
                        st.rerun()
                    else:
                        st.error("❌ Email or password is incorrect. Please try again.")
        with col2:
            if st.button("Continue as Guest →", use_container_width=True):
                st.session_state.page = "chat"
                st.rerun()

        st.markdown("---")
        st.caption(
            "**Test Accounts** (for demo):\n"
            "`sarang@example.com` / `sarang123`  |  "
            "`priya@example.com` / `priya123`  |  "
            "`raj@example.com` / `raj123`"
        )

    with tab_register:
        st.markdown("### New to FinServe? Create Your Account")
        st.caption("Register to get a pre-approved loan limit, track your applications, and access your full profile.")

        r_name  = st.text_input("👤 Full Name (as on ID)", placeholder="Sarang Gajanan Rao", key="reg_name")
        r_email = st.text_input("📧 Email Address", placeholder="you@example.com", key="reg_email")
        r_phone = st.text_input("📱 Mobile Number", placeholder="9876543210", max_chars=10, key="reg_phone")
        r_pass  = st.text_input("🔒 Create Password", type="password", key="reg_pass")
        r_pass2 = st.text_input("🔒 Confirm Password", type="password", key="reg_pass2")

        if st.button("Create Account →", use_container_width=True, type="primary"):
            if not all([r_name, r_email, r_phone, r_pass, r_pass2]):
                st.error("Please fill in all fields.")
            elif r_pass != r_pass2:
                st.error("Passwords do not match.")
            elif len(r_phone) != 10 or not r_phone.isdigit():
                st.error("Please enter a valid 10-digit mobile number.")
            elif "@" not in r_email:
                st.error("Please enter a valid email address.")
            else:
                # Add to customers.json
                import json as _json
                cust_path = "mock_apis/customers.json"
                try:
                    with open(cust_path, "r") as f:
                        all_customers = _json.load(f)

                    # Check if email already registered
                    existing_emails = [c.get("email", "").lower() for c in all_customers]
                    if r_email.lower() in existing_emails:
                        st.error("This email is already registered. Please log in instead.")
                    else:
                        new_id = f"CUST{len(all_customers)+1:03d}"
                        new_cust = {
                            "id": new_id,
                            "name": r_name.strip(),
                            "phone": r_phone.strip(),
                            "email": r_email.strip().lower(),
                            "password": r_pass,
                            "city": "Unknown",
                            "salary": 0,
                            "credit_score": 700,
                            "pre_approved_limit": 100000,
                            "existing_emi_total": 0,
                            "current_loans": [],
                            "risk_flags": []
                        }
                        all_customers.append(new_cust)
                        with open(cust_path, "w") as f:
                            _json.dump(all_customers, f, indent=4, ensure_ascii=False)

                        st.session_state.logged_in = True
                        st.session_state.customer = new_cust
                        st.session_state.phone = r_phone.strip()
                        st.session_state.page = "chat"
                        st.success(f"✅ Account created! Welcome to FinServe, {r_name.split()[0]}!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Registration failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
render_sidebar()

page = st.session_state.page

if page == "login":
    render_login()
elif page == "chat":
    render_chat()
elif page == "profile":
    render_profile()
