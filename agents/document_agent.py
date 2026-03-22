"""Document Verification Agent — Gemini Vision OCR for PAN/Aadhaar/Salary Slip/Bank Statement/ITR.

Extracts structured data from the uploaded document image using a detailed forensic prompt.
Saves all uploads to data/uploads/ for audit trail.
"""

import os, sys, shutil, json, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage, HumanMessage
from config import get_vision_llm

os.makedirs("data/uploads", exist_ok=True)


def _calculate_name_similarity(doc_name: str, customer_name: str) -> float:
    """Calculate similarity score between document name and customer name."""
    if not doc_name or not customer_name:
        return 0.0
    
    # Simple similarity based on common words and exact matches
    doc_words = set(doc_name.lower().split())
    cust_words = set(customer_name.lower().split())
    
    # Remove common titles/words
    common_words = {"kumar", "singh", "mr", "mrs", "ms", "shri", "smt"}
    doc_words -= common_words
    cust_words -= common_words
    
    if not cust_words:
        return 0.0
    
    # Calculate Jaccard similarity
    intersection = doc_words.intersection(cust_words)
    union = doc_words.union(cust_words)
    
    if not union:
        return 0.0
    
    similarity = len(intersection) / len(union)
    
    # Bonus for exact name match
    if doc_name.lower() == customer_name.lower():
        similarity = max(similarity, 0.9)
    
    return similarity


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


from api.core.websockets import manager

