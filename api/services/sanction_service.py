"""Sanction Service — compile terms + generate PDF (Step 16)."""

import os
from datetime import datetime
from api.core.state_manager import get_session, update_session, advance_phase
from api.config import get_settings
from api.core.redis_cache import get_cache
from api.core.email_service import get_email_service

settings = get_settings()


async def generate_sanction(session_id: str) -> dict:
    """Step 16: Compile Final Terms → Generate Loan PDF → Send to User."""
    cache = await get_cache()
    email_service = await get_email_service()
    # Default to False so email failures don't cause UnboundLocalError later
    email_sent = False

    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    decision = state.get("decision", "")
    reasons = state.get("reasons", [])

    cust_name = customer.get("name", "Customer")
    cust_id = state.get("customer_id", "UNKNOWN")
    principal = terms.get("principal", 0)
    rate = terms.get("rate", 0)
    tenure = terms.get("tenure", 0)
    emi = terms.get("emi", 0)
    dti = state.get("dti_ratio", 0)
    score = customer.get("credit_score", 0)

    # Handle different decision types
    if decision == "approve":
        is_approved = True
        letter_type = "Sanction"
    elif decision in ["reject", "soft_reject"]:
        is_approved = False
        letter_type = "Rejection"
    else:
        # If no decision, default to rejection for safety
        is_approved = False
        letter_type = "Rejection"
        decision = "reject"
        reasons.append("No clear decision recorded in underwriting")
    filename = f"{cust_id}_{letter_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(settings.SANCTION_DIR, filename)

    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.pagesizes import letter as page_letter

        doc = SimpleDocTemplate(filepath, pagesize=page_letter,
                                rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        elements = []

        # Header
        elements.append(Paragraph("<b>FinServe NBFC Ltd.</b>", styles["Title"]))
        elements.append(Paragraph("Registered Office: Financial District, Mumbai", styles["Normal"]))
        elements.append(Paragraph("CIN: U65100MH2024PLC123456", styles["Normal"]))
        elements.append(Spacer(1, 12))

        title = "LOAN SANCTION LETTER" if is_approved else "LOAN REJECTION LETTER"
        elements.append(Paragraph(f"<b>{title}</b>", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %B %Y')}", styles["Normal"]))
        elements.append(Paragraph(
            f"<b>Reference:</b> NBFC/SL/{cust_id}/{datetime.now().strftime('%Y%m%d')}", styles["Normal"]))
        elements.append(Spacer(1, 14))

        # Applicant details
        elements.append(Paragraph("<b>Applicant Details</b>", styles["Heading3"]))
        app_data = [
            ["Name", cust_name],
            ["Customer ID", cust_id],
            ["Credit Score", str(score)],
            ["Status", "Approved" if is_approved else "Rejected"],
        ]
        if not is_approved:
            app_data.append(["Rejection Reasons", "; ".join(reasons)])

        table = Table(app_data, colWidths=[150, 300])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 14))

        # Loan details
        elements.append(Paragraph("<b>Loan Details</b>", styles["Heading3"]))
        loan_data = [
            ["Amount", f"INR {principal:,.2f}"],
            ["Interest Rate", f"{rate}% p.a."],
            ["Tenure", f"{tenure} months"],
            ["EMI", f"INR {emi:,.2f}"],
            ["DTI Ratio", f"{dti*100:.1f}%"],
        ]
        loan_table = Table(loan_data, colWidths=[200, 250])
        loan_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ]))
        elements.append(loan_table)
        elements.append(Spacer(1, 14))

        # Footer
        if is_approved:
            elements.append(Paragraph(
                "Congratulations! Your loan has been approved. Complete documentation within 30 days.",
                styles["Normal"]))
        else:
            elements.append(Paragraph(
                "Thank you for applying. Please address the concerns above and reapply when ready.",
                styles["Normal"]))

        elements.append(Spacer(1, 20))
        elements.append(Paragraph("This is a system-generated letter.", styles["Italic"]))
        elements.append(Paragraph("<b>For FinServe NBFC Ltd.</b>", styles["Normal"]))

        # Terms page
        elements.append(PageBreak())
        elements.append(Paragraph("<b>Terms & Conditions</b>", styles["Heading3"]))
        terms_text = (
            "1. Sanction valid for 30 days from issue. <br/>"
            "2. Disbursement subject to documentation. <br/>"
            "3. Late payment: 2% per month penal interest. <br/>"
            "4. Prepayment permitted after 6 months. <br/>"
            "5. Terms subject to regulatory guidelines. <br/>"
        )
        elements.append(Paragraph(terms_text, styles["Normal"]))

        doc.build(elements)

    except ImportError:
        # Fallback: plain text
        filepath = filepath.replace(".pdf", ".txt")
        with open(filepath, "w") as f:
            f.write(f"{letter_type.upper()} LETTER — {cust_name}\n"
                    f"Status: {'Approved' if is_approved else 'Rejected'}\n"
                    f"Amount: {principal}\nEMI: {emi}\n")

    await update_session(session_id, {"sanction_pdf": filepath})
    await advance_phase(session_id, "sanction_generated")

    # Send email notification
    try:
        email_sent = await email_service.send_loan_application_notification(
            customer, terms, decision, session_id
        )
        print(f"📧 Email notification sent: {email_sent}")
    except Exception as e:
        print(f"⚠️ Email notification failed: {e}")

    # Cache the result
    await cache.set_session(session_id, {
        **state,
        "sanction_pdf": filepath,
        "letter_type": letter_type,
        "email_sent": email_sent
    })

    # ── PERSIST TO LOAN APPLICATIONS COLLECTION ──────────────────────────────
    from db.database import loan_applications_collection
    disbursed_at = datetime.utcnow()
    first_emi_due = (disbursed_at.replace(day=5) if disbursed_at.day <= 5 else (disbursed_at.replace(day=5) if disbursed_at.month < 12 else disbursed_at.replace(year=disbursed_at.year + 1, month=1, day=5)))
    if disbursed_at.day > 5:
        if disbursed_at.month == 12:
            first_emi_due = first_emi_due.replace(year=disbursed_at.year + 1, month=1)
        else:
            first_emi_due = first_emi_due.replace(month=disbursed_at.month + 1)

    emi_schedule = []
    if tenure and emi:
        due = first_emi_due
        for _ in range(int(tenure)):
            emi_schedule.append({"due_date": due.date().isoformat(), "amount": emi, "status": "pending"})
            if due.month == 12:
                due = due.replace(year=due.year + 1, month=1)
            else:
                due = due.replace(month=due.month + 1)

    loan_record = {
        "session_id": session_id,
        "customer_id": cust_id,
        "name": cust_name,
        "phone": customer.get("phone", ""),
        "email": customer.get("email", ""),
        "amount": principal,
        "loan_type": terms.get("loan_type", "Personal"),
        "interest_rate": rate,
        "tenure": tenure,
        "emi": emi,
        "status": "Approved" if is_approved else "Rejected",
        "decision": decision,  # Store the actual decision (approve/reject/soft_reject)
        "reasons": reasons,
        "dti_ratio": dti,
        "credit_score": score,
        "created_at": disbursed_at.isoformat(),
        "loan_issued_at": disbursed_at.isoformat(),
        "first_emi_due_date": first_emi_due.date().isoformat(),
        "emi_schedule": emi_schedule,
        "pdf_path": filepath,
        "email_sent": email_sent
    }
    await loan_applications_collection.insert_one(loan_record)
    status_emoji = "✅" if is_approved else "❌"
    print(f"📊 Loan application persisted: {cust_name} ({loan_record['status']}) - {decision}")

    return {
        "sanction_pdf_path": filepath,
        "letter_type": letter_type,
        "loan_terms": terms,
        "message": f"{letter_type} letter generated: {filepath}",
        "email_sent": email_sent
    }


