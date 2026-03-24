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
    log.append("📜 Drafting legally-compliant Sanction Letter and Loan Agreement...")

    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    
    principal = terms.get("principal", 0)
    rate = terms.get("rate", 0.10)
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

        # Header
        elements.append(Paragraph("<b>FinServe NBFC Ltd.</b>", styles["Title"]))
        elements.append(Paragraph(f"<b>{letter_label.upper()} LETTER</b>", styles["Heading2"]))
        elements.append(Paragraph(f"Date: {current_date}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        # Applicant Table
        app_data = [
            ["Name", cust_name],
            ["Address", Paragraph(cust_addr, styles["Normal"])],
            ["Phone", cust_phone],
            ["Status", status_text],
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

    msg = (f"📜 **Your Sanction Letter is Ready!**\n\n"
           f"I've generated your official agreement (ID: {filename}).\n\n"
           f"**NEXT STEP**: Please click the button below to **E-sign** and authorize the disbursement of ₹{principal:,} to your linked account.")
    
    updates = {
        "sanction_pdf": filepath, 
        "messages": [AIMessage(content=msg)],
        "action_log": log,
        "options": ["✍️ E-sign & Disburse", "📄 View Letter", "Talk to Arjun"],
        "current_phase": "sanction_esign",
        "customer_data": customer
    }
    
    # Save to DB
    try:
        await SessionManager.save_document(session_id, "sanction_letter", filepath, {"type": letter_label}, 1.0)
    except: pass
    
    try:
        await SessionManager.save_session(session_id, updates)
    except: pass
    
    return updates
