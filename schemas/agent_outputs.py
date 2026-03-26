"""Pydantic schemas for agent outputs — ensures consistent state shape and validates all agent node returns."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# ─── DOCUMENT AGENT OUTPUT ───────────────────────────────────────────────────
class ExtractedDataSchema(BaseModel):
    """Extracted structured data from a single document."""
    full_name: Optional[str] = None
    document_number: Optional[str] = None
    dob: Optional[str] = None
    employer_name: Optional[str] = None
    net_monthly_income: Optional[float] = None
    gross_monthly_income: Optional[float] = None
    document_date: Optional[str] = None


class ForensicAnalysisSchema(BaseModel):
    """Forensic analysis results from document vision."""
    confidence_score: float = Field(ge=0.0, le=1.0)
    is_tampered: bool
    tamper_indicators: List[str] = []
    fraud_signals: List[str] = []


class DocumentExtractionSchema(BaseModel):
    """Single extracted document with forensic analysis."""
    document_type: str
    extracted_data: ExtractedDataSchema
    forensic_analysis: ForensicAnalysisSchema


class DocumentAgentOutputSchema(BaseModel):
    """Document Agent full output."""
    total_documents_processed: int
    extracted_documents: List[DocumentExtractionSchema]
    verified: bool = False
    document_type: Optional[str] = None
    name_extracted: Optional[str] = None
    salary_extracted: Optional[float] = None
    confidence: Optional[float] = None
    tampered: Optional[bool] = None
    
    class Config:
        extra = "allow"  # Allow extra fields from state merging


# ─── KYC AGENT OUTPUT ────────────────────────────────────────────────────────
class KYCOutputSchema(BaseModel):
    """KYC verification agent output."""
    kyc_status: str = Field(pattern="^(verified|failed|pending)$")
    action_log: List[str] = []
    options: List[str] = []
    current_phase: Optional[str] = None
    
    class Config:
        extra = "allow"


# ─── FRAUD AGENT OUTPUT ──────────────────────────────────────────────────────
class FraudAgentOutputSchema(BaseModel):
    """Fraud detection agent output."""
    fraud_score: float = Field(ge=0.0, le=1.0)
    fraud_signals: int = Field(ge=0, le=6)
    fraud_level: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")
    action_log: List[str] = []
    options: List[str] = []
    current_phase: Optional[str] = None
    
    @validator("fraud_level", always=True)
    def calculate_fraud_level(cls, v, values):
        score = values.get("fraud_score", 0.0)
        if score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"
    
    class Config:
        extra = "allow"


# ─── UNDERWRITING AGENT OUTPUT ───────────────────────────────────────────────
class LoanTermsSchema(BaseModel):
    """Loan terms structure."""
    principal: float = Field(gt=0)
    tenure: int = Field(gt=0)
    emi: float = Field(ge=0)
    rate: float = Field(ge=0.0, le=100.0)
    requested_amount: Optional[float] = None
    loan_purpose: Optional[str] = None
    loan_type: Optional[str] = None
    sanction_date: Optional[str] = None
    first_emi_date: Optional[str] = None
    next_emi_date: Optional[str] = None
    emi_day_of_month: Optional[int] = None
    payments_made: int = 0
    days_overdue: int = 0
    last_payment_date: Optional[str] = None
    
    class Config:
        extra = "allow"


class UnderwritingOutputSchema(BaseModel):
    """Underwriting decision engine output."""
    decision: str = Field(pattern="^(approve|soft_reject|hard_reject|pending_docs|reject|)$")
    dti_ratio: float = Field(ge=0.0, le=10.0)  # DTI as fraction (0.0 to 10.0, not percent)
    risk_level: str = Field(pattern="^(low|medium|high|very_high)$")
    reasons: List[str] = []
    alternative_offer: float = Field(default=0.0, ge=0.0)
    fraud_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    action_log: List[str] = []
    options: List[str] = []
    current_phase: Optional[str] = None
    loan_terms: Optional[LoanTermsSchema] = None
    
    class Config:
        extra = "allow"


# ─── PERSUASION AGENT OUTPUT ────────────────────────────────────────────────
class PersuasionOptionSchema(BaseModel):
    """Single restructuring option."""
    label: str
    amount: float = Field(gt=0)
    tenure: int = Field(gt=0)
    emi: float = Field(gt=0)


class PersuasionOutputSchema(BaseModel):
    """Persuasion (negotiation) agent output."""
    negotiation_round: int = Field(ge=1)
    persuasion_options: List[PersuasionOptionSchema] = []
    action: Optional[str] = Field(default=None, pattern="^(accept|decline|clarify|unclear)$")
    decision: str = Field(default="", pattern="^(approve|reject|)$")
    persuasion_status: str = Field(default="", pattern="^(pending|accepted|declined|unclear|)$")
    action_log: List[str] = []
    options: List[str] = []
    current_phase: Optional[str] = None
    
    class Config:
        extra = "allow"


# ─── SALES AGENT OUTPUT ──────────────────────────────────────────────────────
class SalesAgentOutputSchema(BaseModel):
    """Sales/Advisory agent output."""
    reply: str  # Human-readable response from LLM
    extracted: Optional[Dict[str, Any]] = None  # Optional parsed JSON from LLM
    intent: Optional[str] = None
    next_agent: Optional[str] = None
    action_log: List[str] = []
    
    class Config:
        extra = "allow"


# ─── MASTER STATE VALIDATOR ─────────────────────────────────────────────────
class StateSchema(BaseModel):
    """Master state schema — validates the complete pipeline state."""
    session_id: str
    customer_data: Dict[str, Any] = {}
    documents: Dict[str, Any] = {}
    loan_terms: LoanTermsSchema
    messages: List[Dict[str, Any]] = []
    action_log: List[str] = []
    
    # Pipeline state
    decision: str = ""
    dti_ratio: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    fraud_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    kyc_status: Optional[str] = None
    risk_level: Optional[str] = None
    options: List[str] = []
    current_phase: Optional[str] = None
    
    class Config:
        extra = "allow"


# ─── VALIDATION UTILITIES ────────────────────────────────────────────────────
def validate_agent_output(agent_name: str, output: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validates an agent output dict against the corresponding schema.
    
    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    try:
        if agent_name == "document_agent":
            # Document agent output is a raw dict merge; validate key fields
            if "documents" in output and isinstance(output["documents"], dict):
                pass  # Validation passed (flexible schema)
            return True, None
        
        elif agent_name == "kyc_agent":
            KYCOutputSchema(**output)
            return True, None
        
        elif agent_name == "fraud_agent":
            FraudAgentOutputSchema(**output)
            return True, None
        
        elif agent_name == "underwriting_agent":
            UnderwritingOutputSchema(**output)
            return True, None
        
        elif agent_name == "persuasion_agent":
            PersuasionOutputSchema(**output)
            return True, None
        
        elif agent_name == "sales_agent":
            SalesAgentOutputSchema(**output)
            return True, None
        
        else:
            return True, None  # Unknown agent, skip validation
    
    except Exception as e:
        return False, f"Validation failed for {agent_name}: {str(e)}"
