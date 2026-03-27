"""Sanction Letter Generator Agent — produces a professional PDF sanction letter."""

import os, sys, datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage
from agents.session_manager import SessionManager

# Ensure output directories exist
os.makedirs("data/sanctions", exist_ok=True)


async def sanction_agent_node(state: dict):
    """
    Generates a formal Sanction Letter PDF string based on confirmed loan details.
    Includes Address Gathering and E-sign workflow.
    """
    session_id = state.get("session_id", "default")
    customer = state.get("customer_data", {}) or {}
    terms = state.get("loan_terms", {}) or {}
    decision = state.get("decision", "approve")
    
    # ✅ NEW: Retrieve selected lender information (Phase 5 integration)
    selected_lender_id = state.get("selected_lender_id")
    selected_lender_name = state.get("selected_lender_name")
    selected_rate = state.get("selected_interest_rate")
    
    print(f"📜 [SANCTION AGENT] Processing for lender: {selected_lender_name or 'N/A'}")

    # 1. ADDRESS GATHERING (If approved but no address)
    if decision == "approve" and not customer.get("address"):
        print("📜 [SANCTION] Missing address. Requesting from user...")
        return {
            "messages": [AIMessage(content=(
                "🎊 **Just one last thing before I release your funds!**\n\n"
                "To finalize the legal agreement, I'll need your **current residential address**. "
                "Please type it out below, and I'll generate your official Sanction Letter instantly."
            ))],
            "current_phase": "sanction_address",
            "options": ["Skip for now", "Talk to Arjun"]
        }

    # 2. CAPTURE ADDRESS FROM LAST MESSAGE (If in sanction_address phase)
    if state.get("current_phase") == "sanction_address" and not customer.get("address"):
        last_msg = ""
        for m in reversed(state.get("messages", [])):
            from langchain_core.messages import HumanMessage
            if isinstance(m, HumanMessage):
                last_msg = m.content
                break
        
        if last_msg and len(last_msg) > 5:
            customer["address"] = last_msg
            print(f"🏠 [SANCTION] Captured address: {last_msg}")
        else:
             return {
                "messages": [AIMessage(content="I need a valid address to prepare your legal documents. Could you please provide your full residential address?")],
                "current_phase": "sanction_address"
             }

    print("📜 [SANCTION AGENT] Generating final sanction letter...")
    
    log = list(state.get("action_log") or [])
    log.append(f"📜 Drafting legally-compliant Sanction Letter for {selected_lender_name or 'approved lender'}...")

    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    
    principal = terms.get("principal", 0)
    # ✅ Use selected rate if available, otherwise fall back to terms rate
    rate = selected_rate if selected_rate else terms.get("rate", 0.10)
    tenure = terms.get("tenure", 12)
    emi = terms.get("emi", 0)
    cust_name = customer.get("name", "Applicant")
    cust_phone = customer.get("phone", "N/A")
    cust_id = state.get("customer_id", "UNKNOWN")
    cust_addr = customer.get("address", "Not provided")

    is_approved = decision != "hard_reject" and decision != "reject"
    status_text = "Approved" if is_approved else "Rejected"
    letter_label = "Sanction" if is_approved else "Rejection"
    
    log.append(f"✍️ Drafting {letter_label} Letter for {cust_name}...")

    filename = f"{cust_phone}_{letter_label}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join("data", "sanctions", filename)

    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.pagesizes import letter

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        reg_details = state.get("selected_lender_reg_details", {}) or {}
        lender_cin = reg_details.get("cin", "L65910PN2007PLC130076")
        lender_office = reg_details.get("office", "FinServe complex, Mumbai-Pune Road, Pune - 411035")
        lender_web = reg_details.get("web", "www.finserve-nbfc.com")

        # Header
        elements.append(Paragraph(f"<b>{selected_lender_name or 'FinServe NBFC Ltd.'}</b>", styles["Title"]))
        elements.append(Paragraph(f"<font size=8>CIN: {lender_cin} | Registered Office: {lender_office}</font>", styles["Normal"]))
        elements.append(Paragraph(f"<font size=8>Website: {lender_web}</font>", styles["Normal"]))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>{letter_label.upper()} LETTER</b>", styles["Heading2"]))
        elements.append(Paragraph(f"Date: {current_date}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        # Applicant Table
        app_data = [
            ["Lender", selected_lender_name or "FinServe NBFC Ltd."],
            ["Applicant Name", cust_name],
            ["Communication Addr", Paragraph(cust_addr, styles["Normal"])],
            ["Registered Phone", cust_phone],
            ["Application Status", status_text],
        ]
        table = Table(app_data, colWidths=[120, 330])
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        # Loan Table
        if is_approved:
            loan_data = [
                ["Amount", f"INR {principal:,.0f}"],
                ["Rate", f"{rate*100 if rate < 1 else rate}% p.a."],
                ["Tenure", f"{tenure} mos"],
                ["EMI", f"INR {emi:,.2f}"],
            ]
            loan_table = Table(loan_data, colWidths=[120, 330])
            loan_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0,0), (0,-1), colors.whitesmoke)]))
            elements.append(loan_table)
        
        doc.build(elements)
        log.append(f"✅ Generated PDF: {filename}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        filepath = filepath.replace(".pdf", ".txt")
        with open(filepath, "w") as f: f.write(f"Sanction Letter\nName: {cust_name}\nAmount: {principal}")

    if is_approved:
        msg = (f"📜 **Your Sanction Letter is Ready!**\n\n"
               f"I've generated your official agreement (ID: {filename}).\n\n"
               f"**Lender**: {selected_lender_name or 'FinServe NBFC'}\n"
               f"**Rate**: {rate:.1f}% p.a.\n"
               f"**Amount**: ₹{principal:,}\n\n"
               f"**NEXT STEP**: Please click the button below to **E-sign** and authorize the disbursement of ₹{principal:,} to your linked account.")
        options = ["✍️ E-sign & Disburse", "📄 View Letter", "Talk to Arjun"]
        phase = "sanction_esign"
    else:
        msg = (f"📜 **Rejection Letter Generated**\n\n"
               f"I've generated a formal letter (ID: {filename}) explaining our decision.\n\n"
               f"**Lender**: {selected_lender_name or 'FinServe NBFC'}\n"
               f"**Status**: Not Approved\n\n"
               f"You can view the letter below. I recommend reviewing the suggestions to improve your eligibility for future applications.")
        options = ["📄 View Letter", "Talk to Arjun"]
        phase = "loan_rejected"
    
    updates = {
        "sanction_pdf": filepath, 
        "selected_lender_id": selected_lender_id,  # ✅ Persist lender info
        "selected_lender_name": selected_lender_name,  # ✅ Persist lender info
        "selected_interest_rate": selected_rate,  # ✅ Persist lender info
        "messages": [AIMessage(content=msg)],
        "action_log": log,
        "options": options,
        "current_phase": phase,
        "customer_data": customer
    }
    
    # Save to DB
    try:
        await SessionManager.save_document(session_id, "sanction_letter", filepath, {"type": letter_label}, 1.0)
    except: pass
    
    try:
        await SessionManager.save_session(session_id, updates)
    except: pass

    # ── PERSIST LOAN TO loan_applications_collection ──────────────────────────
    try:
        from db.database import loan_applications_collection
        from datetime import timedelta

        disbursed_at = datetime.datetime.utcnow()
        first_emi_day = 5
        if disbursed_at.day > first_emi_day:
            # Next month
            if disbursed_at.month == 12:
                first_emi_due = disbursed_at.replace(year=disbursed_at.year + 1, month=1, day=first_emi_day)
            else:
                first_emi_due = disbursed_at.replace(month=disbursed_at.month + 1, day=first_emi_day)
        else:
            first_emi_due = disbursed_at.replace(day=first_emi_day)

        loan_record = {
            "session_id": session_id,
            "phone": cust_phone,
            "name": cust_name,
            "amount": principal,
            "loan_type": terms.get("loan_type", "Personal"),
            "interest_rate": rate,
            "tenure": tenure,
            "emi": emi,
            "status": "Approved" if is_approved else "Rejected",
            "decision": decision,
            "created_at": disbursed_at.isoformat(),
            "first_emi_due_date": first_emi_due.strftime("%Y-%m-%d"),
            "next_emi_date": first_emi_due.strftime("%Y-%m-%d"),
            "payments_made": 0,
            "remaining_balance": round(principal, 2),
            "pdf_path": filepath,
            # ✅ NEW: Include selected lender information
            "lender_id": selected_lender_id,
            "lender_name": selected_lender_name,
            "lender_rate": selected_rate,
        }
        await loan_applications_collection.insert_one(loan_record)
        print(f"📊 [SANCTION AGENT] Loan persisted: {cust_name} — {'Approved' if is_approved else 'Rejected'} — ₹{principal:,}")

        # Also update the customer's existing_emi_total in mock customers JSON
        if is_approved and emi > 0:
            try:
                from api.services.auth_service import load_mock_customers, save_mock_customers
                customers = load_mock_customers()
                for c in customers:
                    if c.get("phone") == cust_phone:
                        old_emi = c.get("existing_emi_total", 0) or 0
                        c["existing_emi_total"] = old_emi + emi
                        print(f"💰 [SANCTION AGENT] Updated existing_emi_total for {cust_phone}: ₹{old_emi} → ₹{c['existing_emi_total']:.2f}")
                        break
                save_mock_customers(customers)
            except Exception as emi_err:
                print(f"⚠️ [SANCTION AGENT] Failed to update existing_emi_total: {emi_err}")

    except Exception as persist_err:
        print(f"⚠️ [SANCTION AGENT] Failed to persist loan record: {persist_err}")

    return updates
