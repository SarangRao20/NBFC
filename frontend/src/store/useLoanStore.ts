import { create } from 'zustand';

export type AppState = 
  | 'UNAUTHENTICATED'
  | 'AUTHENTICATED' 
  | 'PROFILE_COMPLETION'
  | 'ONBOARDING'
  | 'DOCUMENT_COLLECTION'
  | 'DECISION_READY'
  | 'ACTIVE_LOAN';

export type DashboardView = 'DASHBOARD' | 'APPLICATION' | 'ACTIVE_LOANS' | 'ADVISOR' | 'PROFILE';

export interface UserProfile {
  name: string;
  email: string;
  picture: string;
  phone?: string;
  salary?: number;
  city?: string;
  creditScore?: number;
  pan?: string;
  aadhaar?: string;
  preApprovedLimit?: number;
}

export interface LoanDetails {
  requestedAmount: number;
  tenureMonths: number;
  purpose?: string;
  sanctionedAmount?: number;
  interestRate?: number;
  monthlyEmi?: number;
}

export interface Document {
  id: string;
  type: 'PAN' | 'AADHAAR';
  status: 'UPLOADED' | 'VERIFIED' | 'REJECTED';
  extractedData?: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  component?: 'PROFILE_FORM' | 'ONBOARDING_FORM' | 'KYC_DROPZONE' | 'LENDER_CAROUSEL' | 'ACTIVE_CONTRACT' | 'SHAP_EXPLANATION';
  componentProps?: Record<string, any>;
}

interface LoanStore {
  // New Layout State
  currentView: DashboardView;
  setView: (view: DashboardView) => void;
  
  // API & Agent State
  sessionId: string | null;
  setSessionId: (id: string) => void;
  isAgentActive: boolean;
  agentLogs: string[];
  setAgentActive: (active: boolean) => void;
  addAgentLog: (log: string) => void;
  clearAgentLogs: () => void;

  currentState: AppState;
  user: UserProfile | null;
  loanDetails: LoanDetails;
  documents: Document[];
  chatHistory: ChatMessage[];
  
  // Actions
  setState: (state: AppState) => void;
  setUser: (user: UserProfile) => void;
  updateLoanDetails: (details: Partial<LoanDetails>) => void;
  addDocument: (doc: Document) => void;
  updateDocument: (id: string, updates: Partial<Document>) => void;
  addChatMessage: (msg: ChatMessage) => void;
  clearSession: () => void;
}

export const useLoanStore = create<LoanStore>((set) => ({
  currentView: 'DASHBOARD',
  setView: (view) => set({ currentView: view }),

  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),
  isAgentActive: false,
  agentLogs: [],
  setAgentActive: (active) => set({ isAgentActive: active }),
  addAgentLog: (log) => set((state) => ({ agentLogs: [...state.agentLogs, log] })),
  clearAgentLogs: () => set({ agentLogs: [] }),

  currentState: 'UNAUTHENTICATED',
  user: null,
  loanDetails: {
    requestedAmount: 500000,
    tenureMonths: 36,
  },
  documents: [],
  chatHistory: [],

  setState: (state) => set({ currentState: state }),
  
  setUser: (user) => set({ user, currentState: 'AUTHENTICATED' }),
  
  updateLoanDetails: (details) => 
    set((state) => ({ 
      loanDetails: { ...state.loanDetails, ...details } 
    })),
    
  addDocument: (doc) => 
    set((state) => ({ 
      documents: [...state.documents, doc] 
    })),
    
  updateDocument: (id, updates) =>
    set((state) => ({
      documents: state.documents.map(d => d.id === id ? { ...d, ...updates } : d)
    })),
    
  addChatMessage: (msg) =>
    set((state) => ({
      chatHistory: [...state.chatHistory, msg]
    })),
    
  clearSession: () => set({
    currentView: 'DASHBOARD',
    sessionId: null,
    isAgentActive: false,
    agentLogs: [],
    currentState: 'UNAUTHENTICATED',
    user: null,
    loanDetails: { requestedAmount: 500000, tenureMonths: 36 },
    documents: [],
    chatHistory: []
  })
}));
