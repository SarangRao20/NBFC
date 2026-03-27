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
  """Professional document collection agent with Gemini Vision OCR."""
  session_id = state.get("session_id", "default")
  await manager.broadcast_thinking(session_id, "Document Agent", True)

  print(f"📄 [DOCUMENT AGENT] Processing document phase for session: {session_id}")
  log = list(state.get("action_log") or [])
  
  docs_state = state.get("documents", {}) or {}
  doc_paths = docs_state.get("document_paths") or docs_state.get("salary_slip_path")
  required_docs = state.get("required_documents", ["Identity Proof (PAN/Aadhaar)", "Income Proof (Salary Slip)"])

  # Normalize to first path if list
  doc_path = None
  if isinstance(doc_paths, list) and doc_paths:
    doc_path = doc_paths[0]
  elif isinstance(doc_paths, str) and doc_paths:
    doc_path = doc_paths

  if not doc_path or not os.path.exists(doc_path):
    # No file present — prompt the user professionally
    await manager.broadcast_thinking(session_id, "Document Agent", False)
    doc_list_str = "\n".join([f"- {d}" for d in required_docs])
    msg = (
      f"🛡️ **Document Verification Phase**\n\n"
      f"To proceed with your application, please provide the following documentation for regulatory compliance:\n\n"
      f"{doc_list_str}\n\n"
      "Please upload clear images or PDFs. Our automated system will process them immediately to move your application to underwriting."
    )
    return {
      "documents": {**docs_state, "verified": False, "ocr_error": ""},
      "messages": [AIMessage(content=msg)],
      "current_phase": "document",
      "documents_uploaded": False,
      "options": ["📤 Upload Documents Now", "❓ Why is this required?"]
    }

  # File exists - initiate high-fidelity OCR and forensic analysis
  log.append("🔍 Initiating high-fidelity OCR and forensic document analysis...")
  
  # Audit copy
  audit_filename = f"audit_{session_id[:8]}_{os.path.basename(doc_path)}"
  audit_path = os.path.join("data", "uploads", audit_filename)
  shutil.copy2(doc_path, audit_path)

  import base64
  ext = doc_path.rsplit(".", 1)[-1].lower()
  mime_map = {"pdf": "application/pdf", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
  mime = mime_map.get(ext, "image/jpeg")

  try:
    with open(doc_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    vision_llm = get_vision_llm()
    message = HumanMessage(content=[
        {"type": "text", "text": DOCUMENT_VISION_AGENT_PROMPT},
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}}
    ])
    
    response = await vision_llm.ainvoke([message])
    text_content = response.content
    
    # Extract JSON content from potential Markdown blocks
    json_match = re.search(r'\{.*\}', text_content, re.DOTALL)
    if not json_match:
        raise ValueError("LLM response did not contain valid JSON")
        
    extracted_root = json.loads(json_match.group(0))
    all_extracted = extracted_root.get("extracted_documents", [])
    
    if not all_extracted:
        raise ValueError("No documents extracted from file")
        
    first_doc = all_extracted[0]
    doc_type = first_doc.get("document_type", "Unknown")
    ext_data = first_doc.get("extracted_data", {})
    forensic = first_doc.get("forensic_analysis", {})
    
    # Validation signals
    confidence_score = forensic.get("confidence_score", 0.0)
    is_tampered = forensic.get("is_tampered", False)
    
    # Final verification state
    is_verified = confidence_score > 0.85 and not is_tampered
    
    doc_data = {
        **docs_state,
        "verified": is_verified,
        "document_type": doc_type,
        "name_extracted": ext_data.get("full_name", ""),
        "salary_extracted": float(ext_data.get("net_monthly_income") or 0),
        "gross_salary_extracted": float(ext_data.get("gross_monthly_income") or 0),
        "employer_name": ext_data.get("employer_name", ""),
        "document_number": ext_data.get("document_number", ""),
        "issue_date": ext_data.get("document_date", ""),
        "confidence": confidence_score,
        "tampered": is_tampered,
        "tamper_indicators": forensic.get("tamper_indicators", []),
        "fraud_signals": forensic.get("fraud_signals", []),
        "all_extracted_docs": all_extracted,
        "ocr_error": ""
    }

    log.append(f"✅ Document verified: {doc_type} (Confidence: {confidence_score:.2f})")
    await manager.broadcast_thinking(session_id, "Document Agent", False)
    
    msg = f"✅ Thank you. Your {doc_type} has been verified successfully." if is_verified else f"⚠️ We encountered issues verifying your {doc_type}. Please ensure it is clear and untampered."
    
    return {
        "documents": doc_data,
        "documents_uploaded": True,
        "kyc_status": "verified" if is_verified else "failed",
        "messages": [AIMessage(content=msg)],
        "action_log": log,
        "current_phase": "underwriting" if is_verified else "kyc_verification",
        "next_agent": "underwriting_agent" if is_verified else None
    }

  except Exception as e:
    print(f"❌ DOCUMENT AGENT ERROR: {e}")
    await manager.broadcast_thinking(session_id, "Document Agent", False)
    return {
        "documents": {**docs_state, "verified": False, "ocr_error": str(e)},
        "messages": [AIMessage(content=f"❌ Error processing document: {str(e)}")],
        "current_phase": "document"
    }
