import os
from datetime import datetime

os.makedirs("data/sanctions", exist_ok=True)

def generate_rejection_letter(customer: dict, terms: dict, reasons: list, cust_id: str = "UNKNOWN") -> str:
    """Generates a PDF rejection letter using ReportLab."""
    print("📜 [PDF GENERATOR] Generating Rejection Letter...")

    cust_name = customer.get("name", "Customer")
    cust_phone = customer.get("phone", "N/A")
    principal = terms.get("principal", 0)

    filename = f"{cust_id}_Rejection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
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
        c.drawString(50, h - 115, "LOAN APPLICATION DECISION")
        c.setFont("Helvetica", 11)
        c.drawString(50, h - 135, f"Date: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}")
        c.drawString(50, h - 150, f"Reference No: NBFC/REJ/{cust_id}/{datetime.now().strftime('%Y%m%d')}")

        # Applicant Details
        y = h - 185
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Applicant Details")
        c.setFont("Helvetica", 11)
        y -= 20; c.drawString(70, y, f"Name: {cust_name}")
        y -= 18; c.drawString(70, y, f"Phone: {cust_phone}")
        y -= 18; c.drawString(70, y, f"Requested Amount: INR {principal:,.2f}")

        # Decision
        y -= 35
        c.setFont("Helvetica-Bold", 13)
        c.setFillColorRGB(0.8, 0, 0)
        c.drawString(50, y, "Decision: Application Declined")
        c.setFillColorRGB(0, 0, 0)

        # Loan Details Summary
        y -= 30
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, "Loan Request Summary")
        c.setFont("Helvetica", 10)
        y -= 18
        c.drawString(70, y, f"Loan Amount Requested: INR {principal:,.2f}")
        y -= 15
        loan_rate = terms.get("rate", 0)
        loan_tenure = terms.get("tenure", 0)
        if loan_rate and loan_tenure:
            monthly_emi = (principal * loan_rate / 1200) / (1 - (1 + loan_rate / 1200) ** (-loan_tenure))
            c.drawString(70, y, f"Proposed Tenure: {loan_tenure} months")
            y -= 15
            c.drawString(70, y, f"Proposed Interest Rate: {loan_rate:.2f}% p.a.")
            y -= 15
            c.drawString(70, y, f"Estimated Monthly EMI: INR {monthly_emi:,.2f}")
            y -= 18
        c.setFont("Helvetica", 11)
        c.drawString(50, y, "Dear applicant, after careful review of your application, we are unable to approve")
        y -= 16
        c.drawString(50, y, "your loan at this time due to the following reasons:")
        
        y -= 25
        c.setFont("Helvetica", 10)
        for idx, reason in enumerate(reasons, 1):
            # Split long reasons into multiple lines if needed
            if len(reason) > 90:
                # Split at word boundary
                words = reason.split()
                line = ""
                for word in words:
                    if len(line + word) > 90:
                        c.drawString(70, y, line)
                        y -= 15
                        line = word
                    else:
                        line += word + " "
                if line:
                    c.drawString(70, y, line)
                    y -= 18
            else:
                c.drawString(70, y, f"{idx}. {reason}")
                y -= 18

        # Footer
        y = 100
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(50, y, "This is a system-generated document from FinServe NBFC AI Pipeline.")
        y -= 14
        c.drawString(50, y, "For queries, contact: support@finserve-nbfc.in | 1800-XXX-XXXX")

        c.save()

    except ImportError:
        filepath = filepath.replace(".pdf", ".txt")
        with open(filepath, "w") as f:
            f.write(f"REJECTION LETTER — {cust_name}\nReasons:\n" + "\n".join(reasons))

    return filepath
