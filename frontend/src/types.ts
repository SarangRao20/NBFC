export interface AppState {
  customerName: string;
  requestedAmount: number;
  roi: number;
  tenure: number;
  emi: number;
  creditScore: number;
  preApprovedLimit: number;
  underwritingStatus: 'Pending Evaluation' | 'Soft-Rejected' | 'Approved' | 'Reject';
  activeAgent: string | null;
  needsDocument: boolean;
  documents: {
    pan: 'pending' | 'verified';
    bankStatement: 'pending' | 'verified';
  };
}

export type MessageType = 'text' | 'thinking' | 'sanction_letter' | 'emi_slider' | 'agent_steps';


export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'system';
  type: MessageType;
  content: string;
  timestamp: Date;
}
