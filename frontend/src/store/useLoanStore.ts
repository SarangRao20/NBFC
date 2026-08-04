import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type AppState = 
  | 'UNAUTHENTICATED'
  | 'AUTHENTICATED' 
  | 'PROFILE_COMPLETION'
  | 'ONBOARDING'
  | 'DOCUMENT_COLLECTION'
  | 'DECISION_READY'
  | 'ACTIVE_LOAN';

export type DashboardView = 'DASHBOARD' | 'APPLICATION' | 'ACTIVE_LOANS' | 'ADVISOR' | 'PROFILE' | 'DOCS';

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
  role: 'user' | 'assistant';
  content: string;
  component?: string;
  timestamp: number;
  graphTrace?: string[];
  pdfDownloadUrl?: string;
  pdfLabel?: string;
  showShapPill?: boolean;
  allLenderRules?: any[];
  showRulesButton?: boolean;
  uiTrigger?: 'INITIAL_OFFERS' | 'REJECTION' | 'FINAL_LENDER';
  disbursementDetails?: any;
  decision?: string;
  reasons?: string[];
}

interface LoanStore {
  currentView: DashboardView;
  sessionId: string | null;
  isAgentActive: boolean;
  agentLogs: string[];
  currentState: AppState;
  user: UserProfile | null;
  loanDetails: LoanDetails;
  documents: Document[];
  chatHistory: ChatMessage[];
  setView: (view: DashboardView) => void;
  setSessionId: (id: string) => void;
  setAgentActive: (active: boolean) => void;
  addAgentLog: (log: string) => void;
  clearAgentLogs: () => void;
  setState: (state: AppState) => void;
  setUser: (user: UserProfile) => void;
  updateLoanDetails: (details: Partial<LoanDetails>) => void;
  addDocument: (doc: Document) => void;
  updateDocument: (id: string, updates: Partial<Document>) => void;
  addChatMessage: (msg: ChatMessage) => void;
  clearSession: () => void;
}

export const useLoanStore = create<LoanStore>()(
  persist(
    (set) => ({
      currentView: 'DASHBOARD',
      sessionId: null,
      isAgentActive: false,
      agentLogs: [],
      currentState: 'UNAUTHENTICATED',
      user: null,
      loanDetails: { requestedAmount: 500000, tenureMonths: 36 },
      documents: [],
      chatHistory: [],

      setView: (view) => set({ currentView: view }),
      setSessionId: (id) => set({ sessionId: id }),
      setAgentActive: (active) => set({ isAgentActive: active }),
      addAgentLog: (log) => set((s) => ({ agentLogs: [...s.agentLogs, log] })),
      clearAgentLogs: () => set({ agentLogs: [] }),
      setState: (state) => set({ currentState: state }),
      setUser: (user) => set({ user, currentState: 'AUTHENTICATED' }),
      updateLoanDetails: (details) => set((s) => ({ loanDetails: { ...s.loanDetails, ...details } })),
      addDocument: (doc) => set((s) => ({ documents: [...s.documents, doc] })),
      updateDocument: (id, updates) => set((s) => ({ documents: s.documents.map((d) => d.id === id ? { ...d, ...updates } : d) })),
      addChatMessage: (msg) => set((s) => ({ chatHistory: [...s.chatHistory, msg] })),
      clearSession: () => set({
        currentView: 'DASHBOARD',
        currentState: 'UNAUTHENTICATED',
        user: null,
        sessionId: null,
        loanDetails: { requestedAmount: 500000, tenureMonths: 36 },
        documents: [],
        chatHistory: [],
        isAgentActive: false,
        agentLogs: []
      }),
    }),
    {
      name: 'nbfc-session',
      partialize: (state) => ({
        currentState: state.currentState,
        user: state.user,
        sessionId: state.sessionId,
        currentView: state.currentView,
      }),
    }
  )
);
