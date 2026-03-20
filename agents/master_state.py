import operator
from typing import Annotated, Sequence, TypedDict, Any, List, Dict, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class LoanTerms(TypedDict, total=False):
    principal: float
    rate: float
    tenure: int
    emi: float

class CustomerData(TypedDict, total=False):
    name: str
    phone: str
    city: str
    salary: float
    score: int
    limit: float

class DocumentData(TypedDict, total=False):
    salary_slip_path: str
    salary_extracted: float
    verified: bool
    confidence: float

class MasterState(TypedDict):
    """The global session state for the 9-Agent pipeline."""
    # Langgraph requires this specific annotation to maintain Chat History across all nodes
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Customer DB Context
    customer_id: str
    session_id: str
    customer_data: CustomerData
    
    # Active Loan Negotiation
    loan_terms: LoanTerms
    
    # Uploads & Extraction
    documents: DocumentData
    
    # Risk Metrics
    fraud_score: float
    dti_ratio: float
    kyc_status: str
    
    # Final Decision Output
    decision: str
    sanction_pdf: str
    
    # Underwriting Enrichment
    risk_level: str
    alternative_offer: float
    reasons: List[str]
    
    # Persuasion Loop State
    negotiation_round: int
    persuasion_options: List[Dict]
    
    # Routing Tracker: which agent holds the baton currently
    next_agent: str
