"""Sanction Letter Generator Agent — produces a professional PDF sanction letter."""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from langchain_core.messages import AIMessage

# Ensure output directories exist
os.makedirs("data/sanctions", exist_ok=True)


def sanction_agent_node(state: dict):
    """
    Generates a formal Sanction Letter PDF string based on confirmed loan details.
    """
    print("📜 [SANCTION AGENT] Generating final sanction letter...")
    log = list(state.get("action_log") or [])
    log.append("📜 Generating Official Sanction Letter")

    import datetime
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    
    terms = state.get("loan_terms", {})
    customer = state.get("customer_data", {})

    principal = terms.get("principal", 0)
    rate = terms.get("rate", 0)
    tenure = terms.get("tenure", 0)
    emi = terms.get("emi", 0)
    cust_name = customer.get("name", "Applicant")
    cust_phone = customer.get("phone", "N/A")
    cust_id = state.get("customer_id", "UNKNOWN")

    dti = state.get("dti_ratio", 0)
    score = customer.get("credit_score", 0)

    # Determine letter type (approved or rejected)
    status = state.get("decision", "approve").strip().lower()
    is_approved = status != "reject" and status != "hard_reject"
    status_text = "Approved" if is_approved else "Rejected"

    rejection_reason = state.get("rejection_reason", "Not specified")

    letter_label = "Sanction" if is_approved else "Rejection"

    letter = f"""**{letter_label.upper()} LETTER**
Date: {current_date}

Dear {cust_name},

We are pleased to inform you that your application for a {terms.get("loan_type", "Personal")} Loan has been {status_text.lower()}.

**Approved Terms:**
- **Loan Amount (Principal):** ₹{principal:,.0f}
- **Interest Rate:** {rate}% per annum
- **Tenure:** {tenure} months
- **Calculated EMI:** ₹{emi:,.0f}
- **Processing Fee:** ₹{(principal * 0.01):,.0f} (1%)

This offer is valid for 15 days from the date of issuance. Please review and accept these terms to authorize disbursement to your verified bank account.

Authorized Signatory,
FinServe Underwriting Desk
    """
    
    filename = f"{cust_phone}_{letter_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join("data", "sanctions", filename)

    log.append(f"✅ {letter_label} ready for e-signature")
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.pagesizes import letter

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
        )
        styles = getSampleStyleSheet()

        elements = []

        # ================= HEADER =================
        elements.append(Paragraph("<b>FinServe NBFC Ltd.</b>", styles["Title"]))
        elements.append(Paragraph("Registered Office: Financial District, Mumbai", styles["Normal"]))
        elements.append(Paragraph("CIN: U65100MH2024PLC123456", styles["Normal"]))
        elements.append(Spacer(1, 12))

        letter_title = "LOAN SANCTION LETTER" if is_approved else "LOAN REJECTION LETTER"
        elements.append(Paragraph(f"<b>{letter_title}</b>", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d %B %Y')}", styles["Normal"]))
        elements.append(Paragraph(
            f"<b>Reference No:</b> NBFC/SL/{cust_id}/{datetime.now().strftime('%Y%m%d')}",
            styles["Normal"],
        ))
        elements.append(Spacer(1, 14))

        # ================= APPLICANT DETAILS =================
        elements.append(Paragraph("<b>Applicant Details</b>", styles["Heading3"]))
        elements.append(Spacer(1, 6))

        app_data = [
            ["Name", cust_name],
            ["Phone", cust_phone],
            ["Customer ID", cust_id],
            ["Credit Score", str(score)],
            ["Application Status", status_text],
        ]

        if not is_approved:
            app_data.append(["Reason for Rejection", rejection_reason])

        table = Table(app_data, colWidths=[150, 300])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 14))

        # ================= LOAN DETAILS =================
        elements.append(Paragraph("<b>Loan Details</b>", styles["Heading3"]))
        elements.append(Spacer(1, 6))

        loan_data = [
            ["Sanctioned Amount", f"INR {principal:,.2f}"],
            ["Interest Rate", f"{rate}% p.a."],
            ["Tenure", f"{tenure} months"],
            ["EMI", f"INR {emi:,.2f}"],
            ["DTI Ratio", f"{dti*100:.1f}%"],
            ["EMI Due Date", "15th of every month"],
        ]

        loan_table = Table(loan_data, colWidths=[200, 250])
        loan_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ]))
        elements.append(loan_table)
        elements.append(Spacer(1, 14))

        # ================= STATUS MESSAGE =================
        if is_approved:
            status_message = (
                "Congratulations! Your loan application has been approved. "
                "Please complete your documentation within 30 days for disbursement."
            )
        else:
            status_message = (
                "Thank you for applying. Unfortunately, your loan application has been declined. "
                "Please review the reason above and feel free to reapply after addressing the concerns."
            )

        elements.append(Paragraph(status_message, styles["Normal"]))
        elements.append(Spacer(1, 30))

        # ================= SIGNATURE PAGE (page 1) =================
        elements.append(Paragraph(
            "This is a system-generated letter and does not require a physical signature.",
            styles["Italic"],
        ))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>For FinServe NBFC Ltd.</b>", styles["Normal"]))
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("Authorized Signatory", styles["Normal"]))

        # Force a new page for terms & conditions
        elements.append(PageBreak())

        # ================= TERMS (page 2) =================
        elements.append(Paragraph("<b>Terms & Conditions</b>", styles["Heading3"]))
        elements.append(Spacer(1, 8))

        terms_text = (
            "1. This sanction is valid for 30 days from the date of issue. <br/>"
            "2. Disbursement is subject to completion of all documentation. <br/>"
            "3. Late payment attracts penal interest at 2% per month on overdue amounts. <br/>"
            "4. Prepayment is permitted after 6 months, subject to applicable policies. <br/>"
            "5. The Company reserves the right to revise terms in accordance with regulatory guidelines. <br/>"
        )
        elements.append(Paragraph(terms_text, styles["Normal"]))
        elements.append(Spacer(1, 14))

        elements.append(Paragraph(
            "This is a system-generated document from FinServe NBFC." ,
            styles["Italic"],
        ))

        doc.build(elements)
    except ImportError:
        # ReportLab not installed — create a text fallback
        filepath = filepath.replace(".pdf", ".txt")
        with open(filepath, "w") as f:
            f.write(
                f"{letter_label.upper()} LETTER — {cust_name}\n"
                f"Status: {status_text}\n"
                f"Amount: {principal}\n"
                f"EMI: {emi}\n"
                f"Reason: {rejection_reason if not is_approved else 'N/A'}\n"
            )

    msg = f"📜 **{letter_label} Letter Generated!**\nFile: `{filepath}`\nYou can download it from the chat."
    import json
    msg_json = json.dumps({"type": "sanction_letter", "content": msg})
    return {
        "sanction_pdf": filepath, 
        "messages": [AIMessage(content=msg_json)],
        "action_log": log
    }
