"""Sanction Letter Generator Agent — produces a professional PDF sanction letter."""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from langchain_core.messages import AIMessage

# Ensure output directories exist
os.makedirs("data/sanctions", exist_ok=True)


def sanction_agent_node(state: dict) -> dict:
    """Generates a PDF sanction letter using ReportLab."""
    print("📜 [SANCTION AGENT] Generating PDF...")

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    cust_name = customer.get("name", "Customer")
    cust_phone = customer.get("phone", "N/A")
    cust_id = state.get("customer_id", "UNKNOWN")

    principal = terms.get("principal", 0)
    rate = terms.get("rate", 0)
    tenure = terms.get("tenure", 0)
    emi = terms.get("emi", 0)
    dti = state.get("dti_ratio", 0)
    score = customer.get("score", 0)

    filename = f"{cust_id}_Sanction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join("data", "sanctions", filename)

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        c = canvas.Canvas(filepath, pagesize=letter)
        w, h = letter

        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, h - 60, "FinServe NBFC")
        c.setFont("Helvetica", 10)
        c.drawString(50, h - 78, "Registered Office: Financial District, Mumbai | CIN: U65100MH2024PLC123456")
        c.line(50, h - 85, w - 50, h - 85)

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, h - 115, "LOAN SANCTION LETTER")
        c.setFont("Helvetica", 11)
        c.drawString(50, h - 135, f"Date: {datetime.now().strftime('%d %B %Y')}")
        c.drawString(50, h - 150, f"Reference No: NBFC/SL/{cust_id}/{datetime.now().strftime('%Y%m%d')}")

        # Applicant Details
        y = h - 185
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Applicant Details")
        c.setFont("Helvetica", 11)
        y -= 20; c.drawString(70, y, f"Name: {cust_name}")
        y -= 18; c.drawString(70, y, f"Phone: {cust_phone}")
        y -= 18; c.drawString(70, y, f"Customer ID: {cust_id}")
        y -= 18; c.drawString(70, y, f"Credit Score: {score}")

        # Loan Details
        y -= 35
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Sanctioned Loan Details")
        c.setFont("Helvetica", 11)
        y -= 20; c.drawString(70, y, f"Sanctioned Amount: INR {principal:,.2f}")
        y -= 18; c.drawString(70, y, f"Interest Rate: {rate}% per annum")
        y -= 18; c.drawString(70, y, f"Tenure: {tenure} months")
        y -= 18; c.drawString(70, y, f"Monthly EMI: INR {emi:,.2f}")
        y -= 18; c.drawString(70, y, f"DTI Ratio: {dti*100:.1f}%")
        y -= 18; c.drawString(70, y, f"EMI Due Date: 15th of every month")

        # Terms
        y -= 35
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Terms & Conditions")
        c.setFont("Helvetica", 10)
        terms_list = [
            "1. This sanction is valid for 30 days from the date of issue.",
            "2. Disbursement is subject to completion of all documentation.",
            "3. Late payment will attract a penalty of 2% per month on the overdue EMI.",
            "4. Prepayment is allowed after 6 months with no additional charges.",
            "5. The NBFC reserves the right to modify terms based on regulatory changes.",
        ]
        for t in terms_list:
            y -= 16
            c.drawString(70, y, t)

        # Footer
        y -= 45
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(50, y, "This is a system-generated document from FinServe NBFC AI Pipeline.")
        y -= 14
        c.drawString(50, y, "For queries, contact: support@finserve-nbfc.in | 1800-XXX-XXXX")

        c.save()

    except ImportError:
        # ReportLab not installed — create a text fallback
        filepath = filepath.replace(".pdf", ".txt")
        with open(filepath, "w") as f:
            f.write(f"SANCTION LETTER — {cust_name}\nAmount: {principal}\nEMI: {emi}\n")

    msg = f"📜 **Sanction Letter Generated!**\nFile: `{filepath}`\nYou can download it from the chat."
    return {"sanction_pdf": filepath, "messages": [AIMessage(content=msg)]}
