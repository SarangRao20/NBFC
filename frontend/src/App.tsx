import { useState, useEffect } from 'react';
import DashboardPane from './components/DashboardPane';
import ChatPane from './components/ChatPane';
import type { AppState, ChatMessage } from './types';
import { apiClient } from './api/client';

const INITIAL_APP_STATE: AppState = {
  requestedAmount: 500000,
  roi: 12.5,
  tenure: 48,
  emi: 13200,
  underwritingStatus: 'Pending Evaluation',
  activeAgent: null,
  needsDocument: false,
  documents: {
    pan: 'pending',
    bankStatement: 'pending',
  },
};

const INITIAL_CHAT_HISTORY: ChatMessage[] = [
  {
    id: 'msg-1',
    sender: 'agent',
    type: 'text',
    content: 'Hi Sumit! I see you are an existing customer. I am initializing your application file on our new API backend...',
    timestamp: new Date(),
  }
];

function App() {
  const [appState, setAppState] = useState<AppState>(INITIAL_APP_STATE);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(INITIAL_CHAT_HISTORY);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Initialize Backend Session and warm up the pipeline (Steps 1 to 10)
  useEffect(() => {
    async function initBackend() {
      try {
        const { session_id } = await apiClient.startSession();
        setSessionId(session_id);

        // Pre-warm the APIs through Step 10 so we can demo underwriting
        await apiClient.identifyCustomer(session_id, '9876543210');
        await apiClient.captureLoan(session_id, 'personal', 500000, 48);
        await apiClient.requestDocuments(session_id);
        
        // Mock a file upload for OCR
        const mockFile = new File([new Blob(['mock pdf data'])], 'bank_statement.pdf', { type: 'application/pdf' });
        await apiClient.extractOcr(session_id, mockFile);
        
        await apiClient.checkTampering(session_id);
        await apiClient.verifyIncome(session_id);
        await apiClient.kycVerify(session_id);
        await apiClient.fraudCheck(session_id);

        setChatHistory(prev => [
          ...prev,
          {
            id: 'msg-ready',
            sender: 'system',
            type: 'text',
            content: 'Backend is fully synced (Phase 1-10 complete). Type "evaluate" to run Underwriting, or "negotiate" to trigger the Persuasion loop.',
            timestamp: new Date(),
          }
        ]);
      } catch (error) {
        console.error('Failed to initialize backend:', error);
      }
    }
    initBackend();
  }, []);

  const handleSendMessage = async (text: string) => {
    if (!sessionId) return;

    // 1. Add user message
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      type: 'text',
      content: text,
      timestamp: new Date(),
    };
    setChatHistory((prev) => [...prev, userMsg]);

    const lowerText = text.toLowerCase();

    try {
      if (lowerText.includes('evaluate') || lowerText.includes('underwrite') || lowerText.includes('approve')) {
        const thinkingMsgId = 'msg-thinking-' + Date.now();
        setAppState(prev => ({ ...prev, activeAgent: '📊 Underwriting Agent is evaluating...' }));
        
        setChatHistory(prev => [...prev, {
          id: thinkingMsgId,
          sender: 'agent',
          type: 'thinking',
          content: 'Consulting decision engine...',
          timestamp: new Date(),
        }]);

        // Trigger Step 11: Underwrite
        const uwResult = await apiClient.underwrite(sessionId);
        
        setChatHistory(prev => prev.filter(m => m.id !== thinkingMsgId));
        setAppState(prev => ({ 
          ...prev, 
          activeAgent: null,
          underwritingStatus: uwResult.decision === 'approve' ? 'Approved' : 'Soft-Rejected',
        }));

        if (uwResult.decision === 'approve') {
          // Proceed to Sanction
          await apiClient.sanction(sessionId);
          setChatHistory(prev => [...prev, {
            id: 'msg-sanction-' + Date.now(),
            sender: 'agent',
            type: 'sanction_letter',
            content: "Congratulations! The Underwriting Agent approved your loan. Review your Sanction Letter below.",
            timestamp: new Date(),
          }]);
        } else {
          setChatHistory(prev => [...prev, {
            id: 'msg-reject-' + Date.now(),
            sender: 'agent',
            type: 'text',
            content: `Your loan was soft-rejected. Reason: ${uwResult.reasons?.join(', ')}. Type "negotiate" to explore options.`,
            timestamp: new Date(),
          }]);
        }

      } else if (lowerText.includes('negotiate')) {
        const thinkingMsgId = 'msg-thinking-' + Date.now();
        setAppState(prev => ({ ...prev, activeAgent: '🤝 Sales Agent building counter-offer...' }));
        
        setChatHistory(prev => [...prev, {
          id: thinkingMsgId,
          sender: 'agent',
          type: 'thinking',
          content: 'Persuasion loop activated...',
          timestamp: new Date(),
        }]);

        // Step 12 & 13
        await apiClient.analyzeRejection(sessionId);
        const suggestion = await apiClient.suggestFix(sessionId);

        setChatHistory(prev => prev.filter(m => m.id !== thinkingMsgId));
        setAppState(prev => ({ ...prev, activeAgent: null }));

        if (suggestion.options && suggestion.options.length > 0) {
          setChatHistory(prev => [...prev, {
            id: 'msg-slider-' + Date.now(),
            sender: 'agent',
            type: 'emi_slider',
            content: "We've built a restructured offer. Adjust the slider to select your preferred terms, then type 'accept' to finalize.",
            timestamp: new Date(),
          }]);
        } else {
           setChatHistory(prev => [...prev, {
            id: 'msg-no-option',
            sender: 'agent',
            type: 'text',
            content: "Unfortunately, we cannot offer a restructured loan at this time.",
            timestamp: new Date(),
          }]);
        }

      } else if (lowerText.includes('accept')) {
        // Step 14 & 15
        setAppState(prev => ({ ...prev, activeAgent: '✍️ Finalizing terms...' }));
        await apiClient.respondToOffer(sessionId, 'accept_option_a');
        const state = await apiClient.getState(sessionId);

        setAppState(prev => ({
          ...prev,
          activeAgent: null,
          roi: state.loan_terms?.rate || prev.roi,
          emi: state.loan_terms?.emi || prev.emi,
          requestedAmount: state.loan_terms?.principal || prev.requestedAmount,
          tenure: state.loan_terms?.tenure || prev.tenure,
          underwritingStatus: 'Approved'
        }));

        await apiClient.sanction(sessionId);

        setChatHistory(prev => [...prev, {
          id: 'msg-accepted-' + Date.now(),
          sender: 'agent',
          type: 'sanction_letter',
          content: "Terms accepted! Your loan is formally approved. Here is your final Sanction document.",
          timestamp: new Date(),
        }]);

      } else {
        // Fallback or general chatter -> step 17 advisory trigger maybe?
        setChatHistory((prev) => [
          ...prev,
          {
            id: 'msg-response-' + Date.now(),
            sender: 'agent',
            type: 'text',
            content: "I've registered your response in the API. Try typing 'evaluate', 'negotiate', or 'accept' to observe the backend workflow in action.",
            timestamp: new Date(),
          }
        ]);
      }
    } catch (err) {
      console.error("API flow error:", err);
      setChatHistory(prev => [...prev, {
        id: 'msg-error',
        sender: 'system',
        type: 'text',
        content: "System Error: Failed to communicate with backend API. Ensure FastAPI is running on port 8000.",
        timestamp: new Date(),
      }]);
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
      />
    </div>
  );
}

export default App;
