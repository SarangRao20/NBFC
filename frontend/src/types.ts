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
