import { useState, useEffect, useRef } from 'react';
import DashboardPane from './components/DashboardPane';
import ChatPane from './components/ChatPane';
import AuthWrapper from './components/AuthWrapper';
import type { AppState, ChatMessage, MessageType } from './types';
import { apiClient } from './api/client';
import { wsClient } from './api/websocket';

interface UserData {
  name: string;
  phone: string;
  dob: string;
  profession: string;
  address: string;
  email: string;
  password: string;
  city?: string;
  salary?: number;
}

const INITIAL_APP_STATE: AppState = {
  sessionId: null,
  customerName: '',
  requestedAmount: 0,
  roi: 0,
  tenure: 0,
  emi: 0,
  creditScore: 0,
  preApprovedLimit: 0,
  underwritingStatus: 'Pending Evaluation',
  activeAgent: null,
  thinkingAgents: [],
  needsDocument: false,
  requiredDocuments: [],
  documents: {
    pan: 'pending',
    bankStatement: 'pending',
  },
  actionLog: [],
  options: []
};

const INITIAL_CHAT_HISTORY: ChatMessage[] = [];

type ChatPhase = 'init' | 'phone' | 'name' | 'loan_details' | 'document' | 'processing' | 'evaluate' | 'negotiate' | 'accepted' | 'onboarding';