async def process_esign_acceptance(session_id: str) -> dict:
    """Process e-sign acceptance and route to advisory agent."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    decision = state.get("decision", "")
    
    cust_name = customer.get("name", "Customer")
    principal = terms.get("principal", 0)
    
    # Generate thank you message
    if decision == "approve":
        thank_you_msg = (
            f"🎉 **Congratulations {cust_name}!**\n\n"
            f"Your loan of ₹{principal:,.0f} has been successfully approved and e-signed!\n\n"
            f"📄 **Next Steps:**\n"
            f"• Your sanction letter will be sent to your registered email\n"
            f"• Our advisory team will now contact you for documentation guidance\n"
            f"• Loan disbursement will begin after document verification\n\n"
            f"Thank you for choosing FinServe NBFC! 🙏"
        )
    else:
        thank_you_msg = (
            f"📝 **Thank you {cust_name}**\n\n"
            f"We've received your e-sign on the loan decision letter.\n\n"
            f"🤝 **Next Steps:**\n"
            f"• Our advisory team will provide personalized guidance\n"
            f"• We'll help you improve your eligibility for future applications\n"
            f"• Free financial planning consultation will be arranged\n\n"
            f"Thank you for considering FinServe NBFC! 🙏"
        )
    
    # Route to sales agent for advisory mode (post-sanction guidance)
    from agents.sales_agent import sales_agent_node
    advisory_state = {
        "customer_data": customer,
        "loan_terms": terms,
        "decision": decision,
        "session_id": session_id,
        "post_sanction": True
    }
    
    advisory_result = await sales_agent_node(advisory_state)
    msg_obj = advisory_result.get("messages", [None])[0]
    advisory_message = ""
    if msg_obj:
        if hasattr(msg_obj, "content"):
            advisory_message = msg_obj.content
        elif isinstance(msg_obj, dict):
            advisory_message = msg_obj.get("content", "")
    
    # Update session state
    await update_session(session_id, {
        "esign_completed": True,
        "advisory_message": advisory_message,
        "current_phase": "advisory"
    })
    
    return {
        "success": True,
        "message": thank_you_msg,
        "next_step": "advisory",
        "advisory_message": advisory_message
    }


async def get_letter_file(session_id: str) -> dict:
    """Get the file path and details for download."""
    state = await get_session(session_id)
    if not state:
        return None

    sanction_pdf = state.get("sanction_pdf", "")
    if not sanction_pdf or not os.path.exists(sanction_pdf):
        return None
    
    filename = os.path.basename(sanction_pdf)
    
    return {
        "file_path": sanction_pdf,
        "filename": filename,
        "message": f"Letter ready for download: {filename}"
    }
