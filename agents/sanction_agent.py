"""Sanction Letter Generator Agent — produces a professional PDF sanction letter."""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from langchain_core.messages import AIMessage

# Ensure output directories exist
os.makedirs("data/sanctions", exist_ok=True)


async def sanction_agent_node(state: dict):
    """
    Generates a formal Sanction Letter PDF string based on confirmed loan details.
    """
    print("📜 [SANCTION AGENT] Generating final sanction letter...")
    
    log = list(state.get("action_log") or [])
    log.append("📜 Arjun: Constructing final Sanction Letter PDF...")

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
    
    log.append(f"✍️ Drafting {letter_label} Letter for {cust_name}...")

    filename = f"{cust_phone}_{letter_label}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join("data", "sanctions", filename)

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
        elements.append(Spacer(1, 12))

        letter_title = "LOAN SANCTION LETTER" if is_approved else "LOAN REJECTION LETTER"
        elements.append(Paragraph(f"<b>{letter_title}</b>", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        elements.append(Paragraph(f"<b>Date:</b> {current_date}", styles["Normal"]))
        elements.append(Spacer(1, 14))

        # ================= APPLICANT DETAILS =================
        elements.append(Paragraph("<b>Applicant Details</b>", styles["Heading3"]))
        elements.append(Spacer(1, 6))

        app_data = [
            ["Name", cust_name],
            ["Phone", cust_phone],
            ["Customer ID", cust_id],
            ["Status", status_text],
        ]
        if not is_approved:
            app_data.append(["Reason", rejection_reason])

        table = Table(app_data, colWidths=[150, 300])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 14))

        # ================= LOAN DETAILS (only if approved) =================
        if is_approved:
            elements.append(Paragraph("<b>Loan Details</b>", styles["Heading3"]))
            elements.append(Spacer(1, 6))
            loan_data = [
                ["Sanctioned Amount", f"INR {principal:,.2f}"],
                ["Interest Rate", f"{rate}% p.a."],
                ["Tenure", f"{tenure} months"],
                ["EMI", f"INR {emi:,.2f}"],
            ]
            loan_table = Table(loan_data, colWidths=[200, 250])
            loan_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ]))
            elements.append(loan_table)
            elements.append(Spacer(1, 14))

        doc.build(elements)
        log.append(f"✅ Generated PDF file: {filename}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        log.append(f"⚠️ PDF generation failed, creating text fallback.")
        filepath = filepath.replace(".pdf", ".txt")
        with open(filepath, "w") as f:
            f.write(f"{letter_label.upper()} LETTER\nName: {cust_name}\nStatus: {status_text}")

    msg = f"📜 **{letter_label} Letter Generated!**\n\nYour official document is ready for download: `{filename}`\n\nPlease review the terms and click 'Complete' to finalize your session."
    
    log.append(f"📫 Document dispatched to user.")

    return {
        "sanction_pdf": filepath, 
        "messages": [AIMessage(content=msg)],
        "action_log": log,
        "options": ["Download Letter", "Complete Session"]
    }
