import enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DocumentType(str, enum.Enum):
    PAN_CARD = "pan_card"
    AADHAAR_CARD = "aadhaar_card"
    SALARY_SLIP = "salary_slip"
    UNKNOWN = "unknown"

class ExtractionStatus(str, enum.Enum):
    SUCCESS = "success"
    POOR_QUALITY = "poor_quality"
    INCORRECT_FORMAT = "incorrect_format"
    DATA_MISMATCH = "data_mismatch"
    TAMPERED = "tampered"

class ExtractedDocument(BaseModel):
    """Schema for extracted document data using Vision LLM."""
    doc_type: DocumentType = Field(..., description="The type of document detected.")
    full_name: Optional[str] = Field(None, description="Full name as it appears on the document.")
    id_number: Optional[str] = Field(None, description="The unique ID number (PAN, Aadhaar, etc.).")
    date_of_birth: Optional[str] = Field(None, description="DOB if available.")
    address: Optional[str] = Field(None, description="Address if available (usually Aadhaar).")
    monthly_income: Optional[float] = Field(None, description="Extracted salary if it's a salary slip.")
    is_blurry: bool = Field(False, description="Whether the image is too blurry to read.")
    is_tampered_hint: bool = Field(False, description="Any visual signs of editing/tampering.")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in the extraction.")

class VerificationState(BaseModel):
    """LangGraph State for the Verification Workflow."""
    # Input data from Registration/User
    user_provided_name: str
    user_provided_phone: str
    
    # Document being processed
    current_doc_path: Optional[str] = None
    
    # Verification Result
    verified_docs: Dict[DocumentType, ExtractedDocument] = {}
    verification_errors: List[str] = []
    status: str = "idle" # idle, processing, verified, failed
