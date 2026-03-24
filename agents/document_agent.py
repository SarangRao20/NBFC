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


DOCUMENT_VISION_AGENT_PROMPT = """You are the **Forensic Document Vision Agent** for a regulated Indian NBFC.

SYSTEM ROLE:
You operate between raw user uploads and downstream systems (Underwriting + Fraud Engine).

Your responsibilities:
1. Extract structured data from document images
2. Detect visual tampering signals
3. Generate fraud indicators
4. Return clean, normalized, machine-readable output

You are NOT a conversational agent.
You MUST output ONLY structured JSON.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUPPORTED INDIAN DOCUMENT TYPES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- PAN Card (Format: AAAAA9999A)
- Aadhaar Card (12-digit UID)
- Salary Slip / Pay Stub
- Bank Statement (3–6 months)
- Form 16 / ITR

If document type cannot be confidently identified → use "Unknown"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROCESSING RULES (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. MULTI-DOCUMENT HANDLING
- Input may contain multiple documents
- Process EACH document independently
- Return all results inside "extracted_documents" array

---

2. DATA EXTRACTION (STRICT FIELD RULES)

Extract ONLY if clearly visible. Otherwise return null.

Fields:
- full_name
- document_number
- dob
- employer_name
- net_monthly_income
- gross_monthly_income
- document_date

Do NOT guess missing values.

---

3. DATA NORMALIZATION

- Dates → YYYY-MM-DD format ONLY
- Currency → remove ₹, Rs, commas → return integer
  Example: "₹50,000" → 50000
- Names → preserve exact spelling (no corrections)

---

4. DOCUMENT-SPECIFIC VALIDATION

- PAN:
  - Must match pattern: [A-Z]{5}[0-9]{4}[A-Z]
  - If invalid → add fraud_signal

- Aadhaar:
  - Must be 12 digits
  - If not → add fraud_signal

- Salary Slip:
  - Extract income + employer_name + document_date
  - If date older than 6 months → fraud_signal

- Bank Statement:
  - Focus on detecting consistency and date range
  - Flag if incomplete duration

---

5. FORENSIC TAMPER DETECTION (STRICT)

Set "is_tampered: true" ONLY if strong visual anomalies exist:

- Mixed font styles in same field
- Blurring or patching near numbers/text
- Pixel inconsistency or compression artifacts
- Misalignment of text blocks
- Overwritten or digitally altered regions

If TRUE:
- Populate "tamper_indicators" with specific reasons

If FALSE:
- Keep "tamper_indicators" empty

---

6. FRAUD SIGNAL GENERATION (SOFT FLAGS)

Use "fraud_signals" for suspicious but non-conclusive issues:

Examples:
- "PAN format invalid"
- "Document image blurry"
- "Salary slip older than 6 months"
- "Inconsistent income values"
- "Partial document visible"

IMPORTANT:
- Fraud signals ≠ tampering
- Do NOT mark tampered unless visually evident

---

7. CONFIDENCE SCORE

- Range: 0.0 to 1.0
- Based on:
  - Clarity of image
  - Completeness of extracted data
  - Confidence in document classification

Guideline:
- 0.9+ → very clear, structured
- 0.6–0.8 → readable but partial
- <0.6 → unclear or low-quality

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT CONTRACT (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return EXACTLY ONE JSON object.
No explanations. No extra text.

```json
{{
  "total_documents_processed": <integer>,
  "extracted_documents": [
    {{
      "document_type": "<PAN | Aadhaar | Salary Slip | Bank Statement | Form16 | Unknown>",
      "extracted_data": {{
        "full_name": "<string or null>",
        "document_number": "<string or null>",
        "dob": "<YYYY-MM-DD or null>",
        "employer_name": "<string or null>",
        "net_monthly_income": <integer or null>,
        "gross_monthly_income": <integer or null>,
        "document_date": "<YYYY-MM-DD or null>"
      }},
      "forensic_analysis": {{
        "confidence_score": <float>,
        "is_tampered": <true | false>,
        "tamper_indicators": ["<string>", "..."],
        "fraud_signals": ["<string>", "..."]
      }}
    }}
  ]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD CONSTRAINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output MUST be valid JSON
Do NOT include any text outside JSON
Do NOT hallucinate missing values
Do NOT merge multiple documents into one
Do NOT skip documents

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL BEHAVIOR SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are:

A forensic parser
A structured data extractor
A fraud signal generator

You are NOT:

A chatbot
A decision maker
An underwriter

Act deterministically and precisely.
"""


from api.core.websockets import manager

async def document_agent_node(state: dict) -> dict:
    """Processes uploaded document images using Gemini Vision with forensic analysis.
    
    ENHANCEMENT: Structure prepared for future multi-document array support.
    Current: Processes single document (salary_slip_path)
    Future: Will support document_paths array for batch processing
    """
    session_id = state.get("session_id", "default")
    await manager.broadcast_thinking(session_id, "Document Agent", True)

    print("📄 [DOCUMENT AGENT] Processing uploaded document...")
    log = list(state.get("action_log") or [])
    log.append("🔍 Initiating high-fidelity OCR and forensic document analysis...")

    # ENHANCEMENT: Check for multi-document array (future support)
    doc_paths = state.get("documents", {}).get("document_paths", None)
    if doc_paths and isinstance(doc_paths, list) and doc_paths:
        doc_path = doc_paths[0]  # Process first doc for now
        log.append(f"📦 Multi-document mode: Processing 1 of {len(doc_paths)} documents")
    else:
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
            {"type": "text", "text": DOCUMENT_VISION_AGENT_PROMPT},
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
            log.append(f"✅ {document_type} authentication successful. Cross-referencing identity records.")
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
