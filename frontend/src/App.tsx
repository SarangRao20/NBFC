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
      const res = await apiClient.chat(sessionId, text, []); 
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
          underwritingStatus: fullState.decision ? (fullState.decision.charAt(0).toUpperCase() + fullState.decision.slice(1).replace('_', ' ')) : prev.underwritingStatus
        }));
      }

      // Update Phase based on intent/decision/next_agent
      if (fullState?.decision === 'soft_reject') {
        setChatPhase('negotiate');
      } else if (['loan', 'loan_confirmed'].includes(res.intent) && fullState.loan_terms?.principal) {
        setChatPhase('document');
        setAppState(prev => ({ ...prev, needsDocument: true }));
      } else if (res.is_authenticated) {
        setChatPhase('loan_details'); 
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
      <DashboardPane appState={appState} />
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
