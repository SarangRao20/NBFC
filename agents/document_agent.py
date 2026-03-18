"""Document Verification Agent — Gemini Vision OCR for PAN/Aadhaar/Salary Slip.

Extracts text, name, and salary from uploaded documents.
Saves all uploads to data/uploads/ for fraud audit trail.
"""

import os, sys, shutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage, HumanMessage
from config import get_vision_llm

os.makedirs("data/uploads", exist_ok=True)


def document_agent_node(state: dict) -> dict:
    """Processes an uploaded document image using Gemini Vision."""
    print("📄 [DOCUMENT AGENT] Processing uploaded document...")

    doc_path = state.get("documents", {}).get("salary_slip_path", "")

    if not doc_path or not os.path.exists(doc_path):
        return {
            "documents": {**state.get("documents", {}), "verified": False},
            "messages": [AIMessage(content="📄 Please upload your salary slip or ID document to continue.")]
        }

    # Save a permanent copy for audit trail
    audit_filename = f"audit_{os.path.basename(doc_path)}"
    audit_path = os.path.join("data", "uploads", audit_filename)
    shutil.copy2(doc_path, audit_path)
    print(f"  📁 Audit copy saved to: {audit_path}")

    # Read image and send to Gemini Vision
    import base64
    with open(doc_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    vision_llm = get_vision_llm()

    prompt = """Analyze this document image carefully. Extract the following information as JSON:
{
    "document_type": "PAN Card / Aadhaar Card / Salary Slip / Unknown",
    "name_extracted": "Full name visible on the document",
    "salary_extracted": 0,  // Monthly salary if this is a salary slip, else 0
    "document_number": "PAN/Aadhaar number if visible",
    "confidence": 0.95,  // Your confidence in the extraction accuracy (0.0 to 1.0)
    "tampered": false  // Set true if the document looks edited or suspicious
}
Only return the JSON, no other text."""

    try:
        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ])
        response = vision_llm.invoke([message])

        # Parse the response
        import json, re
        text = response.content
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            extracted = json.loads(json_match.group(0))
        else:
            extracted = {"name_extracted": "Unknown", "salary_extracted": 0, "confidence": 0.5, "tampered": False}

        doc_data = {
            **state.get("documents", {}),
            "verified": True,
            "name_extracted": extracted.get("name_extracted", "Unknown"),
            "salary_extracted": float(extracted.get("salary_extracted", 0)),
            "confidence": float(extracted.get("confidence", 0.5)),
            "tampered": extracted.get("tampered", False),
            "document_type": extracted.get("document_type", "Unknown"),
            "audit_path": audit_path
        }

        tamper_warning = " ⚠️ **Document appears tampered!**" if extracted.get("tampered") else ""
        msg = (
            f"📄 **Document Processed Successfully**{tamper_warning}\n"
            f"- Type: {doc_data['document_type']}\n"
            f"- Name: {doc_data['name_extracted']}\n"
            f"- Salary: ₹{doc_data['salary_extracted']:,.0f}\n"
            f"- Confidence: {doc_data['confidence']:.0%}"
        )

        return {"documents": doc_data, "messages": [AIMessage(content=msg)]}

    except Exception as e:
        return {
            "documents": {**state.get("documents", {}), "verified": False},
            "messages": [AIMessage(content=f"❌ Document processing failed: {str(e)}\nPlease try uploading again.")]
        }
