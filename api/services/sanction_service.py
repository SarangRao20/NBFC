"""Sanction Service — compile terms + generate PDF (Step 16)."""

import os
from datetime import datetime
from api.core.state_manager import get_session, update_session, advance_phase
from api.config import get_settings

settings = get_settings()


async def generate_sanction(session_id: str) -> dict:
    """Step 16: Compile Final Terms → Generate Loan PDF → Send to User."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    decision = state.get("decision", "")

    cust_name = customer.get("name", "Customer")
    cust_id = state.get("customer_id", "UNKNOWN")
    principal = terms.get("principal", 0)
    rate = terms.get("rate", 0)
    tenure = terms.get("tenure", 0)
    emi = terms.get("emi", 0)
    dti = state.get("dti_ratio", 0)
    score = customer.get("credit_score", 0)

    is_approved = decision == "approve"
    letter_type = "Sanction" if is_approved else "Rejection"
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
            app_data.append(["Rejection Reasons", "; ".join(state.get("reasons", []))])

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

    # ── PERSIST TO LOAN APPLICATIONS COLLECTION ──────────────────────────────
    from db.database import loan_applications_collection
    loan_record = {
        "session_id": session_id,
        "customer_id": cust_id,
        "name": cust_name,
        "phone": customer.get("phone", ""),
        "amount": principal,
        "loan_type": terms.get("loan_type", "Personal"),
        "interest_rate": rate,
        "tenure": tenure,
        "emi": emi,
        "status": "Approved" if is_approved else "Rejected",
        "reasons": state.get("reasons", []),
        "created_at": datetime.utcnow().isoformat(),
        "pdf_path": filepath
    }
    await loan_applications_collection.insert_one(loan_record)
    print(f"📊 Loan application persisted: {cust_name} ({loan_record['status']})")

    return {
        "sanction_pdf_path": filepath,
        "letter_type": letter_type,
        "loan_terms": terms,
        "message": f"{letter_type} letter generated: {filepath}"
    }
