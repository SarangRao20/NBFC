export interface AppState {
  requestedAmount: number;
  roi: number;
  tenure: number;
  emi: number;
  underwritingStatus: 'Pending Evaluation' | 'Soft-Rejected' | 'Approved';
  documents: {
    pan: 'pending' | 'verified';
    bankStatement: 'pending' | 'verified';
  };
}

export type MessageType = 'text' | 'thinking' | 'sanction_letter';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent' | 'system';
  type: MessageType;
  content: string;
  timestamp: Date;
}
