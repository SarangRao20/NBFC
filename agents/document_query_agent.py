"""Document Query Agent — answers 'is this document valid for me?' in Sales chat."""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage
from config import get_vision_llm

# Document types accepted per loan limit tier
ACCEPTED_DOCS = {
    "safe":     ["aadhaar", "pan", "voter id", "passport"],
    "extended": ["salary slip", "bank statement", "form 16"],
    "high_risk": ["itr", "gst certificate", "property document", "income certificate"]
}

async def document_query_agent_node(state: dict) -> dict:
    """
    Extracts doc type from an uploaded file and tells user if it's acceptable.
    State keys:
        - doc_path: path to the uploaded file
        - loan_principal: requested loan amount (float)
        - pre_approved_limit: customer's limit (float)
    """
    doc_path = state.get("doc_path", "")
    principal = float(state.get("loan_principal", 0))
    limit = float(state.get("pre_approved_limit", 100000))

    if not doc_path or not os.path.exists(doc_path):
        return {"messages": [AIMessage(content="⚠️ No valid document found. Please upload a file first.")]}

    # Determine the required tier
    ratio = principal / limit if limit > 0 else 1
    if ratio <= 1:
        tier = "safe"
        tier_label = "Basic KYC (Safe Limit)"
        accepted = ACCEPTED_DOCS["safe"]
    elif ratio <= 2:
        tier = "extended"
        tier_label = "Extended Review"
        accepted = ACCEPTED_DOCS["safe"] + ACCEPTED_DOCS["extended"]
    else:
        tier = "high_risk"
        tier_label = "High Risk Verification"
        accepted = ACCEPTED_DOCS["safe"] + ACCEPTED_DOCS["extended"] + ACCEPTED_DOCS["high_risk"]

    # Use Gemini Vision to extract document type & name
    try:
        llm = get_vision_llm()
        with open(doc_path, "rb") as f:
            img_bytes = f.read()

        import base64
        b64 = base64.b64encode(img_bytes).decode()
        ext = doc_path.rsplit(".", 1)[-1].lower()
        mime = "application/pdf" if ext == "pdf" else f"image/{ext}"

        prompt = (
            "You are a document classifier. Look at this document and respond ONLY with:\n"
            "DOCUMENT_TYPE: <exact type, e.g. Aadhaar Card, PAN Card, Salary Slip, Bank Statement, Passport>\n"
            "NAME_ON_DOC: <full name as printed on document>\n"
            "VALID: <YES or NO based on whether it appears to be a genuine government/official document>"
        )

        response = llm.invoke([
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                ]
            }
        ])

        lines = response.content.strip().split("\n")
        doc_type_raw = ""
        name_on_doc = ""
        valid_flag = "YES"
        for line in lines:
            if line.startswith("DOCUMENT_TYPE:"):
                doc_type_raw = line.split(":", 1)[1].strip()
            elif line.startswith("NAME_ON_DOC:"):
                name_on_doc = line.split(":", 1)[1].strip()
            elif line.startswith("VALID:"):
                valid_flag = line.split(":", 1)[1].strip().upper()

        doc_type_lower = doc_type_raw.lower()
        is_accepted = any(a in doc_type_lower for a in accepted)

        if valid_flag != "YES":
            msg = (
                f"⚠️ **Document appears invalid or unclear.**\n"
                f"Type detected: `{doc_type_raw}`\n"
                f"Please upload a clear, official document."
            )
        elif is_accepted:
            msg = (
                f"✅ **Valid Document for your loan tier ({tier_label})**\n\n"
                f"📄 Type: **{doc_type_raw}**\n"
                f"👤 Name on document: **{name_on_doc}**\n\n"
                f"This document is accepted for your current loan request. "
                f"You can proceed with this document during verification."
            )
        else:
            accepted_str = ", ".join(a.title() for a in accepted)
            msg = (
                f"❌ **Document not sufficient for your loan tier ({tier_label})**\n\n"
                f"📄 Type detected: **{doc_type_raw}**\n\n"
                f"For a loan of ₹{principal:,.0f} against your limit of ₹{limit:,.0f}, "
                f"you need one of:\n👉 **{accepted_str}**"
            )

    except Exception as e:
        msg = f"⚠️ Could not analyze document: {str(e)[:100]}"

    return {"messages": [AIMessage(content=msg)]}
