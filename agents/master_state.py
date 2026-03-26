import operator
from typing import Annotated, Sequence, TypedDict, Any, List, Dict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# Custom message reducer that filters out dict messages
def safe_add_messages(left: Sequence[BaseMessage], right: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """Add messages while filtering out any dict messages."""
    # Filter out any dict messages from both sides
    filtered_left = [m for m in left if not isinstance(m, dict)]
    filtered_right = [m for m in right if not isinstance(m, dict)]
    return add_messages(filtered_left, filtered_right)

class LoanTerms(TypedDict, total=False):
    requested_amount: float     # Original amount user asked for
    principal: float
    rate: float
    tenure: int
    emi: float
    loan_type: str
    # ✅ NEW: EMI & Payment Tracking
    sanction_date: str          # When loan was approved (YYYY-MM-DD)
    first_emi_date: str         # First EMI due date (YYYY-MM-DD)
    next_emi_date: str          # Current EMI due date
    emi_day_of_month: int       # Day of month for recurring EMI (1-28)
    payments_made: int          # Count of successful EMI payments
    days_overdue: int           # Days past due (for credit score impact)
    last_payment_date: Optional[str]  # Date of last successful payment

class CustomerData(TypedDict, total=False):
    name: str
    email: str
    phone: str
    dob: str
    city: str
    salary: float
    credit_score: int
    pre_approved_limit: float
    existing_emi_total: float
    # ✅ NEW: Customer Source Tracking
    is_new_customer: bool             # True if first application
    score_source: str                 # "cibil", "system_default", "crm_returning"
    created_at: str                   # When customer profile created
    last_payment_date: Optional[str]  # Last EMI payment date
    payment_history: List[Dict]       # [{date, amount, status}]
    score_degradation_due_to_overdue: int  # Points lost due to late payments

class DocumentData(TypedDict, total=False):
    salary_slip_path: str
    salary_extracted: float
    verified: bool
    confidence: float
    ocr_error: str

class MasterState(TypedDict):
    """The global session state for the 9-Agent pipeline — DETERMINISTIC + PERSISTENT."""
    
    # ─── Chat & Messages ───────────────────────────────────────────────────────
    messages: Annotated[Sequence[BaseMessage], safe_add_messages]
    
    # ─── Session Metadata ───────────────────────────────────────────────────────
    customer_id: str
    session_id: str
    current_phase: str  # "registration", "intent", "sales", "documents", "kyc", "fraud", "underwriting", "persuasion", "sanction", "advisor"
    
    # ─── Customer Profile (Minimal for NBFC) ───────────────────────────────────
    customer_data: CustomerData  # name, email, phone, dob, city, salary
    profile_complete: bool  # True if all 6 fields present
    is_authenticated: bool
    
    # ─── User Intent ───────────────────────────────────────────────────────────
    intent: str  # "none", "loan", "kyc", "advice"
    pending_question: Optional[str]
    
    # ─── Loan Terms Negotiation ────────────────────────────────────────────────
    loan_terms: LoanTerms
    loan_confirmed: bool  # ✅ Added: True when user accepts final terms
    
    # ─── Loan Comparison & Selection (Phase 5) ──────────────────────────────────
    selected_lender_id: Optional[str]  # ✅ NEW: e.g., "bank_a", "nbfc_x"
    selected_lender_name: Optional[str]  # ✅ NEW: e.g., "HDFC Bank"
    selected_interest_rate: Optional[float]  # ✅ NEW: Selected loan's interest rate
    comparison_result: Optional[Dict]  # ✅ NEW: Full comparison response from engine
    
    # ─── Document Processing & Tracking ────────────────────────────────────────
    documents: DocumentData
    document_paths: Dict[str, str]  # { "pan": "/path/to/pan.pdf", "salary_slip": "..." }
    required_documents: List[str]  # ✅ NEW: Dynamic list from agent
    documents_uploaded: bool
    
    # ─── Risk & Fraud Analysis ─────────────────────────────────────────────────
    fraud_score: float  # -1 = not checked, 0-100 = score
    dti_ratio: float
    esign_completed: bool # ✅ Added: True after e-signature
    kyc_status: str  # "pending", "verified", "rejected"
    risk_level: str  # "low", "medium", "high"
    sanction_pdf: str # ✅ Added: Move from below to ensure consistent schema
    is_signed: bool
    
    # ─── Underwriting Decision ─────────────────────────────────────────────────
    decision: str  # "", "approve", "soft_reject", "hard_reject"
    reasons: List[str]
    alternative_offer: float  # for soft_reject negotiation
    
    # ─── Sanction & Final Output ───────────────────────────────────────────────
    sanction_pdf: str  # path to generated PDF
    is_signed: bool
    
    # ─── Persuasion/Negotiation State ─────────────────────────────────────────
    negotiation_round: int
    persuasion_options: List[Dict]
    
    # ─── Routing & Logging ─────────────────────────────────────────────────────
    next_agent: str
    routing_reasoning: str
    action_log: List[str]  # human-readable step log for UI + advisor
    options: List[str]  # interaction buttons

