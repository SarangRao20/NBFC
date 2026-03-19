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

        # Reasons
        y -= 30
        c.setFont("Helvetica", 11)
        c.drawString(50, y, "Dear applicant, after careful review of your application, we are unable to approve")
        y -= 16
        c.drawString(50, y, "your loan at this time due to the following reasons:")
        
        y -= 25
        for idx, reason in enumerate(reasons, 1):
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
