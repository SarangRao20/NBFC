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
from agents.registration import build_registration_agent, RegistrationState, pull_customer_from_db
from agents.sales_agent import sales_chat_response
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
        "pipeline_phase": "sales",  # sales | document | processing | complete
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

            # Past chat sessions
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
        else:
            st.info("Please login to continue.")


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE (Registration Agent)
# ═══════════════════════════════════════════════════════════════════════════════
def render_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# 🏦 FinServe NBFC")
        st.markdown("### Welcome to India's Smartest Loan Platform")
        st.caption("Powered by 9 AI Agents working together")
        st.divider()

        # Show registration chat
        for msg in st.session_state.reg_state.get("messages", []):
            cls = msg.__class__.__name__
            if cls == "SystemMessage":
                continue
            role = "assistant" if cls == "AIMessage" else "user"
            with st.chat_message(role, avatar="🏦" if role == "assistant" else "👤"):
                st.markdown(msg.content)

        # Check if login is complete
        if st.session_state.reg_state.get("otp_verified") and st.session_state.reg_state.get("customer_profile"):
            profile = st.session_state.reg_state["customer_profile"]
            st.session_state.logged_in = True
            st.session_state.customer = profile
            st.session_state.phone = profile.get("phone")

            # Auto-start new chat
            greeting = (
                f"Hello {profile.get('name', '')}! 👋 Welcome to FinServe NBFC.\n\n"
                f"📊 Your Profile: Credit Score **{profile.get('credit_score', 'N/A')}** | "
                f"Pre-approved Limit **₹{profile.get('pre_approved_limit', 0):,}**\n\n"
                f"How can I help you today? Would you like to explore a **Personal Loan**, "
                f"**Home Loan**, **Business Loan**, or **Education Loan**?"
            )
            st.session_state.chat_history = [{"role": "assistant", "content": greeting}]
            st.session_state.page = "chat"
            st.session_state.pipeline_phase = "sales"

            # Create chat session in DB
            sid = save_chat_session(profile.get("phone", ""), "Loan Chat", st.session_state.chat_history)
            st.session_state.chat_session_id = sid
            st.rerun()

        # Chat input for login
        if user_input := st.chat_input("Enter your phone number...", key="login_input"):
            st.session_state.reg_state["messages"].append(HumanMessage(content=user_input))
            with st.spinner("🔐 Processing..."):
                try:
                    agent = build_registration_agent()
                    new_state = agent.invoke(st.session_state.reg_state)
                    st.session_state.reg_state = new_state
                except Exception as e:
                    print(f"❌ LOGIN AGENT ERROR: {str(e)}")
                    st.session_state.reg_state["messages"].append(
                        AIMessage(content=f"⚠️ Service busy. Please wait a moment and try again. (Technical: {str(e)[:50]})")
                    )
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  CHAT PAGE (9-Agent Pipeline)
# ═══════════════════════════════════════════════════════════════════════════════
def render_chat():
    customer = st.session_state.customer or {}
    phase = st.session_state.pipeline_phase

    # Pipeline progress indicator
    phases = ["sales", "document", "processing", "complete"]
    phase_labels = ["💬 Sales", "📄 Documents", "⚙️ Processing", "✅ Complete"]
    current_idx = phases.index(phase) if phase in phases else 0
    progress = (current_idx + 1) / len(phases)
    st.progress(progress, text=f"Pipeline: {phase_labels[current_idx]}")

    # Render chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"], avatar="🏦" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    # ── SALES PHASE ──────────────────────────────────────────────────────────
    if phase == "sales":
        if user_input := st.chat_input("Tell me about the loan you need...", key="sales_input"):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user", avatar="👤"):
                st.markdown(user_input)

            with st.chat_message("assistant", avatar="🏦"):
                with st.spinner("Sales Agent thinking..."):
                    try:
                        hist = [m for m in st.session_state.chat_history[:-1]]
                        res = sales_chat_response(user_input, hist)
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

                            # Auto-run EMI agent
                            emi_result = emi_agent_node({"loan_terms": st.session_state.loan_terms})
                            st.session_state.loan_terms = emi_result["loan_terms"]
                            emi_msg = emi_result["messages"][0].content
                            st.markdown(emi_msg)
                            st.session_state.chat_history.append({"role": "assistant", "content": emi_msg})

                            # Check pre-approved limit logic
                            limit = customer.get("pre_approved_limit", 0)
                            principal = st.session_state.loan_terms["principal"]

                            if principal <= limit:
                                doc_msg = "✅ Your loan amount is within pre-approved limits! Basic KYC docs are sufficient.\n\n📄 Please upload your **PAN Card** or **Aadhaar Card** image below."
                            elif principal <= 2 * limit:
                                doc_msg = "📄 Your loan exceeds your pre-approved limit. We'll need **extended verification**.\n\nPlease upload your **Salary Slip** for income verification."
                            else:
                                # > 2x limit — will be rejected at underwriting, but let them proceed
                                doc_msg = "📄 Please upload your **identity document** (PAN/Aadhaar) to proceed with verification."

                            st.markdown(doc_msg)
                            st.session_state.chat_history.append({"role": "assistant", "content": doc_msg})
                            st.session_state.pipeline_phase = "document"

                    except Exception as e:
                        print(f"❌ SALES AGENT ERROR: {str(e)}")
                        err_msg = f"⚠️ Service is momentarily busy. Please wait a few seconds and try again. (Technical: {str(e)[:50]}...)"
                        st.markdown(err_msg)
                        st.session_state.chat_history.append({"role": "assistant", "content": err_msg})

                    # Persist chat
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
                uw_msg = uw_result["messages"][0].content
                st.session_state.chat_history.append({"role": "assistant", "content": uw_msg})

                # 5. If approved → Sanction PDF
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
                    reasons=[],
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
                st.download_button(
                    "📥 Download Sanction Letter PDF",
                    data=f, file_name="Sanction_Letter.pdf",
                    type="primary", use_container_width=True
                )

        st.info("💬 Pipeline complete! Use the sidebar to start a new loan application or view your profile.")


# ═══════════════════════════════════════════════════════════════════════════════
#  PROFILE PAGE
# ═══════════════════════════════════════════════════════════════════════════════
def render_profile():
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
#  MAIN ROUTER
# ═══════════════════════════════════════════════════════════════════════════════
render_sidebar()

page = st.session_state.page

if page == "login":
    render_login()
elif page == "chat":
    if not st.session_state.logged_in:
        st.session_state.page = "login"
        st.rerun()
    render_chat()
elif page == "profile":
    if not st.session_state.logged_in:
        st.session_state.page = "login"
        st.rerun()
    render_profile()
