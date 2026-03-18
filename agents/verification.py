import os
import sys

# Append parent dir for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict, Dict, Any, List
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END, START

# Project Configs and Utils
from config import get_vision_llm, get_chat_llm
from utils.document_helpers import encode_image
from schema import DocumentType, ExtractedDocument, ExtractionStatus

# --- Define State ---

class VerificationState(TypedDict):
    """The State Dictionary for the Verification Agent graph."""
    user_provided_name: str
    user_provided_phone: str
    current_doc_path: str
    verified_docs: Dict[str, dict] # E.g., {"pan_card": ExtractedDocument(...)}
    verification_errors: List[str]
    status: str
    doc_assist_messages: List[str]
    extracted_temp: Dict[str, Any]

# --- Nodes ---

def extract_document_node(state: VerificationState) -> dict:
    """Uses a Vision LLM to parse image fields securely."""
    print("--- VERIFICATION AGENT: EXTRACTING DOCUMENT DATA ---")
    doc_path = state.get("current_doc_path")
    
    if not doc_path or not os.path.exists(doc_path):
        return {"verification_errors": ["File not found at path."], "status": "failed"}

    # Base64 the image
    base64_image = encode_image(doc_path)
    
    vision_llm = get_vision_llm()
    # Enforce Pydantic schema structure
    vision_extractor = vision_llm.with_structured_output(ExtractedDocument)
    
    prompt = """
    You are an expert fraud detection and document verification AI for an NBFC.
    Analyze the uploaded document image.
    1. Identify if it is a PAN Card, Aadhaar Card, or Salary Slip. If none, mark as UNKNOWN.
    2. Extract the Name, ID Number, Date of Birth, Address, and Salary (if applicable).
    3. Determine if the image is too blurry to read accurately (is_blurry = true).
    4. Spot glaring anomalies that suggest digital tampering or Photoshopping (is_tampered_hint = true).
    5. Provide a confidence score (0.0 to 1.0) of your overall extraction accuracy.
    """
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    )
    
    try:
        # Calls the OpenRouter Vision Endpoint
        result: ExtractedDocument = vision_extractor.invoke([message])
        return {"extracted_temp": result.dict()} 
    except Exception as e:
        return {"verification_errors": [f"LLM Extraction failed: {str(e)}"], "status": "failed"}


def evaluate_document_node(state: VerificationState) -> dict:
    """Takes the Extracted JSON from the previous node and runs strictly coded rules against it."""
    print("--- VERIFICATION AGENT: EVALUATING DATA AGAINST RULES ---")
    errors = []
    
    extracted_data = state.get("extracted_temp")
    if not extracted_data:
        return {"status": "failed", "verification_errors": state.get("verification_errors", ["No data was extracted."])}
        
    extracted = ExtractedDocument(**extracted_data)
    
    # Validation Rules
    if extracted.doc_type == DocumentType.UNKNOWN:
        errors.append("Unrecognized document template. Provide a clear PAN, Aadhaar, or Salary Slip.")
        
    if extracted.is_blurry or extracted.confidence_score < 0.7:
        errors.append("Document image is too blurry or dark. Ensure good lighting and readable text.")
        
    if extracted.is_tampered_hint:
        errors.append("Digital manipulation detected. Rejecting document.")
        return {"status": "tampered_rejected", "verification_errors": errors}

    # Cross-reference rule: Name Matching
    if extracted.full_name and state.get("user_provided_name"):
        user_name = state["user_provided_name"].lower()
        doc_name = extracted.full_name.lower()
        # Basic check to see if names share parts (e.g. "Sarang Rao" in "Sarang M Rao")
        if not set(user_name.split()).intersection(set(doc_name.split())):
            errors.append(f"Name mismatch: Registered as '{state['user_provided_name']}' but document says '{extracted.full_name}'.")

    # Routing Decisions
    if errors:
        all_errors = state.get("verification_errors", []) + errors
        return {"status": "formatting_or_quality_error", "verification_errors": all_errors}
    
    # State update on success
    verified = state.get("verified_docs", {})
    verified[extracted.doc_type.value] = extracted.dict()
    
    return {
        "status": "success",
        "verified_docs": verified,
        "verification_errors": []
    }


def document_assistance_node(state: VerificationState) -> dict:
    """When a document fails, generates personalized user instructions to fix the error."""
    print("--- VERIFICATION AGENT: RUNNING DOCUMENT ASSISTANCE FALLBACK ---")
    errors = state.get("verification_errors", [])
    
    chat_llm = get_chat_llm()
    
    prompt = f"""
    You are a friendly Customer Support AI helping the user upload their documents.
    Their upload just failed our system checks for technical reasons: {errors}
    
    Write a short, non-tactless, easy-to-understand instruction telling the user exactly what to fix before they re-upload. 
    (E.g., "Please bring the camera closer so the edges of the PAN card fit..." or "The name doesn't seem to match...")
    """
    
    msg = chat_llm.invoke(prompt)
    current_assist_msgs = state.get("doc_assist_messages", [])
    current_assist_msgs.append(str(msg.content))
    
    return {"doc_assist_messages": current_assist_msgs}


# --- Dynamic Router ---

def route_evaluation(state: VerificationState) -> str:
    status = state.get("status")
    if status == "success":
        return END
    elif status == "formatting_or_quality_error":
        return "doc_assistance"
    elif status == "tampered_rejected":
        return END # Terminal state
    return END

# --- Graph Creation ---

def build_verification_agent():
    workflow = StateGraph(VerificationState)

    workflow.add_node("extract_document", extract_document_node)
    workflow.add_node("evaluate_document", evaluate_document_node)
    workflow.add_node("doc_assistance", document_assistance_node)

    workflow.add_edge(START, "extract_document")
    workflow.add_edge("extract_document", "evaluate_document")
    workflow.add_conditional_edges(
        "evaluate_document",
        route_evaluation,
        {
            END: END,
            "doc_assistance": "doc_assistance"
        }
    )

    return workflow.compile()