async def document_agent_node(state: dict) -> dict:
    """Processes an uploaded document image using Gemini Vision with detailed forensic prompt."""
    session_id = state.get("session_id", "default")
    await manager.broadcast_thinking(session_id, "Document Agent", True)

    print("📄 [DOCUMENT AGENT] Processing uploaded document...")
    log = list(state.get("action_log") or [])
    log.append("📄 Reading uploaded document...")

    doc_path = state.get("documents", {}).get("salary_slip_path", "")

    if not doc_path or not os.path.exists(doc_path):
        await manager.broadcast_thinking(session_id, "Document Agent", False)
        return {
            "documents": {**state.get("documents", {}), "verified": False, "ocr_error": "No document path found"},
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
        response = await vision_llm.ainvoke([message])

        # Robust JSON extraction using regex
        text_content = response.content
        print(f"📄 [DOCUMENT AGENT] Raw OCR Response: {text_content[:200]}...")
        
        json_match = re.search(r'\{.*\}', text_content, re.DOTALL)
        if json_match:
            try:
                extracted = json.loads(json_match.group(0))
            except Exception as je:
                print(f"  ❌ JSON parse error: {je}")
                # Fallback: Try to manual parse if it's very close
                extracted = {"document_type": "Unknown", "confidence": 0.3}
        else:
            print("  ⚠️ No JSON found in OCR response. Attempting recovery...")
            extracted = {"document_type": "Unknown", "confidence": 0.1}

        # --- Enhanced Verification Logic ---
        confidence = float(extracted.get("confidence", 0))
        tampered = bool(extracted.get("tampered", False))
        document_type = extracted.get("document_type", "Unknown")
        name_extracted = extracted.get("name_extracted", "").strip()
        
        # Get customer data for identity verification
        customer_data = state.get("customer_data", {})
        customer_name = customer_data.get("name", "").strip().lower()
        customer_phone = customer_data.get("phone", "")
        loan_amount = state.get("loan_terms", {}).get("principal", 0)
        pre_approved = customer_data.get("pre_approved_limit", 0)
        
        # Document type validation based on loan requirements
        required_docs = []
        if loan_amount > pre_approved:
            required_docs.append("Salary Slip")
        required_docs.extend(["PAN Card", "Aadhaar Card"])
        
        is_valid_doc_type = document_type in required_docs
        name_match_score = _calculate_name_similarity(name_extracted.lower(), customer_name) if customer_name else 0
        
        # Enhanced verification criteria
        verification_checks = {
            "confidence_ok": confidence > 0.75,
            "not_tampered": not tampered,
            "valid_doc_type": is_valid_doc_type,
            "name_match": name_match_score > 0.7 if customer_name else True  # Skip name check if no customer name
        }
        
        is_verified = all(verification_checks.values())
        
        # Build detailed verification message
        log.append(f"🔍 Analyzing {document_type}...")
        
        reason = ""
        if not is_verified:
            issues = []
            if not verification_checks["confidence_ok"]:
                issues.append(f"Low OCR confidence ({confidence:.0%})")
            if verification_checks["not_tampered"]:
                issues.append("Document appears tampered")
            if not verification_checks["valid_doc_type"]:
                issues.append(f"Invalid document type. Expected one of: {', '.join(required_docs)}")
            if not verification_checks["name_match"] and customer_name:
                issues.append(f"Name mismatch: '{name_extracted}' vs '{customer_data.get('name', '')}'")
            
            reason = "; ".join(issues)
            msg = f"❌ **Document Verification Failed:** {reason}\n\nPlease upload a valid, original document."
            log.append(f"❌ Verification failed: {reason}")
            print(f"  ⚠️ Document rejected: {reason}")
        else:
            confidence_emoji = "🟢" if confidence >= 0.85 else "🟡"
            msg = f"✅ **{document_type} verified successfully** {confidence_emoji} ({confidence:.0%} confidence)"
            if customer_name and name_match_score > 0.7:
                msg += f"\n✅ Identity verified: Name matches ({name_match_score:.0%} similarity)"
            log.append(f"✅ {document_type} verified successfully.")
            print(f"  ✅ Document verified: {document_type} for {customer_name or 'Unknown'}")

        doc_data = {
            **state.get("documents", {}),
            "verified": is_verified,
            "ocr_error": reason if not is_verified else "",
            "document_type": document_type,
            "name_extracted": name_extracted,
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
            "notes": extracted.get("notes", ""),
            "verification_checks": verification_checks,
            "name_match_score": name_match_score,
            "required_documents": required_docs,
            "customer_name_verified": customer_name and name_match_score > 0.7
        }

        # Build user-friendly message with verification details
        tamper_warn = f"\n⚠️ **Tamper Alert**: {doc_data['tamper_reason']}" if doc_data["tampered"] else ""
        salary_line = f"\n💰 **Salary Extracted**: ₹{doc_data['salary_extracted']:,.0f}/month" if doc_data["salary_extracted"] > 0 else ""
        employer_line = f"\n🏢 **Employer**: {doc_data['employer_name']}" if doc_data.get("employer_name") else ""
        
        # Add verification status details
        verification_details = []
        if verification_checks["valid_doc_type"]:
            verification_details.append("✅ Valid document type")
        if customer_name and name_match_score > 0.7:
            verification_details.append(f"✅ Identity verified ({name_match_score:.0%} match)")
        if verification_checks["confidence_ok"]:
            verification_details.append("✅ High confidence OCR")
        
        verification_summary = "\n" + "\n".join(verification_details) if verification_details else ""

        final_msg = msg + verification_summary + salary_line + employer_line + tamper_warn
        
        await manager.broadcast_thinking(session_id, "Document Agent", False)
        return {
            "documents": doc_data, 
            "messages": [AIMessage(content=final_msg)],
            "action_log": log,
            "options": ["Proceed to Fraud Check", "Re-upload Document", "Talk to Specialist"] if is_verified else ["Re-upload Document", "Need help?", "Exit"],
            "current_phase": "kyc_verification" if not doc_data.get("verified") else "fraud_analysis"
        }

    except Exception as e:
        print(f"  ❌ Document agent error: {e}")
        await manager.broadcast_thinking(session_id, "Document Agent", False)
        return {
            "documents": {**state.get("documents", {}), "verified": False, "ocr_error": str(e)},
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
