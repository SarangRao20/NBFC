export interface AppState {
  requestedAmount: number;
  roi: number;
  tenure: number;
  emi: number;
  underwritingStatus: 'Pending Evaluation' | 'Soft-Rejected' | 'Approved';
  activeAgent: string | null;
  needsDocument: boolean;
  documents: {
    pan: 'pending' | 'verified';
    bankStatement: 'pending' | 'verified';
  };
}

export type MessageType = 'text' | 'thinking' | 'sanction_letter' | 'emi_slider';


export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'system';
  type: MessageType;
  content: string;
  timestamp: Date;
}
