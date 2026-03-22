import { useState, useEffect, useRef } from 'react';
import DashboardPane from './components/DashboardPane';
import ChatPane from './components/ChatPane';
import type { AppState, ChatMessage, MessageType } from './types';
import { apiClient } from './api/client';

const INITIAL_APP_STATE: AppState = {
  customerName: '',
  requestedAmount: 0,
  roi: 0,
  tenure: 0,
  emi: 0,
  creditScore: 0,
  preApprovedLimit: 0,
  underwritingStatus: 'Pending Evaluation',
  activeAgent: null,
  needsDocument: false,
  requiredDocuments: [],
  documents: {
    pan: 'pending',
    bankStatement: 'pending',
  },
};

const INITIAL_CHAT_HISTORY: ChatMessage[] = [];

type ChatPhase = 'init' | 'phone' | 'name' | 'loan_details' | 'document' | 'processing' | 'evaluate' | 'negotiate' | 'accepted';

function App() {
  const [appState, setAppState] = useState<AppState>(INITIAL_APP_STATE);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(INITIAL_CHAT_HISTORY);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatPhase, setChatPhase] = useState<ChatPhase>('init');
  const greetingStarted = useRef(false);

  // Initialize Backend Session
  useEffect(() => {
    if (greetingStarted.current) return;
    greetingStarted.current = true;

    async function initBackend() {
      try {
        const { session_id } = await apiClient.startSession();
        setSessionId(session_id);
        setChatPhase('phone');

        // Automatically trigger initial greeting from Arjun
        const res = await apiClient.chat(session_id, "hello");
        if (res.all_replies && res.all_replies.length > 0) {
          res.all_replies.forEach((m: any) => {
            if (typeof m === 'string') pushAgentMessage(m);
            else if (m && typeof m === 'object') pushAgentMessage(m.content, m.type);
          });
        } else if (res.reply) {
          pushAgentMessage(res.reply);
        }
      } catch (error) {
        console.error('Failed to initialize backend:', error);
      }
    }
    initBackend();
  }, []);

  const pushAgentMessage = (text: string, type: MessageType = 'text', id = `msg-${Date.now()}`) => {
    setChatHistory(prev => [...prev, {
      id,
      sender: 'agent',
      type,
      content: text,
      timestamp: new Date(),
    }]);
    return id;
  };

  const runNegotiation = async () => {
    if (!sessionId) return;
    const thinkingId = pushAgentMessage('Persuasion loop activated...', 'thinking');
    setAppState(prev => ({ ...prev, activeAgent: '🤝 Sales Agent building counter-offer...' }));
    
    try {
      await apiClient.analyzeRejection(sessionId);
      const suggestion = await apiClient.suggestFix(sessionId);

      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      setAppState(prev => ({ ...prev, activeAgent: null }));

      if (suggestion.options && suggestion.options.length > 0) {
        setChatPhase('negotiate');
        pushAgentMessage("We've built a restructured offer. Adjust the slider to select your preferred terms, then type 'accept' to finalize.", 'emi_slider');
      } else {
        pushAgentMessage("Unfortunately, we cannot offer a restructured loan at this time.");
      }
    } catch (e) {
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      pushAgentMessage("Error generating counter offer.");
      setAppState(prev => ({ ...prev, activeAgent: null }));
    }
  };

  const runUnderwriting = async () => {
    if (!sessionId) return;
    const thinkingId = pushAgentMessage('Consulting decision engine...', 'thinking');
    setAppState(prev => ({ ...prev, activeAgent: '📊 Underwriting Agent is evaluating...' }));
    
    try {
      const uwResult = await apiClient.underwrite(sessionId);
      
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      setAppState(prev => ({ 
        ...prev, 
        activeAgent: null,
        underwritingStatus: uwResult.decision === 'approve' ? 'Approved' : 'Soft-Rejected',
      }));

      if (uwResult.decision === 'approve') {
        await apiClient.sanction(sessionId);
        setChatPhase('accepted');
        pushAgentMessage("Congratulations! The Underwriting Agent approved your loan. Review your Sanction Letter below.", 'sanction_letter');
      } else {
        pushAgentMessage(`Your loan was soft-rejected. Reason: ${uwResult.reasons?.join(', ')}. Generating counter-offer...`);
        await runNegotiation();
      }
    } catch (e) {
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      pushAgentMessage("Error during underwriting.");
      setAppState(prev => ({ ...prev, activeAgent: null }));
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!sessionId) return;
    
    setChatHistory(prev => [...prev, {
      id: `msg-upload-${Date.now()}`,
      sender: 'user',
      type: 'text',
      content: `Uploaded ${file.name}`,
      timestamp: new Date(),
    }]);

    setAppState(prev => ({
      ...prev,
      needsDocument: false,
      documents: { ...prev.documents, bankStatement: 'verified' },
      activeAgent: '📄 Processing Document...'
    }));

    const thinkingId = pushAgentMessage('Running Verification (OCR, Tampering, KYC, Fraud)...', 'thinking');
    
    try {
      setChatPhase('processing');
      await apiClient.extractOcr(sessionId, file);
      await apiClient.checkTampering(sessionId);
      await apiClient.verifyIncome(sessionId);
      await apiClient.kycVerify(sessionId);
      await apiClient.fraudCheck(sessionId);
      
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      setAppState(prev => ({ ...prev, activeAgent: null }));
      
      pushAgentMessage('Documents verified successfully. Moving to Underwriting...');
      
      // Automatically trigger underwriting
      await runUnderwriting();

    } catch (err) {
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      pushAgentMessage('Error processing document. Please check backend logs.');
      setAppState(prev => ({ ...prev, activeAgent: null }));
    }
  };

  const loadSession = async (sid: string) => {
    try {
      setSessionId(sid);
      const state = await apiClient.getSession(sid);
      const history = await apiClient.getHistory(sid);

      if (state) {
        setAppState(prev => ({
          ...prev,
          customerName: state.customer_data?.name || '',
          requestedAmount: state.loan_terms?.principal || 0,
          tenure: state.loan_terms?.tenure || 0,
          roi: state.loan_terms?.rate || 0,
          emi: state.loan_terms?.emi || 0,
          creditScore: state.customer_data?.credit_score || 0,
          preApprovedLimit: state.customer_data?.pre_approved_limit || 0,
          underwritingStatus: state.decision ? (state.decision.charAt(0).toUpperCase() + state.decision.slice(1).replace('_', ' ')) as any : 'Pending Evaluation',
          activeAgent: null,
          needsDocument: state.current_phase === 'document',
          requiredDocuments: state.current_phase === 'document' ? ["Identity (PAN or Aadhaar)"] : [],
          documents: {
            pan: state.documents?.verified ? 'verified' : 'pending',
            bankStatement: state.documents?.verified ? 'verified' : 'pending',
          },
          pastLoans: state.customer_data?.past_loans,
          pastRecords: state.customer_data?.past_records,
        }));
      }

      if (history.history && history.history.length > 0) {
        const chatMsgs: ChatMessage[] = history.history.map((m: any, i: number) => ({
          id: `msg-hist-${i}-${sid}`,
          sender: (m.sender || m.role === 'user') ? (m.sender || 'user') : 'agent',
          type: m.type || 'text',
          content: m.content || m.text || (typeof m === 'string' ? m : ''),
          timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
        }));
        setChatHistory(chatMsgs);
      } else {
        setChatHistory([]);
      }
      
      // Update chat phase based on session state
      if (state.decision === 'approve') setChatPhase('accepted');
      else if (state.decision === 'soft_reject') setChatPhase('negotiate');
      else setChatPhase('loan_details');

    } catch (err) {
      console.error("Failed to load session:", err);
      pushAgentMessage("Error: Failed to load selected session.");
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!sessionId) return;

    setChatHistory(prev => [...prev, {
      id: Date.now().toString(),
      sender: 'user',
      type: 'text',
      content: text,
      timestamp: new Date(),
    }]);

    const lowerText = text.toLowerCase().trim();

    try {
      // General agent-driven chat
      setAppState(prev => ({ ...prev, activeAgent: 'Thinking...' }));
      const res = await apiClient.chat(sessionId, text, chatHistory); 
      setAppState(prev => ({ ...prev, activeAgent: null }));

      if (res.all_replies && res.all_replies.length > 0) {
        res.all_replies.forEach((m: any) => {
            if (typeof m === 'string') pushAgentMessage(m);
            else if (m && typeof m === 'object') pushAgentMessage(m.content, m.type);
        });
      } else if (res.reply) {
        pushAgentMessage(res.reply);
      }

      // Sync state from backend
      const fullState = await apiClient.getSession(sessionId);
      if (fullState) {
        setAppState(prev => ({
          ...prev,
          customerName: fullState.customer_data?.name || prev.customerName,
          requestedAmount: fullState.loan_terms?.principal || prev.requestedAmount,
          tenure: fullState.loan_terms?.tenure || prev.tenure,
          roi: fullState.loan_terms?.rate || prev.roi, // Match 'rate' from SessionStateResponse
          emi: fullState.loan_terms?.emi || prev.emi,
          creditScore: fullState.customer_data?.credit_score || prev.creditScore,
          preApprovedLimit: fullState.customer_data?.pre_approved_limit || prev.preApprovedLimit,
          underwritingStatus: fullState.decision ? (fullState.decision.charAt(0).toUpperCase() + fullState.decision.slice(1).replace('_', ' ')) : prev.underwritingStatus,
          pastLoans: fullState.customer_data?.past_loans || prev.pastLoans,
          pastRecords: fullState.customer_data?.past_records || prev.pastRecords,
        }));
      }

      // Update Phase based on intent/decision/next_agent
      if (fullState?.decision === 'soft_reject') {
        setChatPhase('negotiate');
      } else if (['loan', 'loan_confirmed'].includes(res.intent) && fullState.loan_terms?.principal) {
        setChatPhase('document');
        let docs = ["Identity (PAN or Aadhaar)"];
        let limit = fullState.customer_data?.pre_approved_limit || 150000;
        if (fullState.loan_terms.principal > limit) {
          docs.push("Income Proof (Salary Slip)");
        }
        setAppState(prev => ({ ...prev, needsDocument: true, requiredDocuments: docs }));
      } else if (res.is_authenticated) {
        setChatPhase('loan_details'); 
        // Fetch past sessions when user is identified
        if (fullState.customer_data?.phone) {
          const sessions = await apiClient.getSessionsByPhone(fullState.customer_data.phone);
          setAppState(prev => ({ ...prev, pastSessions: sessions }));
        }
      }

      // Specific legacy triggers if still helpful (e.g. accepting modified offer from UI)
      if (chatPhase === 'negotiate' && lowerText.includes('accept')) {
        // Handled by agent above now, but keeping for direct UI buttons if any exist
      }
    } catch (err) {
      console.error("API flow error:", err);
      pushAgentMessage("System Error: Failed to communicate with backend API.");
      setAppState(prev => ({ ...prev, activeAgent: null }));
    }
  };

  return (
    <div className="w-full h-screen flex overflow-hidden font-sans bg-slate-50 text-slate-900 leading-relaxed">
      <DashboardPane appState={appState} onLoadSession={loadSession} />
      <ChatPane 
        appState={appState} 
        setAppState={setAppState} 
        chatHistory={chatHistory} 
        onSendMessage={handleSendMessage} 
        onFileUpload={handleFileUpload}
      />
    </div>
  );
}

export default App;
