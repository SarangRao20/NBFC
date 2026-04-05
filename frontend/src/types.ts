export interface AppState {
  sessionId: string | null;
  customerName: string;
  requestedAmount: number;
  roi: number;
  tenure: number;
  emi: number;
  creditScore: number;
  preApprovedLimit: number;
  phone?: string;
  salary: number;
  underwritingStatus: 'Pending Evaluation' | 'Soft-Rejected' | 'Approved' | 'Reject';
  activeAgent: string | null;
  thinkingAgents: string[];
  needsDocument: boolean;
  requiredDocuments: string[];
  uploadedDocNames?: string[];
  documents: {
    pan: 'pending' | 'verified';
    bankStatement: 'pending' | 'verified';
  };
  documents_uploaded: boolean;
  eligible_offers: any[];
  actionLog: string[];
  options: string[];
  loan_terms?: {
    principal: number;
    tenure: number;
    rate: number;
    emi: number;
    payments_made?: number;
    remaining_balance?: number;
    next_emi_date?: string;
  };
  pastLoans?: Array<{
    amount: number;
    type: string;
    decision: string;
    sanction_letter?: string;
    date: string;
  }>;
  pastRecords?: string;
  pastSessions?: SessionSummary[];
  disbursement_step?: "pending" | "ui_paused" | "completed";
  net_disbursement_amount?: number;
  kfs_signed?: boolean;
  enach_setup?: boolean;
  rejectionType?: "emi_affordability" | "ltv_limit" | "exposure_limit" | "cashflow_insufficient" | "general_risk" | null;
  negotiationApproach?: "tenure_adjustment" | "reduced_principal" | null;
}

export interface UserData {
  name: string;
  phone: string;
  dob: string;
  profession: string;
  address: string;
  email: string;
  password: string;
  city?: string;
  salary?: number;
  credit_score?: number;
  pre_approved_limit?: number;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: UserData | null;
  isLoading: boolean;
  error: string | null;
}

export interface SessionSummary {
  session_id: string;
  created_at: string;
  current_phase: string;
  loan_amount?: number;
  loan_type?: string;
  decision?: string;
  display_status?: 'approved' | 'in_process' | 'rejected' | 'pending' | string;
}

export type MessageType = 'text' | 'thinking' | 'sanction_letter' | 'rejection_letter' | 'emi_slider' | 'agent_steps' | 'options';


export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'system';
  type: MessageType;
  content: string;
  options?: string[];
  timestamp: Date;
}

// ============================================================================
// NBFC Dashboard Types
// ============================================================================

export type NBFCView = 'overview' | 'applications' | 'products' | 'performance' | 'disbursements' | 'risk';

export interface NBFCDashboardProps {
  nbfcId?: string;
  nbfcName?: string;
  userRole?: 'manager' | 'underwriter' | 'viewer';
  onLogout?: () => void;
}

export interface LoanApplication {
  id: string;
  customer_name: string;
  customer_phone: string;
  amount_requested: number;
  tenure_months: number;
  purpose: string;
  credit_score: number;
  monthly_income: number;
  status: 'pending' | 'under_review' | 'approved' | 'rejected' | 'disbursed';
  applied_date: string;
  risk_score?: number;
  documents_verified: boolean;
}

export interface LoanProduct {
  id: string;
  name: string;
  type: 'personal' | 'business' | 'home' | 'vehicle' | 'education';
  min_amount: number;
  max_amount: number;
  min_tenure: number;
  max_tenure: number;
  interest_rate_min: number;
  interest_rate_max: number;
  processing_fee_percent: number;
  prepayment_charges: number;
  is_active: boolean;
  created_at: string;
}

export interface DisbursementRecord {
  id: string;
  application_id: string;
  customer_name: string;
  amount_disbursed: number;
  disbursement_date: string;
  emi_amount: number;
  total_emis: number;
  emis_paid: number;
  emis_pending: number;
  next_emi_date: string;
  status: 'active' | 'closed' | 'defaulted';
}

export interface NBFCStats {
  total_applications: number;
  pending_review: number;
  approved_count: number;
  rejected_count: number;
  disbursed_count: number;
  total_disbursed_amount: number;
  total_outstanding: number;
  total_emis_collected: number;
  avg_loan_amount: number;
  avg_interest_rate: number;
  conversion_rate: number;
}
