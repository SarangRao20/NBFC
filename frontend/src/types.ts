export interface AppState {
  sessionId: string | null;
  customerName: string;
  requestedAmount: number;
  roi: number;
  tenure: number;
  emi: number;
  creditScore: number;
  preApprovedLimit: number;
  underwritingStatus: 'Pending Evaluation' | 'Soft-Rejected' | 'Approved' | 'Reject';
  activeAgent: string | null;
  thinkingAgents: string[];
  needsDocument: boolean;
  requiredDocuments: string[];
  documents: {
    pan: 'pending' | 'verified';
    bankStatement: 'pending' | 'verified';
  };
  actionLog: string[];
  options: string[];
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

export interface SessionSummary {
  session_id: string;
  created_at: string;
  current_phase: string;
  loan_amount?: number;
  decision?: string;
}

export type MessageType = 'text' | 'thinking' | 'sanction_letter' | 'emi_slider' | 'agent_steps' | 'options';


export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'system';
  type: MessageType;
  content: string;
  options?: string[];
  timestamp: Date;
}
