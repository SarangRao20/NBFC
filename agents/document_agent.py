"""Document Verification Agent — Gemini Vision OCR for PAN/Aadhaar/Salary Slip/Bank Statement/ITR.

Extracts structured data from the uploaded document image using a detailed forensic prompt.
Saves all uploads to data/uploads/ for audit trail.
"""

import os, sys, shutil, json, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage, HumanMessage
from config import get_vision_llm

os.makedirs("data/uploads", exist_ok=True)


DOCUMENT_OCR_PROMPT = """You are a forensic document analysis system for a regulated NBFC (Non-Banking Financial Company) in India. Your job is to meticulously extract structured information from the provided document image with maximum accuracy.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUPPORTED DOCUMENT TYPES (Indian):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- PAN Card (Permanent Account Number — issued by Income Tax Dept.)
- Aadhaar Card (12-digit UID — issued by UIDAI)
- Salary Slip / Pay Stub (monthly income proof)
- Bank Statement (last 3-6 months)
- Form 16 (annual tax certificate from employer)
- ITR Acknowledgement (Income Tax Return)
- Passport
- Voter ID Card (EPIC)
- Driving License

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXTRACTION INSTRUCTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. First, IDENTIFY the document type by looking for key indicators:
   - PAN: "INCOME TAX DEPARTMENT", 10-character PAN number (AAAAA9999A format)
   - Aadhaar: 12-digit number, "Unique Identification Authority", QR code
   - Salary Slip: Company logo, "Net Pay"/"Basic Salary"/"Gross Earnings" headers, employee details
   - Bank Statement: Bank letterhead, account number, transaction table, opening/closing balance

2. For SALARY SLIP specifically:
   - Look for the NET PAY / TAKE HOME amount (after deductions) — this is the salary_extracted
   - Also extract GROSS SALARY if visible
   - Extract month/year of the slip
   - Extract employer name
   - Extract employee designation if visible

3. TAMPER DETECTION — flag as tampered=true if ANY of these:
   - Text/numbers appear inconsistent in font size or color within the same section
   - Background shows signs of digital editing (gradient artifacts, white patches)
   - Photo on ID appears digitally replaced or different resolution than rest of document
   - Signature is pixelated or appears copy-pasted
   - Documents numbers (PAN, Aadhaar) fail standard format validation

4. CONFIDENCE SCORE:
   - 0.90-1.00: Document is clearly legible in good lighting, all fields visible
   - 0.70-0.89: Minor blur or partial glare, most fields readable  
   - 0.50-0.69: Significant blur, shadow, or poor angle — key fields unclear
   - 0.00-0.49: Document is too damaged, folded, or obscured to reliably extract data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT — Return ONLY this JSON (no markdown, no prose):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
    "document_type": "PAN Card | Aadhaar Card | Salary Slip | Bank Statement | Form 16 | ITR | Passport | Voter ID | Driving License | Unknown",
    "name_extracted": "Full name exactly as printed on document — preserve casing",
    "salary_extracted": 0,
    "gross_salary_extracted": 0,
    "employer_name": "Company name if salary slip or Form 16",
    "document_number": "Full ID number (mask last 4 of Aadhaar for privacy)",
    "address_extracted": "Full residential address if visible",
    "dob_extracted": "Date of Birth if visible (YYYY-MM-DD)",
    "issue_date": "Issue or validity date if visible — format DD-MM-YYYY",
    "confidence": 0.95,
    "tampered": false,
    "tamper_reason": "Explain what looked suspicious if tampered=true, else empty string",
    "notes": "Any other relevant observations about document quality or content"
}"""


