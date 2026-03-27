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
  credit_score?: number;
  pre_approved_limit?: number;
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
  documents_uploaded: false,
  eligible_offers: [],
  actionLog: [],
  options: [],
  loan_terms: undefined,
  phone: undefined,
  salary: 0
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
            if (savedSessionId) await loadSession(savedSessionId);
            console.log("Session resumed successfully:", savedSessionId);
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
    localStorage.setItem('nbfc_customer_phone', userData.phone);

    setAppState(prev => ({ 
      ...prev, 
      sessionId: newSessionId,
      customerName: userData.name,
      phone: userData.phone,
      creditScore: userData.credit_score || prev.creditScore || 0,
      preApprovedLimit: userData.pre_approved_limit || prev.preApprovedLimit || 0,
      salary: userData.salary || prev.salary || 0,
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

        // Initial greeting is now handled by the user's first interaction
        // to prevent duplicate initial messages.

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

  // Auto-logout on page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (isAuthenticated) {
        handleLogout();
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isAuthenticated]);

  // WebSocket Listener
  useEffect(() => {
    if (!sessionId) return;
    
    wsClient.connect(sessionId);
    const unsubscribe = wsClient.subscribe((data) => {
      console.log('📥 [WS EVENT]', data);
      
      if (data.type === 'AGENT_STEP') {
        const steps = data.action_log || data.steps || [];
        setAppState(prev => ({ 
          ...prev, 
          actionLog: Array.isArray(steps) ? steps : [steps], 
          // options removed to disable button UI
          activeAgent: Array.isArray(steps) && steps.length > 0 ? `🔍 ${steps[steps.length - 1]}...` : prev.activeAgent 
        }));
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
              loan_terms: fullState.loan_terms || prev.loan_terms,
              eligible_offers: (fullState.eligible_offers || prev.eligible_offers || []).map((o: any) => ({
                lender_id: o.lender_id || o.id || o.lenderId || o.nbfc_id || o.nbfcId,
                lender_name: o.lender_name || o.name || o.lenderName || o.nbfc_name || o.nbfcName,
                interest_rate: o.interest_rate || o.rate || o.rate_percent || o.r,
                emi: o.emi || o.monthly_payment || 0
              })),
              documents_uploaded: fullState.documents_uploaded || prev.documents_uploaded || false,
              disbursement_step: fullState.disbursement_step,
              net_disbursement_amount: fullState.net_disbursement_amount,
              needsDocument: (fullState.current_phase === 'kyc_verification' || fullState.current_phase === 'document'),
              requiredDocuments: fullState.required_documents || prev.requiredDocuments,
            }));
          }
        });
      }
    });

    return () => { unsubscribe(); };
  }, [sessionId]);

  const pushAgentMessage = (text: string, type: MessageType = 'text', id = `msg-${Date.now()}-${Math.random()}`) => {
    // Buttons/options intentionally disabled in chat UI — keep messages concise
    setChatHistory(prev => [...prev, {
      id,
      sender: 'agent',
      type,
      content: text,
      options: [],
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
        // Apply first option's restructured terms to appState so the EMI slider shows correct values
        const firstOption = suggestion.options[0];
        setAppState(prev => ({
          ...prev,
          requestedAmount: firstOption.amount || prev.requestedAmount,
          tenure: firstOption.tenure || prev.tenure,
          emi: firstOption.emi || prev.emi,
        }));
        setChatPhase('negotiate');
        pushAgentMessage("We've built a restructured offer. Adjust the slider to select your preferred terms, then click 'Apply Revised Terms' to finalize.", 'emi_slider');
      } else if (suggestion?.requires_salary) {
        // Salary is missing — show a helpful prompt with action buttons to retry
        const salaryMsg = suggestion?.message || 
          "We need your monthly income to propose negotiable options. Please provide your monthly salary to continue.";
        setChatHistory(prev => [...prev, {
          id: `msg-${Date.now()}-${Math.random()}`,
          sender: 'agent',
          type: 'text',
          content: `${salaryMsg}\n\nPlease share your monthly salary (for example: 'My salary is 60000') and then click Negotiate again.`,
          options: ['Negotiate', 'Download Rejection Letter'],
          timestamp: new Date(),
        }]);
      } else {
        // No viable options at all — show rejection messaging with buttons
        const fallbackMessage = suggestion?.message || "Unfortunately, we cannot offer a restructured loan at this time.";
        setChatHistory(prev => [...prev, {
          id: `msg-${Date.now()}-${Math.random()}`,
          sender: 'agent',
          type: 'text',
          content: fallbackMessage,
          options: ['Download Rejection Letter'],
          timestamp: new Date(),
        }]);
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
        const reasonsText = uwResult.reasons?.length ? uwResult.reasons.join(', ') : 'Not specified';
        // Present heuristic action buttons: Negotiate or Download Rejection Letter
        setChatHistory(prev => [...prev, {
          id: `msg-${Date.now()}-${Math.random()}`,
          sender: 'agent',
          type: 'text',
          content: `Your loan was soft-rejected. Reason: ${reasonsText}\n\nYou can choose to negotiate a counter-offer or download your rejection letter.`,
          options: ['Negotiate', 'Download Rejection Letter'],
          timestamp: new Date(),
        }]);
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

  const handleSelectLender = async (lenderId: string) => {
    if (!sessionId) return;
    try {
      const res = await apiClient.selectLender(sessionId, lenderId);
      // Refresh session state
      const fullState = await apiClient.getSession(sessionId);
      if (fullState) {
        setAppState(prev => ({
          ...prev,
          loan_terms: fullState.loan_terms || prev.loan_terms,
          options: fullState.options || prev.options,
        }));
      }
      pushAgentMessage(res.message || 'Lender selected');
    } catch (err) {
      console.error('Select lender failed:', err);
      pushAgentMessage('Failed to save selected lender.');
    }
  };

  const handleBatchFileUpload = async (files: File[]) => {
    if (!sessionId || files.length === 0) return;
    
    // 1. Log the batch intention
    setChatHistory(prev => [...prev, {
      id: `msg-batch-${Date.now()}`,
      sender: 'user',
      type: 'text',
      content: `Uploading ${files.length} documents: ${files.map(f => f.name).join(', ')}`,
      timestamp: new Date(),
    }]);
    // Hide the zone immediately and log current selected documents
    setAppState(prev => ({
      ...prev,
      thinkingAgents: [...prev.thinkingAgents, 'Document Agent'],
      activeAgent: '📄 Verifying All Documents...',
      // Keep the upload zone visible until verification completes
      needsDocument: true,
    }));

    const thinkingId = pushAgentMessage(`Running Batch Verification for ${files.length} documents...`, 'thinking');
    
    const failBatch = (reason: string) => {
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      pushAgentMessage(`❌ **Batch Verification Failed:** ${reason}\n\nPlease try again with the correct files.`);
      
      // Restore document zone if failed so user can try again
      setChatPhase('document');
      setAppState(prev => {
        // Re-calculate what's needed based on previous logic
        return {
          ...prev,
          thinkingAgents: [],
          activeAgent: null,
          needsDocument: true,
        };
      });
    };

    try {
      setChatPhase('processing');
      
      // Step 1: Batch OCR
      const batchResult = await apiClient.extractOcrBatch(sessionId, files);
      const results = batchResult.batch_results || [];
      
      let allPassed = true;
      let failureReason = "";

      for (let i = 0; i < results.length; i++) {
        const res = results[i];
        const docName = files[i].name;
        const extracted = (res.extracted_data && typeof res.extracted_data === 'object') ? res.extracted_data : {};
        const verified = (extracted as any).verified === true;
        
        if (!verified) {
          allPassed = false;
          failureReason += `\n- **${docName}**: ${(extracted as any).ocr_error || 'Identity or type mismatch.'}`;
          continue;
        }

        // Additional checks (Tampering, KYC, Fraud)
        const tamper = await apiClient.checkTampering(sessionId);
        if (tamper.tampered) {
          allPassed = false;
          failureReason += `\n- **${docName}**: Tampering detected.`;
          continue;
        }

        const kyc = await apiClient.kycVerify(sessionId);
        if (kyc.kyc_status === 'failed') {
          allPassed = false;
          failureReason += `\n- **${docName}**: KYC Match Failed (${kyc.issues?.join(', ')})`;
          continue;
        }
      }

      if (!allPassed) {
        failBatch(`Some documents could not be verified:${failureReason}`);
        return;
      }

      // Final Fraud Check 
      const fraud = await apiClient.fraudCheck(sessionId);
      if (fraud.fraud_detected) {
        failBatch(`Fraud signals detected in document bundle: ${fraud.details}`);
        return;
      }

      // SUCCESS
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      pushAgentMessage(`✅ **All ${files.length} documents verified successfully.** Proceeding to underwriting...`);
      
      setAppState(prev => ({
        ...prev,
        thinkingAgents: [],
        activeAgent: null,
        needsDocument: false,
        requiredDocuments: [],
        uploadedDocNames: [...(prev.uploadedDocNames || []), ...files.map(f => f.name)]
      }));

      await runUnderwriting();

    } catch (err) {
      console.error("Batch upload failed:", err);
      failBatch("System error during batch processing.");
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
      thinkingAgents: [...prev.thinkingAgents, 'Document Agent'],
      activeAgent: '📄 Processing Document...'
    }));

    const thinkingId = pushAgentMessage('Running Verification (OCR, Tampering, KYC, Fraud)...', 'thinking');
    
    const failAndKeepUploadZone = (reason: string) => {
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      pushAgentMessage(`❌ **Document Rejected:** ${reason}\n\nPlease upload the correct document.`);
      setAppState(prev => ({
        ...prev,
        thinkingAgents: [],
        activeAgent: null
      }));
    };

    try {
      setChatPhase('processing');
      
      const ocrResult = await apiClient.extractOcr(sessionId, file);
      const docType = ocrResult?.extracted_data?.document_type || 'Unknown';
      const ocrVerified = ocrResult?.extracted_data?.verified === true;
      const confidence = ocrResult?.confidence || 0;
      
      if (!ocrVerified) {
        const ocrError = ocrResult?.extracted_data?.ocr_error || '';
        let reason = ocrError || `Document type "${docType}" could not be verified (confidence: ${(confidence * 100).toFixed(0)}%).`;
        failAndKeepUploadZone(reason);
        return;
      }
      
      const tamperResult = await apiClient.checkTampering(sessionId);
      if (tamperResult?.tampered) {
        failAndKeepUploadZone(`Document appears to be tampered. ${tamperResult.tamper_reason || 'Digital alterations detected.'}`);
        return;
      }

      await apiClient.verifyIncome(sessionId);
      
      const kycResult = await apiClient.kycVerify(sessionId);
      if (kycResult?.kyc_status === 'failed') {
        const issues = kycResult.issues?.join('; ') || 'KYC verification failed.';
        failAndKeepUploadZone(`KYC Failed: ${issues}`);
        return;
      }
      
      const fraudResult = await apiClient.fraudCheck(sessionId);
      if (fraudResult?.fraud_detected) {
        failAndKeepUploadZone(`Fraud signals detected: ${fraudResult.details || 'Suspicious patterns identified.'}`);
        return;
      }
      
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      
      setAppState(prev => {
        const uploadedNames = [...(prev.uploadedDocNames || []), file.name];
        const newRequired = [...(prev.requiredDocuments || [])];
        
        if (newRequired.length > 0) {
          const matchIdx = newRequired.findIndex(d => {
            const dLower = d.toLowerCase();
            const typeLower = (docType || '').toLowerCase();
            return dLower.includes(typeLower) || 
              (typeLower.includes('pan') && dLower.includes('pan')) || 
              (typeLower.includes('aadhaar') && dLower.includes('aadhaar')) || 
              (typeLower.includes('salary') && dLower.includes('income'));
          });
          if (matchIdx >= 0) newRequired.splice(matchIdx, 1);
          else newRequired.shift();
        }
        
        const allUploaded = newRequired.length === 0;
        return {
          ...prev,
          thinkingAgents: [],
          activeAgent: null,
          uploadedDocNames: uploadedNames,
          requiredDocuments: newRequired,
          needsDocument: !allUploaded,
        };
      });
      
      const uploadedSoFar = (appState.uploadedDocNames || []).length + 1;
      const allDocsUploaded = uploadedSoFar >= (appState.requiredDocuments?.length || 0);
      
      if (allDocsUploaded) {
        pushAgentMessage(`✅ **${docType} verified**. All required documents received. Analyzing risk...`);
        await runUnderwriting();
      } else {
        pushAgentMessage(`✅ **${docType} verified**. Please upload the next document.`);
      }

    } catch (err) {
      setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
      pushAgentMessage('Error processing document. Please check backend logs.');
    }
  };

  const loadSession = async (sid: string) => {
    try {
      setSessionId(sid);
      setAppState(prev => ({ ...prev, sessionId: sid, actionLog: [] }));
      const state = await apiClient.getSession(sid);
      const history = await apiClient.getHistory(sid);

      if (state) {
        const sData: AppState = {
          ...INITIAL_APP_STATE,
          sessionId: sid,
          customerName: state.customer_data?.name || '',
          phone: state.customer_data?.phone || '',
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
          loan_terms: state.loan_terms || undefined,
          documents: {
            pan: state.documents?.verified ? 'verified' : 'pending',
            bankStatement: state.documents?.verified ? 'verified' : 'pending',
          },
          pastLoans: state.customer_data?.past_loans,
          salary: state.customer_data?.salary || 0,
          needsDocument: (state.current_phase === 'kyc_verification' || state.current_phase === 'document'),
          requiredDocuments: state.required_documents || [],
          eligible_offers: (state.eligible_offers || []).map((o: any) => ({
            lender_id: o.lender_id || o.id || o.lenderId || o.nbfc_id || o.nbfcId,
            lender_name: o.lender_name || o.name || o.lenderName || o.nbfc_name || o.nbfcName,
            interest_rate: o.interest_rate || o.rate || o.rate_percent || o.r,
            emi: o.emi || o.monthly_payment || 0
          })),
          disbursement_step: state.disbursement_step,
          net_disbursement_amount: state.net_disbursement_amount,
        };
        setAppState(sData);
        if (state.customer_data?.phone) {
          localStorage.setItem('nbfc_customer_phone', state.customer_data.phone);
        }
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

    // Intercept common UI actions: negotiate or request rejection letter
    const normalized = text.trim().toLowerCase();
    if (normalized.includes('negotiate')) {
      await runNegotiation();
      return;
    }

    if ((normalized.includes('rejection') && normalized.includes('letter')) || normalized.includes('download rejection') || normalized.includes('give me rejection')) {
      // Generate rejection letter on demand and render rejection card
      const thinkingId = pushAgentMessage('Generating your rejection letter...', 'thinking');
      try {
        const res = await apiClient.sanction(sessionId);
        // remove thinking indicator
        setChatHistory(prev => prev.filter(m => m.id !== thinkingId));

        const content = res?.message || 'Your rejection letter has been generated. Download below.';
        setChatHistory(prev => [...prev, {
          id: `msg-${Date.now()}-${Math.random()}`,
          sender: 'agent',
          type: 'rejection_letter',
          content,
          timestamp: new Date(),
        }]);
      } catch (err) {
        setChatHistory(prev => prev.filter(m => m.id !== thinkingId));
        pushAgentMessage('Failed to generate rejection letter.', 'text');
      }
      return;
    }

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
          res.all_replies.forEach((m: any) => {
              if (typeof m === 'string') pushAgentMessage(m, 'text');
              else if (m && typeof m === 'object') pushAgentMessage(m.content, m.type);
          });
        } else if (res.reply) {
          pushAgentMessage(res.reply, 'text');
        }
        
        // Update eligible_offers from chat response if available
        if (res.eligible_offers) {
          console.log('App.tsx: Received eligible_offers from chat:', res.eligible_offers);
          setAppState(prev => ({ ...prev, eligible_offers: res.eligible_offers }));
        } else {
          console.log('App.tsx: No eligible_offers in chat response:', Object.keys(res));
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
            loan_terms: fullState.loan_terms || prev.loan_terms,
            salary: fullState.customer_data?.salary || prev.salary,
            eligible_offers: fullState.eligible_offers || prev.eligible_offers || [],
            disbursement_step: fullState.disbursement_step,
            net_disbursement_amount: fullState.net_disbursement_amount,
            needsDocument: (fullState.current_phase === 'kyc_verification' || fullState.current_phase === 'document'),
            requiredDocuments: fullState.required_documents || prev.requiredDocuments,
          }));
        }
      } catch (err) {
        console.error("State sync failed:", err);
      }

      // Update Phase based on intent/decision/next_agent
      try {
        const isDocPhase = fullState?.current_phase === 'kyc_verification' || fullState?.current_phase === 'document';
        const allUploaded = fullState?.documents_uploaded === true;

        if (fullState?.decision === 'soft_reject') {
          setChatPhase('negotiate');
          setAppState(prev => ({ ...prev, needsDocument: false }));
        } else if (isDocPhase && !allUploaded) {
          setChatPhase('document');
          const docs = fullState.required_documents || ["Identity (PAN or Aadhaar)"];
          setAppState(prev => ({ 
            ...prev, 
            needsDocument: true, 
            requiredDocuments: docs,
            documents_uploaded: false
          }));
        } else if (fullState?.current_phase === 'sales' || fullState?.loan_terms?.principal) {
          setChatPhase('loan_details'); 
          setAppState(prev => ({ ...prev, needsDocument: false, documents_uploaded: allUploaded }));
          // Fetch past sessions when user is identified
          if (fullState?.customer_data?.phone) {
            const sessions = await apiClient.getSessionsByPhone(fullState.customer_data.phone);
            setAppState(prev => ({ ...prev, pastSessions: sessions }));
          }
        } else {
          setChatPhase('onboarding');
          setAppState(prev => ({ ...prev, needsDocument: false, documents_uploaded: allUploaded }));
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

  const handlePayEmi = async () => {
    if (!sessionId) return;
    try {
      const res = await apiClient.payEmi(sessionId);
      if (res.success) {
        pushAgentMessage(`✅ ${res.message}`, 'text');
        // State will sync via the PHASE_UPDATE broadcast, but let's force a sync here too
        const fullState = await apiClient.getSession(sessionId);
        if (fullState) {
          setAppState(prev => ({
            ...prev,
            loan_terms: fullState.loan_terms
          }));
        }
      }
    } catch (err) {
      console.error("Payment failed:", err);
      pushAgentMessage("❌ Payment failed. Please try again.", 'text');
    }
  };

  const handleDeleteSession = async (sessionIdToDelete: string) => {
    if (!sessionIdToDelete) return;
    try {
      console.log("🗑️ Attempting to delete session:", sessionIdToDelete);
      await apiClient.deleteSession(sessionIdToDelete);
      
      // Refresh past sessions using phone from appState or localStorage
      const phone = appState.phone || localStorage.getItem('nbfc_customer_phone');
      if (phone) {
        console.log("🔄 Refreshing sessions for phone:", phone);
        const sessions = await apiClient.getSessionsByPhone(phone);
        setAppState(prev => ({ ...prev, pastSessions: sessions }));
      }
      
      // If we deleted the current session, start a new one
      if (sessionIdToDelete === sessionId) {
        handleNewChat();
      }
    } catch (err) {
      console.error("❌ Failed to delete session:", err);
      pushAgentMessage("Error: Failed to delete the chat session.");
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
        onPayEmi={handlePayEmi}
        onDeleteSession={handleDeleteSession}
        onSelectLender={handleSelectLender}
      />
      <ChatPane 
        appState={appState} 
        setAppState={setAppState} 
        chatHistory={chatHistory} 
        onSendMessage={handleSendMessage} 
        onFileUpload={handleFileUpload}
        onBatchFileUpload={handleBatchFileUpload}
      />
    </div>
  );
}

export default App;