function App() {
  const [appState, setAppState] = useState<AppState>(INITIAL_APP_STATE);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(INITIAL_CHAT_HISTORY);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  // @ts-ignore - currentUser is currently unused but kept for future features
  const [currentUser] = useState<UserData | null>(null);
  // @ts-ignore - chatPhase is currently unused but kept for state consistency
  const [chatPhase, setChatPhase] = useState<ChatPhase>('init');
  const greetingStarted = useRef(false);

  // Persistence: Check for existing session on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem('nbfc_session_id');
    if (savedSessionId) {
      async function resumeSession() {
        try {
          // Verify session first
          const verifyUrl = `http://localhost:8000/auth/verify?session_id=${savedSessionId}`;
          const vResp = await fetch(verifyUrl);
          const vData = await vResp.json();
          
          if (vResp.ok && vData.success) {
            setSessionId(savedSessionId);
            setIsAuthenticated(true);
            // Load full state (history, terms etc)
            await loadSession(savedSessionId);
            console.log("🔄 Session resumed successfully:", savedSessionId);
          } else {
            localStorage.removeItem('nbfc_session_id');
            localStorage.removeItem('nbfc_customer_name');
          }
        } catch (err) {
          console.error("Failed to resume session:", err);
        }
      }
      resumeSession();
    }
  }, []);

  const fetchPastSessions = async (phone?: string) => {
    if (!phone) return;
    try {
      const sessions = await apiClient.getSessionsByPhone(phone);
      setAppState(prev => ({ ...prev, pastSessions: sessions || [] }));
    } catch (err) {
      console.error('Failed to fetch past sessions:', err);
    }
  };

  const handleAuthComplete = (userData: UserData, newSessionId: string) => {
    // @ts-ignore - setCurrentUser is currently unused but kept for future features
    // setCurrentUser(userData);
    setSessionId(newSessionId);
    setIsAuthenticated(true);
    
    // Persist to localStorage
    localStorage.setItem('nbfc_session_id', newSessionId);
    localStorage.setItem('nbfc_customer_name', userData.name);

    setAppState(prev => ({ 
      ...prev, 
      sessionId: newSessionId,
      customerName: userData.name,
      creditScore: userData.salary ? 700 : 650, // Simple credit score logic
      preApprovedLimit: userData.salary ? userData.salary * 3 : 100000, // Simple limit calculation
      actionLog: []
    }));
    fetchPastSessions(userData.phone);
    setChatPhase('loan_details');
  };

  // Initialize Backend Session after authentication
  useEffect(() => {
    if (!isAuthenticated || !sessionId || greetingStarted.current) return;
    greetingStarted.current = true;

    async function initBackend() {
      try {
        // Set session ID and start chat
        setAppState(prev => ({ ...prev, sessionId: sessionId }));

        // Automatically trigger initial greeting from Arjun
        const res = await apiClient.chat(sessionId!, "hello");
        if (res.all_replies && res.all_replies.length > 0) {
          res.all_replies.forEach((m: any) => {
            if (typeof m === 'string') pushAgentMessage(m);
            else if (m && typeof m === 'object') pushAgentMessage(m.content, m.type, undefined, m.options);
          });
        } else if (res.reply) {
          pushAgentMessage(res.reply, 'text', undefined, res.options);
        }

        // Fetch and display advisory message if user has past loans
        try {
          const state = await apiClient.getState(sessionId!);
          const phone = state?.customer_data?.phone;
          
          if (phone) {
            const advisoryRes = await fetch(`http://localhost:8000/advisory/loans/${phone}/message?intent=general`);
            if (advisoryRes.ok) {
              const advisoryData = await advisoryRes.json();
              if (advisoryData.message) {
                pushAgentMessage(advisoryData.message, 'text');
              }
            }
          }
        } catch (err) {
          // Silent fail - advisory message is optional
        }

      } catch (error) {
        console.error('Failed to initialize backend:', error);
      }
    }
    initBackend();

    return () => wsClient.disconnect();
  }, [sessionId, isAuthenticated]);

  // WebSocket Listener
  useEffect(() => {
    if (!sessionId) return;
    
    wsClient.connect(sessionId);
    const unsubscribe = wsClient.subscribe((data) => {
      console.log('📥 [WS EVENT]', data);
      
      if (data.type === 'AGENT_STEP') {
        const steps = data.action_log || data.steps || [];
        const options = data.options || [];
        setAppState(prev => ({ 
          ...prev, 
          actionLog: Array.isArray(steps) ? steps : [steps], 
          options: options,
          activeAgent: Array.isArray(steps) && steps.length > 0 ? `🔍 ${steps[steps.length - 1]}...` : prev.activeAgent 
        }));
        
        // If we have options, push them to chat as well for accessibility
        if (options && options.length > 0) {
          pushAgentMessage('I have prepared some options for you:', 'text', `msg-opt-${Date.now()}-${Math.random()}`, options);
        }
      }
      
      if (data.type === 'AGENT_THINKING') {
        const { agent, thinking } = data;
        setAppState(prev => {
          const newThinking = thinking 
            ? [...new Set([...prev.thinkingAgents, agent])]
            : prev.thinkingAgents.filter(a => a !== agent);
          
          return {
            ...prev,
            thinkingAgents: newThinking,
            activeAgent: newThinking.length > 0 ? `🔍 ${newThinking.join(', ')} is thinking...` : null
          };
        });
      }

      if (data.type === 'PHASE_UPDATE') {
        console.log(`🚀 [PHASE UPDATE] -> ${data.phase}`);
        // Automatically sync state when phase changes
        apiClient.getSession(sessionId).then(fullState => {
          if (fullState) {
            setAppState(prev => ({
              ...prev,
              customerName: fullState.customer_data?.name || prev.customerName,
              requestedAmount: fullState.loan_terms?.principal || prev.requestedAmount,
              tenure: fullState.loan_terms?.tenure || prev.tenure,
              roi: fullState.loan_terms?.rate || prev.roi,
              emi: fullState.loan_terms?.emi || prev.emi,
              creditScore: fullState.customer_data?.credit_score || prev.creditScore,
              preApprovedLimit: fullState.customer_data?.pre_approved_limit || prev.preApprovedLimit,
              underwritingStatus: fullState.decision ? (fullState.decision.charAt(0).toUpperCase() + fullState.decision.slice(1).replace('_', ' ')) : prev.underwritingStatus,
            }));
          }
        });
      }
    });

    return () => { unsubscribe(); };
  }, [sessionId]);

  const pushAgentMessage = (text: string, type: MessageType = 'text', id = `msg-${Date.now()}-${Math.random()}`, options?: string[]) => {
    const autoOptions = options && options.length > 0
      ? options
      : (/\b(yes|no)\b/i.test(text) && (/\?/g.test(text) || /confirm|proceed|accept|decline/i.test(text))
        ? ['Yes', 'No']
        : undefined);
    setChatHistory(prev => [...prev, {
      id,
      sender: 'agent',
      type,
      content: text,
      options: autoOptions,
      timestamp: new Date(),
    }]);
    return id;
  };

  const runNegotiation = async () => {
    if (!sessionId) return;
    const thinkingId = pushAgentMessage('Persuasion loop activated...', 'thinking');
    setAppState(prev => ({ 
      ...prev, 
      thinkingAgents: [...prev.thinkingAgents, 'Sales Agent'],
      activeAgent: '🤝 Sales Agent building counter-offer...' 
    }));
    
    try {
      await apiClient.analyzeRejection(sessionId);
      const suggestion = await apiClient.suggestFix(sessionId);

      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      setAppState(prev => ({ 
        ...prev, 
        thinkingAgents: [],
        activeAgent: null 
      }));

      if (suggestion.options && suggestion.options.length > 0) {
        setChatPhase('negotiate');
        pushAgentMessage("We've built a restructured offer. Adjust the slider to select your preferred terms, then type 'accept' to finalize.", 'emi_slider');
      } else {
        pushAgentMessage("Unfortunately, we cannot offer a restructured loan at this time.");
      }
    } catch (e) {
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      pushAgentMessage("Error generating counter offer.");
      setAppState(prev => ({ 
        ...prev, 
        thinkingAgents: [],
        activeAgent: null 
      }));
    }
  };

  const runUnderwriting = async () => {
    if (!sessionId) return;
    const thinkingId = pushAgentMessage('Consulting decision engine...', 'thinking');
    setAppState(prev => ({ 
      ...prev, 
      thinkingAgents: [...prev.thinkingAgents, 'Underwriting Agent'],
      activeAgent: '📊 Underwriting Agent is evaluating...' 
    }));
    
    try {
      const uwResult = await apiClient.underwrite(sessionId);
      
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      setAppState(prev => ({ 
        ...prev, 
        thinkingAgents: prev.thinkingAgents.filter(a => a !== 'Underwriting Agent'),
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
      setAppState(prev => ({ 
        ...prev, 
        thinkingAgents: prev.thinkingAgents.filter(a => a !== 'Underwriting Agent'),
        activeAgent: null 
      }));
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!sessionId) return;
    
    setChatHistory(prev => [...prev, {
      id: `msg-upload-${Date.now()}-${Math.random()}`,
      sender: 'user',
      type: 'text',
      content: `Uploaded ${file.name}`,
      timestamp: new Date(),
    }]);

    setAppState(prev => ({
      ...prev,
      needsDocument: false,
      documents: { ...prev.documents, bankStatement: 'verified' },
      thinkingAgents: [...prev.thinkingAgents, 'Document Agent'],
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
      setAppState(prev => ({ 
        ...prev, 
        thinkingAgents: [],
        activeAgent: null 
      }));
      
      pushAgentMessage('Documents verified successfully. Moving to Underwriting...');
      
      // Automatically trigger underwriting
      await runUnderwriting();

    } catch (err) {
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      pushAgentMessage('Error processing document. Please check backend logs.');
      setAppState(prev => ({ 
        ...prev, 
        thinkingAgents: [],
        activeAgent: null 
      }));
    }
  };

  const loadSession = async (sid: string) => {
    try {
      setSessionId(sid);
      setAppState(prev => ({ ...prev, sessionId: sid, actionLog: [] }));
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
          underwritingStatus: state.decision === 'approve' ? 'Approved' : (state.decision === 'soft_reject' ? 'Soft-Rejected' : 'Pending Evaluation'),
          activeAgent: state.current_phase,
          actionLog: state.action_log || [],
          options: state.options || [],
          needsDocument: state.current_phase === 'kyc_agent',
          requiredDocuments: state.current_phase === 'document' ? ["Identity (PAN or Aadhaar)"] : [],
          documents: {
            pan: state.documents?.verified ? 'verified' : 'pending',
            bankStatement: state.documents?.verified ? 'verified' : 'pending',
          },
          pastLoans: state.customer_data?.past_loans,
          pastRecords: state.customer_data?.past_records,
        }));
        await fetchPastSessions(state.customer_data?.phone);
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

  const handleNewChat = async () => {
    try {
      const resp = await apiClient.startSession();
      if (resp && resp.session_id) {
        setSessionId(resp.session_id);
        const user = { name: appState.customerName, phone: '', email: '', dob: '', profession: '', address: '', password: '' };
        // We keep the customerName but reset everything else
        setAppState({
          ...INITIAL_APP_STATE,
          sessionId: resp.session_id,
          customerName: appState.customerName,
          pastSessions: appState.pastSessions
        });
        setChatHistory([]);
        setChatPhase('init');
        greetingStarted.current = false;
        
        // Fetch advisory message if user has past loans
        try {
          // Get customer info to retrieve phone
          const state = await apiClient.getState(resp.session_id);
          const phone = state?.customer_data?.phone;
          
          if (phone) {
            // Try to fetch advisory message
            const advisoryRes = await fetch(`http://localhost:8000/advisory/loans/${phone}/message?intent=general`);
            if (advisoryRes.ok) {
              const advisoryData = await advisoryRes.json();
              if (advisoryData.message) {
                pushAgentMessage(advisoryData.message, 'text');
              }
            }
          }
        } catch (err) {
          console.log("No advisory message available for new chat");
        }
        
        console.log("🆕 New session started:", resp.session_id);
      }
    } catch (err) {
      console.error("Failed to start new chat:", err);
      pushAgentMessage("Error: Failed to start a new chat session.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('nbfc_session_id');
    localStorage.removeItem('nbfc_customer_name');
    setSessionId(null);
    setIsAuthenticated(false);
    setAppState(INITIAL_APP_STATE);
    setChatHistory(INITIAL_CHAT_HISTORY);
    greetingStarted.current = false;
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

    try {
      // General agent-driven chat
      setAppState(prev => ({ 
        ...prev, 
        thinkingAgents: [...prev.thinkingAgents, 'Arjun'],
        activeAgent: 'Thinking...' 
      }));
      
      let res: any = null;
      try {
        res = await apiClient.chat(sessionId!, text, chatHistory); 
        setAppState(prev => ({ 
          ...prev, 
          thinkingAgents: prev.thinkingAgents.filter(a => a !== 'Arjun'),
          activeAgent: null 
        }));

        // Handle multiple replies if available
        if (res.all_replies && res.all_replies.length > 0) {
          res.all_replies.forEach((m: any, idx: number) => {
              const isLast = idx === res.all_replies.length - 1;
              const msgOptions = isLast ? (m.options || res.options) : m.options;
              
              if (typeof m === 'string') pushAgentMessage(m, 'text', undefined, msgOptions);
              else if (m && typeof m === 'object') pushAgentMessage(m.content, m.type, undefined, msgOptions);
          });
        } else if (res.reply) {
          pushAgentMessage(res.reply, 'text', undefined, res.options);
        }
      } catch (err) {
        console.error("Chat API failed:", err);
        pushAgentMessage("System Error: Chat communication failed.");
        setAppState(prev => ({ 
          ...prev, 
          thinkingAgents: prev.thinkingAgents.filter(a => a !== 'Arjun'),
          activeAgent: null 
        }));
        return; // Stop if chat fails
      }

      // Sync state from backend
      let fullState: any = null;
      try {
        fullState = await apiClient.getSession(sessionId);
        if (fullState) {
          setAppState(prev => ({
            ...prev,
            customerName: fullState.customer_data?.name || prev.customerName,
            requestedAmount: fullState.loan_terms?.principal || prev.requestedAmount,
            tenure: fullState.loan_terms?.tenure || prev.tenure,
            roi: fullState.loan_terms?.rate || prev.roi,
            emi: fullState.loan_terms?.emi || prev.emi,
            creditScore: fullState.customer_data?.credit_score || prev.creditScore,
            preApprovedLimit: fullState.customer_data?.pre_approved_limit || prev.preApprovedLimit,
            underwritingStatus: fullState.decision ? (fullState.decision.charAt(0).toUpperCase() + fullState.decision.slice(1).replace('_', ' ')) : prev.underwritingStatus,
            pastLoans: fullState.customer_data?.past_loans || prev.pastLoans,
            pastRecords: fullState.customer_data?.past_records || prev.pastRecords,
          }));
        }
      } catch (err) {
        console.error("State sync failed:", err);
      }

      // Update Phase based on intent/decision/next_agent
      try {
        if (fullState?.decision === 'soft_reject') {
          setChatPhase('negotiate');
        } else if (fullState?.current_phase === 'kyc_verification' || fullState?.current_phase === 'document') {
          setChatPhase('document');
          let docs = ["Identity (PAN or Aadhaar)"];
          let limit = fullState.customer_data?.pre_approved_limit || 150000;
          if (fullState.loan_terms?.principal > limit) {
            docs.push("Income Proof (Salary Slip)");
          }
          setAppState(prev => ({ ...prev, needsDocument: true, requiredDocuments: docs }));
        } else if (fullState?.current_phase === 'sales' || fullState?.loan_terms?.principal) {
          setChatPhase('loan_details'); 
          // Fetch past sessions when user is identified
          if (fullState?.customer_data?.phone) {
            const sessions = await apiClient.getSessionsByPhone(fullState.customer_data.phone);
            setAppState(prev => ({ ...prev, pastSessions: sessions }));
          }
        } else {
          setChatPhase('onboarding');
        }
      } catch (err) {
        console.error("Post-chat logic failed:", err);
      }
    } catch (err) {
      console.error("Top-level API error:", err);
      pushAgentMessage("System Error: Failed to communicate with backend API.");
      setAppState(prev => ({ 
        ...prev, 
        thinkingAgents: [],
        activeAgent: null 
      }));
    }

  };

  // Show AuthWrapper if not authenticated, otherwise show main app
  if (!isAuthenticated) {
    return <AuthWrapper onAuthComplete={handleAuthComplete} />;
  }

  return (
    <div className="w-full h-screen flex overflow-hidden font-sans bg-slate-50 text-slate-900 leading-relaxed">
      <DashboardPane 
        appState={appState} 
        onLoadSession={loadSession} 
        onNewChat={handleNewChat} 
        onLogout={handleLogout}
      />
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