def document_agent_node(state: dict) -> dict:
    """Processes an uploaded document image using Gemini Vision with detailed forensic prompt."""
    print("📄 [DOCUMENT AGENT] Processing uploaded document...")

    doc_path = state.get("documents", {}).get("salary_slip_path", "")

    if not doc_path or not os.path.exists(doc_path):
        return {
            "documents": {**state.get("documents", {}), "verified": False},
            "messages": [AIMessage(content=(
                "📄 **Document Required**\n\n"
                "Please upload one of the following documents to continue:\n"
                "• **PAN Card** or **Aadhaar Card** (for basic KYC)\n"
                "• **Salary Slip** (if your loan exceeds your pre-approved limit)\n"
                "• **Bank Statement** (last 3 months for extended review)\n\n"
                "Accepted formats: JPG, PNG, PDF"
            ))],
            "current_phase": "kyc_verification"
        }

    # Save a permanent audit copy
    audit_filename = f"audit_{os.path.basename(doc_path)}"
    audit_path = os.path.join("data", "uploads", audit_filename)
    shutil.copy2(doc_path, audit_path)
    print(f"  📁 Audit copy saved: {audit_path}")

    # Read and encode document
    import base64
    ext = doc_path.rsplit(".", 1)[-1].lower()
    mime_map = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
    mime = mime_map.get(ext, "image/jpeg")

    with open(doc_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    vision_llm = get_vision_llm()

    try:
        message = HumanMessage(content=[
            {"type": "text", "text": DOCUMENT_OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}}
        ])
        response = vision_llm.invoke([message])

        # Robust JSON extraction using regex
        json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if json_match:
            try:
                extracted = json.loads(json_match.group(0))
            except Exception as je:
                print(f"  ❌ JSON parse error: {je}")
                raise ValueError("Could not parse extracted document data.")
        else:
            raise ValueError("No valid data block found in document analysis.")

        # --- Strict Verification Logic ---
        confidence = float(extracted.get("confidence", 0))
        tampered = bool(extracted.get("tampered", False))
        
        # We only mark as 'verified' if confidence is high and no tampering
        is_verified = confidence > 0.75 and not tampered
        
        if not is_verified:
            reason = extracted.get("tamper_reason") or "OCR confidence too low or document unclear."
            msg = f"❌ **Document Rejected:** {reason}\nPlease upload a clearer, original document."
            print(f"  ⚠️ Document rejected: {reason}")
        else:
            msg = f"✅ **{extracted.get('document_type', 'Document')} processed.** (Confidence: {confidence:.0%})"
            print(f"  ✅ Document verified: {extracted.get('document_type')}")

        doc_data = {
            **state.get("documents", {}),
            "verified": is_verified,
            "document_type": extracted.get("document_type", "Unknown"),
            "name_extracted": extracted.get("name_extracted", "Unknown"),
            "salary_extracted": float(extracted.get("salary_extracted") or 0),
            "gross_salary_extracted": float(extracted.get("gross_salary_extracted") or 0),
            "employer_name": extracted.get("employer_name", ""),
            "document_number": extracted.get("document_number", ""),
            "address_extracted": extracted.get("address_extracted", ""),
            "dob_extracted": extracted.get("dob_extracted", ""),
            "confidence": confidence,
            "tampered": tampered,
            "tamper_reason": extracted.get("tamper_reason", ""),
            "audit_path": audit_path,
            "notes": extracted.get("notes", "")
        }

        # Build user-friendly message
        tamper_warn = f"\n⚠️ **Tamper Alert**: {doc_data['tamper_reason']}" if doc_data["tampered"] else ""
        confidence_emoji = "🟢" if doc_data["confidence"] >= 0.85 else ("🟡" if doc_data["confidence"] >= 0.6 else "🔴")
        salary_line = f"\n💰 **Salary Extracted**: ₹{doc_data['salary_extracted']:,.0f}/month" if doc_data["salary_extracted"] > 0 else ""
        employer_line = f"\n🏢 **Employer**: {doc_data['employer_name']}" if doc_data.get("employer_name") else ""

        msg = (
            f"📄 **Document Verified**{tamper_warn}\n\n"
            f"**Type**: {doc_data['document_type']}\n"
            f"**Name on Document**: {doc_data['name_extracted']}\n"
            f"{confidence_emoji} **OCR Confidence**: {doc_data['confidence']:.0%}"
            f"{salary_line}"
            f"{employer_line}"
        )

        return {
            "documents": doc_data, 
            "messages": [AIMessage(content=msg)],
            "current_phase": "kyc_verification" if not doc_data.get("verified") else "underwriting"
        }

    except Exception as e:
        print(f"  ❌ Document agent error: {e}")
        return {
            "documents": {**state.get("documents", {}), "verified": False},
            "messages": [AIMessage(content=(
                f"❌ **Document Processing Failed**\n\n"
                "We couldn't process your document. Please ensure:\n"
                "• The image is well-lit and in focus\n"
                "• The document fills most of the frame\n"
                "• File size is under 5MB\n\n"
                f"Technical detail: {str(e)[:80]}\n\n"
                "Please try again with a clearer photo."
            ))],
            "current_phase": "kyc_verification"
        }
