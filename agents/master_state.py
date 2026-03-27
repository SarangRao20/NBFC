import operator
from typing import Annotated, Sequence, TypedDict, Any, List, Dict, Optional, cast
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# Custom message reducer that filters out dict messages
def safe_add_messages(left: Sequence[BaseMessage], right: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """Add messages while filtering out any dict messages."""
    # Keep only actual BaseMessage instances from both sides (drop dicts/strings)
    # Use `tuple` (a `Sequence`) because `Sequence` is covariant whereas `list` is not.
    filtered_left: Sequence[BaseMessage] = tuple(m for m in left if isinstance(m, BaseMessage))
    filtered_right: Sequence[BaseMessage] = tuple(m for m in right if isinstance(m, BaseMessage))

    # `add_messages` may accept different message-like types; cast its result to a
    # generic sequence for safe runtime filtering below so we return only BaseMessage
    # Convert to list since `add_messages` expects Messages union which includes list[...] but not tuple[BaseMessage, ...]
    combined = cast(Sequence[Any], add_messages(list(filtered_left), list(filtered_right)))

    # Filter the combined result to only BaseMessage instances and return as a tuple
    return tuple(m for m in combined if isinstance(m, BaseMessage))

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
    current_phase: str  
    
    # ─── Customer Profile (Minimal for NBFC) ───────────────────────────────────
    customer_data: CustomerData  
    profile_complete: bool  
    is_authenticated: bool
    
    # ─── User Intent ───────────────────────────────────────────────────────────
    intent: str  
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
    document_paths: Dict[str, str]  
    required_documents: List[str]  
    documents_uploaded: bool
    
    # ─── Risk & Fraud Analysis ─────────────────────────────────────────────────
    fraud_score: float  
    dti_ratio: float
    esign_completed: bool 
    kyc_status: str  
    risk_level: str  
    
    # ─── Underwriting Decision ─────────────────────────────────────────────────
    decision: str  # "", "approve", "soft_reject", "hard_reject"
    reasons: List[str]
    alternative_offer: float  
    
    # ─── Sanction & Final Output ───────────────────────────────────────────────
    sanction_pdf: str  # path to generated PDF
    is_signed: bool
    
    # ─── Persuasion/Negotiation State (Soft Reject Loop) ───────────────────────
    negotiation_round: int
    persuasion_options: List[Dict]
    user_accepted_counter_offer: bool  # ✅ NEW: Tracks if user accepted the soft-reject offer
    
    # ─── 5-Step Disbursement & Compliance Flags (Hybrid Approach) ──────────────
    net_disbursement_amount: float     # ✅ NEW: Calculated post-sanction amount
    kfs_signed: bool                   # ✅ NEW: UI flag for Key Fact Statement
    enach_setup: bool                  # ✅ NEW: UI flag for Autopay
    cooling_off_active: bool           # ✅ NEW: Tracks 1-day RBI cooling off period
    disbursement_step: str             # ✅ NEW: "pending", "ui_paused", "completed"
    
    # ─── Routing & Logging ─────────────────────────────────────────────────────
    next_agent: str
    previous_agent: Optional[str]  # ✅ Added: Internal tracker to prevent loops
    routing_reasoning: str
    action_log: List[str]  # human-readable step log for UI + advisor
    options: List[str]  # interaction buttons
    eligible_offers: List[Dict] # ✅ NEW: NBFC offers for selection
    sales_output: Dict # ✅ NEW: Structured sales data for UI

