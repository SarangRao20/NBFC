import { useState, useEffect } from 'react';
import DashboardPane from './components/DashboardPane';
import ChatPane from './components/ChatPane';
import type { AppState, ChatMessage } from './types';
import { apiClient } from './api/client';

const INITIAL_APP_STATE: AppState = {
  requestedAmount: 0,
  roi: 0,
  tenure: 0,
  emi: 0,
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
    content: 'Welcome to FinServe! I am initializing your application... Please enter your 10-digit phone number to begin.',
    timestamp: new Date(),
  }
];

type ChatPhase = 'init' | 'phone' | 'loan_details' | 'document' | 'processing' | 'evaluate' | 'negotiate' | 'accepted';

function App() {
  const [appState, setAppState] = useState<AppState>(INITIAL_APP_STATE);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(INITIAL_CHAT_HISTORY);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatPhase, setChatPhase] = useState<ChatPhase>('init');

  // Initialize Backend Session
  useEffect(() => {
    async function initBackend() {
      try {
        const { session_id } = await apiClient.startSession();
        setSessionId(session_id);
        setChatPhase('phone');
      } catch (error) {
        console.error('Failed to initialize backend:', error);
      }
    }
    initBackend();
  }, []);

  const pushAgentMessage = (text: string, type: 'text' | 'thinking' | 'sanction_letter' | 'emi_slider' = 'text', id = `msg-${Date.now()}`) => {
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
      if (chatPhase === 'phone') {
        setAppState(prev => ({ ...prev, activeAgent: 'Looking up customer...' }));
        const res = await apiClient.identifyCustomer(sessionId, lowerText);
        setAppState(prev => ({ ...prev, activeAgent: null }));
        
        let reply = `Customer Identified: ${res.is_existing_customer ? 'Returning Customer' : 'New Customer'}. `;
        if (res.customer_data) {
           reply += `Welcome back, ${res.customer_data.name}. `;
        }
        reply += `Please provide your desired Loan Amount and Tenure in months (e.g. 500000 48).`;
        
        pushAgentMessage(reply);
        setChatPhase('loan_details');

      } else if (chatPhase === 'loan_details') {
        const parts = lowerText.split(' ');
        if (parts.length < 2) {
          pushAgentMessage("Please provide both amount and tenure, separated by a space (e.g. 500000 48).");
          return;
        }
        
        const amount = parseInt(parts[0]);
        const tenure = parseInt(parts[1]);
        
        if (isNaN(amount) || isNaN(tenure)) {
           pushAgentMessage("Invalid numbers. Please try again.");
           return;
        }

        setAppState(prev => ({ ...prev, activeAgent: 'Capturing loan details...' }));
        await apiClient.captureLoan(sessionId, 'personal', amount, tenure);
        await apiClient.requestDocuments(sessionId);
        
        setAppState(prev => ({ 
          ...prev, 
          activeAgent: null,
          requestedAmount: amount, 
          tenure, 
          needsDocument: true 
        }));
        
        setChatPhase('document');
        pushAgentMessage("Terms captured. Please upload your Bank Statement PDF using the dropzone below.");

      } else if (chatPhase === 'negotiate' && lowerText.includes('accept')) {
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
        setChatPhase('accepted');
        pushAgentMessage("Terms accepted! Your loan is formally approved. Here is your final Sanction document.", 'sanction_letter');

      } else if (chatPhase === 'accepted') {
        pushAgentMessage("Your loan is already approved. Thank you!");
      } else {
        // Fallback or unrecognized
        pushAgentMessage("I didn't catch that. Please follow the instructions to proceed.");
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
