import { useState, useRef, useEffect } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import type { ChatMessage } from '../../../store/useLoanStore';
import { Bot, User, Send, Sparkles, Sliders, ArrowRight, FileText, Mail, CreditCard, BarChart3 } from 'lucide-react';
import OnboardingWidget from '../widgets/OnboardingWidget';
import KycWidget from '../widgets/KycWidget';
import OffersWidget from '../widgets/OffersWidget';
import SanctionViewer from '../widgets/SanctionViewer';
import ShapWidget from '../widgets/ShapWidget';
import GraphVisualizer from '../widgets/GraphVisualizer';
import AgentTypingIndicator from '../../AgentTypingIndicator';
import { api } from '../../../lib/api';


export default function GenUiApplication() {
  const { user, sessionId, setSessionId, loanDetails, updateLoanDetails, setAgentActive, addAgentLog, clearAgentLogs, setView, setState: setAppState, chatHistory, addChatMessage, setChatHistory } = useLoanStore();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [currentPhase, setCurrentPhase] = useState('load_session');
  const [nextAgent, setNextAgent] = useState<string | undefined>(undefined);
  const bottomRef = useRef<HTMLDivElement>(null);

  const firstName = user?.name ? user.name.split(' ')[0] : 'Partner';
  const preApprovedLimit = user?.preApprovedLimit ?? 1500000;
  const creditScore = user?.creditScore ?? 785;

  // Initialize welcome message once if chat is empty
  useEffect(() => {
    if (chatHistory.length === 0) {
      addChatMessage({
        id: 'init-1',
        role: 'assistant',
        content: `Hello ${firstName}. System Intelligence is active. Based on your verified profile (CIBIL: ${creditScore}), you are pre-approved for instant credit facilities up to ₹${preApprovedLimit.toLocaleString('en-IN')}.\n\nTo structure your capital, what is the primary purpose or goal for your loan today? (e.g. Business Expansion, Medical Emergency, Debt Consolidation, Personal)`,
        graphTrace: [
          'StateGraph initialized: load_session_node',
          `CIBIL Bureau Lookup: ${creditScore}`,
          `Pre-approved Limit Engine: ₹${preApprovedLimit.toLocaleString('en-IN')}`
        ],
        timestamp: Date.now()
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isTyping]);

  useEffect(() => {
    if (sessionId && chatHistory.length <= 1) {
      // Only restore from backend if we have no real conversation yet (just the welcome msg)
      api.getChatHistory(sessionId).then((res) => {
        if (res.success && res.data?.history && res.data.history.length > 0) {
          const loadedMsgs: ChatMessage[] = res.data.history.map((m: any, idx: number) => ({
            id: `restored-${idx}`,
            role: m.role === 'user' || m.type === 'human' ? 'user' : 'assistant',
            content: m.content || m.text || '',
            graphTrace: m.graphTrace || ['StateGraph Node: session_restored'],
            timestamp: Date.now()
          }));
          if (loadedMsgs.length > 0) {
            setChatHistory(loadedMsgs);
          }
        }
      });
    }
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  const runAgentStream = async (logs: string[], taskFn: () => Promise<void>) => {
    clearAgentLogs();
    setAgentActive(true);

    for (const log of logs) {
      addAgentLog(log);
      await new Promise((res) => setTimeout(res, 350));
    }

    try {
      await taskFn();
    } catch (e: any) {
      addAgentLog(`❌ Error: ${e.message}`);
    } finally {
      setTimeout(() => setAgentActive(false), 500);
    }
  };

  const handleStartConfigurator = () => {
    addChatMessage({ id: Date.now().toString(), role: 'user', content: 'I would like to open the capital parameter slider.', timestamp: Date.now() });
    addChatMessage({ id: (Date.now() + 1).toString(), role: 'assistant', content: 'Understood. Please adjust your requested principal amount and tenure using the interactive facility configurator below:', component: 'ONBOARDING', graphTrace: ['StateGraph Node: sales_agent -> onboarding_configurator'], timestamp: Date.now() });
  };

  const handleProceedToKyc = () => {
    handleOnboardingNext();
  };

  const handleCheckBestTerms = () => {
    // Use actual user profile data — creditScore and preApprovedLimit from store
    const optimalAmount = Math.min(preApprovedLimit, 500000);
    const r = 10.5 / 100 / 12;
    const n = 36;
    const optimalEmi = Math.round(optimalAmount * r * Math.pow(1 + r, n) / (Math.pow(1 + r, n) - 1));
    addChatMessage({ id: Date.now().toString(), role: 'user', content: 'Considering my profile, what are the best terms you can provide me?', timestamp: Date.now() });
    addChatMessage({
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: `Based on your credit score of ${creditScore} and monthly income, your optimal pre-approved facility is ₹${optimalAmount.toLocaleString('en-IN')} at a prime rate of 10.5% p.a. over 36 months (~₹${optimalEmi.toLocaleString('en-IN')}/mo EMI). You can confirm these parameters to proceed to KYC, or adjust them using the configurator below:`,
      showConfiguratorPill: true,
      graphTrace: [
        `StateGraph Node: intent_agent (CLASSIFIED: Best Terms Inquiry)`,
        `CIBIL Score: ${creditScore}`,
        `Pre-approved Limit: ₹${preApprovedLimit.toLocaleString('en-IN')}`,
      ],
      timestamp: Date.now()
    });
  };

  const handleShowShap = () => {
    addChatMessage({ id: Date.now().toString(), role: 'user', content: 'Explain my underwriting pricing using SHAP feature contributions.', timestamp: Date.now() });
    addChatMessage({ id: (Date.now() + 1).toString(), role: 'assistant', content: 'Here is the SHAP Feature Importance Waterfall showing exactly how your credit score, income levels, debt obligations, and location metrics contributed to your final approved interest rate:', component: 'SHAP', graphTrace: ['StateGraph Node: underwriting_agent -> shap_explainer_mcp'], timestamp: Date.now() });
  };


  const handleOnboardingNext = async () => {
    setIsTyping(true);
    await runAgentStream([
      'POST /session/start initializing StateGraph workflow...',
      'Invoking Sales Agent (LangGraph node)...',
      'POST /sales/capture-loan-params calculating DTI & FOIR...',
      'Parameters updated in MongoDB session state.',
    ], async () => {
      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const startRes = await api.startSession();
        if (startRes.success && startRes.data) {
          activeSessionId = startRes.data.session_id;
          setSessionId(activeSessionId!);
        }
      }

      if (activeSessionId) {
        // Don't push default loan terms — let the sales agent collect via chat
        await api.updateLoanParams(activeSessionId, {
          requested_amount: 0,  // signal: values not yet set
          tenure_months: 0,
        });
      }

      setIsTyping(false);
      addChatMessage({ id: Date.now().toString(), role: 'assistant', content: `Capital parameters confirmed (Principal: ₹${loanDetails.requestedAmount.toLocaleString('en-IN')}, Tenure: ${loanDetails.tenureMonths} Months). For Vision AI identity verification, please complete 1-Click DigiLocker or upload your Aadhaar & PAN below:`, component: 'KYC', graphTrace: ['StateGraph Node: kyc_agent (Aadhaar & PAN Verification Node)'], timestamp: Date.now() });
    });
  };

  const handleKycNext = async () => {
    setIsTyping(true);
    await runAgentStream([
      'POST /documents/upload verifying XML signatures...',
      'Invoking Vision AI Agent (OCR & Fraud Verification)...',
      'POST /session/underwrite running Decision Engine...',
    ], async () => {
      let decision = 'approve';
      let downloadUrl = '';
      if (sessionId) {
        const underRes = await api.underwrite(sessionId);
        decision = underRes.data?.decision || 'approve';
        if (decision === 'reject' || decision === 'hard_reject' || decision === 'soft_reject') {
          const sanRes = await api.generateSanction(sessionId);
          if (sanRes.success) downloadUrl = api.getDownloadLetterUrl(sessionId);
        }
      }

      setIsTyping(false);

      if (decision === 'reject' || decision === 'hard_reject' || decision === 'soft_reject') {
        addChatMessage({ id: Date.now().toString(), role: 'assistant', content: `We regret to inform you that your application could not be approved at this amount. The underwriting engine has flagged the request — see the decision explainability below, and the official rejection letter has been dispatched to your email (${user?.email || 'registered email'}):`, component: 'SHAP', pdfDownloadUrl: downloadUrl, pdfLabel: 'Official Rejection Letter', timestamp: Date.now() });
      } else {
        addChatMessage({ id: Date.now().toString(), role: 'assistant', content: `Underwriting complete. CIBIL Score: ${creditScore}. Here are your pre-approved institutional offers:`, component: 'OFFERS', showShapPill: true, timestamp: Date.now() });
      }
    });
  };

  const handleOfferSelect = async (lenderId: string) => {
    setIsTyping(true);
    await runAgentStream([
      `POST /session/select-lender selected partner ${lenderId}...`,
      'Running underwriting decision engine...',
      'Compiling final decision & letter...',
    ], async () => {
      let downloadUrl = '';
      let decision = 'approve';
      if (sessionId) {
        const selRes = await api.selectLender(sessionId, { selected_lender_id: lenderId });
        decision = selRes.data?.decision || 'approve';
        if (decision === 'approve' || decision === 'reject' || decision === 'hard_reject') {
          const sanRes = await api.generateSanction(sessionId);
          if (sanRes.success) downloadUrl = api.getDownloadLetterUrl(sessionId);
        }
      }

      setIsTyping(false);

      if (decision === 'approve') {
        setAppState('ACTIVE_LOAN');
        addChatMessage({ id: (Date.now() + 1).toString(), role: 'assistant', content: `Facility Approved & Sanction Letter generated! Dispatched to ${user?.email || 'your registered email'}. Download below:`, component: 'SANCTION', pdfDownloadUrl: downloadUrl, pdfLabel: 'Official Facility Sanction PDF', timestamp: Date.now() });
      } else if (decision === 'pending_docs') {
        addChatMessage({ id: (Date.now() + 1).toString(), role: 'assistant', content: 'Your requested amount exceeds your instant pre-approved limit, so additional income verification is required. Please upload your salary slip below:', component: 'KYC', timestamp: Date.now() });
      } else {
        addChatMessage({ id: (Date.now() + 1).toString(), role: 'assistant', content: `We regret to inform you that your application could not be approved at this amount. The underwriting engine has flagged the request — see the decision explainability below, and the official rejection letter has been dispatched to ${user?.email || 'your registered email'}:`, component: 'SHAP', pdfDownloadUrl: downloadUrl, pdfLabel: 'Official Rejection Letter', timestamp: Date.now() });
      }
    });
  };

  const handleSendUserMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const text = input;
    setInput('');

    addChatMessage({ id: Date.now().toString(), role: 'user', content: text, timestamp: Date.now() });
    setIsTyping(true);

    // 1. Ensure active backend session
    let activeSessionId = sessionId;
    if (!activeSessionId) {
      const startRes = await api.startSession();
      if (startRes.success && startRes.data) {
        activeSessionId = startRes.data.session_id;
        setSessionId(activeSessionId!);
      }
    }

    // 2. Pass message directly to Backend LangGraph StateGraph & LLM NLP Classifier
    try {
      const chatRes = await api.chatWithAgent(activeSessionId!, text);
      setIsTyping(false);

      if (chatRes.success && chatRes.data) {
        const backendReply = chatRes.data.reply || 'Understood.';
        const intent = chatRes.data.intent || 'general';
        const phase = chatRes.data.current_phase || 'active';

        // Update DAG visualizer state
        setCurrentPhase(phase);
        if (chatRes.data.next_agent) setNextAgent(chatRes.data.next_agent);

        // Update local loan details if returned from backend NLP extraction
        if (chatRes.data.loan_terms?.principal) {
          updateLoanDetails({
            requestedAmount: chatRes.data.loan_terms.principal,
            tenureMonths: chatRes.data.loan_terms.tenure || loanDetails.tenureMonths,
            ...(chatRes.data.loan_terms.interest_rate && { interestRate: chatRes.data.loan_terms.interest_rate }),
            ...(chatRes.data.loan_terms.emi && { monthlyEmi: Math.round(chatRes.data.loan_terms.emi) }),
            ...(chatRes.data.loan_terms.principal && { sanctionedAmount: chatRes.data.loan_terms.principal }),
          });
        }

        // Build graph execution traces (shown as subtle chips above message)
        const graphTraces: string[] = [
          `intent_agent → ${intent.toUpperCase()}`,
          `phase: ${phase}`,
        ];
        if (chatRes.data.next_agent) graphTraces.push(`→ ${chatRes.data.next_agent}`);
        if (chatRes.data.loan_terms?.emi) graphTraces.push(`EMI ₹${Math.round(chatRes.data.loan_terms.emi).toLocaleString('en-IN')}/mo`);
        // Append trace spans as human-readable timing labels
        (chatRes.data.trace_events || []).forEach((span: any) => {
          if (span.node && span.duration_ms != null) {
            graphTraces.push(`${span.node} ${span.duration_ms}ms${span.success === false ? ' ✗' : ''}`);
          }
        });

        const lowerText = text.toLowerCase();
        const explicitlyWantsSlider = lowerText.includes('slider') || lowerText.includes('configure') || lowerText.includes('adjust slider');
        const wantsShap = lowerText.includes('shap') || lowerText.includes('explain') || lowerText.includes('why') || lowerText.includes('rationale') || lowerText.includes('decision');
        
        // Deterministic UI trigger from LangGraph backend (Industry Standard: Tool Calling / Structured States)
        const pendingQuestion = chatRes.data.pending_question;
        const isConfirmingTerms = pendingQuestion === 'confirmation' || explicitlyWantsSlider;

        const isEmiStatus = intent === 'payment' || lowerText.includes('remaining') || lowerText.includes('loanfree') || lowerText.includes('loan free') || lowerText.includes('balance') || lowerText.includes('status');
        const isRejected = ['reject', 'hard_reject', 'soft_reject'].includes(chatRes.data.decision);
        const isApproved = chatRes.data.decision === 'approve';
        const isPendingDocs = chatRes.data.decision === 'pending_docs';
        const hasOffers = Array.isArray(chatRes.data.eligible_offers) && chatRes.data.eligible_offers.length > 0;
        const needsKyc = Array.isArray(chatRes.data.required_documents) && chatRes.data.required_documents.length > 0 && !chatRes.data.documents_uploaded;

        // Render the matching premium widget from backend LangGraph structured state (not raw markdown)
        const component =
          isApproved ? 'SANCTION'
          : isRejected || wantsShap ? 'SHAP'
          : isPendingDocs || needsKyc ? 'KYC'
          : hasOffers ? 'OFFERS'
          : explicitlyWantsSlider ? 'ONBOARDING'
          : undefined;

        addChatMessage({ id: (Date.now() + 1).toString(), role: 'assistant', content: backendReply, component, showConfiguratorPill: isConfirmingTerms, showActiveLoansPill: isEmiStatus, graphTrace: graphTraces, timestamp: Date.now() });
      } else {
        addChatMessage({ id: (Date.now() + 1).toString(), role: 'assistant', content: chatRes.error ? `Sorry, I ran into an issue: ${chatRes.error}. Please try again.` : 'Something went wrong. Please try again.', graphTrace: ['StateGraph Node: master_router'], timestamp: Date.now() });
      }
    } catch (err: any) {
      setIsTyping(false);
      addChatMessage({ id: (Date.now() + 1).toString(), role: 'assistant', content: `Connection error: ${err?.message || 'Unable to reach the server.'}. Please check your connection and try again.`, graphTrace: ['StateGraph Node: master_router (error)'], timestamp: Date.now() });
    }
  };

  const renderComponent = (compName?: string) => {
    switch (compName) {
      case 'ONBOARDING':
        return <OnboardingWidget onNext={handleOnboardingNext} />;
      case 'KYC':
        return <KycWidget onNext={handleKycNext} />;
      case 'OFFERS':
        return <OffersWidget onSelect={handleOfferSelect} />;
      case 'SANCTION':
        return <SanctionViewer />;
      case 'SHAP':
        return <ShapWidget />;
      default:
        return null;
    }
  };

  // ── Inline markdown: bold + bullets only — no dangerouslySetInnerHTML ──────
  const renderBoldSegments = (line: string) => {
    const parts = line.split(/\*\*(.*?)\*\*/g);
    return parts.map((part, i) =>
      i % 2 === 1 ? <strong key={i}>{part}</strong> : <span key={i}>{part}</span>
    );
  };

  const renderMarkdown = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, i) => {
      if (line.match(/^[•\-\*]\s/)) {
        const content = line.replace(/^[•\-\*]\s/, '');
        return (
          <div key={i} className="flex gap-2 items-start my-0.5">
            <span className="mt-[7px] w-1.5 h-1.5 rounded-full bg-emerald-500/60 shrink-0" />
            <span>{renderBoldSegments(content)}</span>
          </div>
        );
      }
      if (line.trim() === '') return <div key={i} className="h-1.5" />;
      return <p key={i} className="leading-relaxed">{renderBoldSegments(line)}</p>;
    });
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-140px)] w-full">

      {/* ── Main Chat Card (restored original structure) ─────────────── */}
      <div className="flex-1 bg-[#111] border border-white/10 rounded-2xl flex flex-col overflow-hidden shadow-2xl relative">

        {/* Console Header */}
        <div className="p-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display font-medium text-white text-sm">System Intelligence Console</h3>
              <p className="text-[10px] text-white/40 uppercase tracking-widest font-mono">LangGraph Multi-Agent Orchestrator DAG</p>
            </div>
          </div>
          <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full flex items-center gap-1.5 font-medium">
            <Sparkles className="w-3.5 h-3.5" /> Generative StateGraph Active
          </span>
        </div>

        {/* Chat Stream Feed */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 scroll-smooth">
          {chatHistory.map((item) => (
            <div key={item.id} className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
              <div className={`max-w-[90%] flex gap-4 ${item.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                  item.role === 'user' ? 'bg-white/10 border-white/20' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500'
                }`}>
                  {item.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4" />}
                </div>

                <div className="space-y-4 min-w-0 flex-1">
                  {item.content && (
                    <div className={`px-5 py-4 text-[15px] leading-relaxed rounded-2xl ${
                      item.role === 'user'
                        ? 'bg-white/10 text-white rounded-tr-sm border border-white/5'
                        : 'bg-[#0A0A0A] text-white/90 border border-white/10 rounded-tl-sm space-y-3'
                    }`}>
                      {item.role === 'assistant'
                        ? renderMarkdown(item.content)
                        : <p className="whitespace-pre-line">{item.content}</p>
                      }
                    </div>
                  )}

                  {/* PDF Download Direct Banner */}
                  {item.pdfDownloadUrl && (
                    <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <FileText className="w-6 h-6 text-emerald-400 shrink-0" />
                        <div>
                          <p className="text-sm font-semibold text-white">{item.pdfLabel || 'Official Facility Sanction PDF'}</p>
                          <p className="text-xs text-emerald-400 flex items-center gap-1 mt-0.5">
                            <Mail className="w-3 h-3" /> Dispatched to {user?.email || 'email'}
                          </p>
                        </div>
                      </div>
                      <a
                        href={item.pdfDownloadUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="px-4 py-2 bg-white text-black font-semibold rounded-lg text-xs hover:bg-white/90 transition-all shrink-0"
                      >
                        Download PDF →
                      </a>
                    </div>
                  )}

                  {/* Initial Action Pills */}
                  {item.id === 'init-1' && chatHistory.length === 1 && (
                    <div className="flex flex-wrap gap-3 pt-2">
                      <button
                        onClick={handleCheckBestTerms}
                        className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl text-xs font-medium hover:bg-emerald-500/20 transition-all flex items-center gap-2"
                      >
                        <Sparkles className="w-3.5 h-3.5" /> Check Best Terms for My Profile
                      </button>
                      <button
                        onClick={handleStartConfigurator}
                        className="px-4 py-2 bg-white/5 border border-white/10 text-white/80 rounded-xl text-xs font-medium hover:bg-white/10 transition-all flex items-center gap-2"
                      >
                        <Sliders className="w-3.5 h-3.5" /> Configure Capital Slider
                      </button>
                    </div>
                  )}

                  {item.showConfiguratorPill && (
                    <div className="flex flex-wrap gap-3 pt-1">
                      <button
                        onClick={handleProceedToKyc}
                        className="px-4 py-2 bg-white text-black rounded-xl text-xs font-semibold hover:bg-white/90 transition-all flex items-center gap-2"
                      >
                        Confirm Terms & Proceed to KYC <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={handleStartConfigurator}
                        className="px-4 py-2 bg-white/5 border border-white/10 text-white/80 rounded-xl text-xs font-medium hover:bg-white/10 transition-all flex items-center gap-2"
                      >
                        <Sliders className="w-3.5 h-3.5" /> Adjust Parameters Slider
                      </button>
                    </div>
                  )}

                  {item.showActiveLoansPill && (
                    <div className="flex flex-wrap gap-3 pt-1">
                      <button
                        onClick={() => setView('ACTIVE_LOANS')}
                        className="px-4 py-2 bg-emerald-500 text-black rounded-xl text-xs font-semibold hover:bg-emerald-400 transition-all flex items-center gap-2"
                      >
                        <CreditCard className="w-3.5 h-3.5" /> View Active Loans & Repayment Ledger →
                      </button>
                    </div>
                  )}

                  {item.showShapPill && (
                    <div className="flex flex-wrap gap-3 pt-1">
                      <button
                        onClick={handleShowShap}
                        className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl text-xs font-semibold hover:bg-emerald-500/20 transition-all flex items-center gap-2"
                      >
                        <BarChart3 className="w-3.5 h-3.5" /> Explain Underwriting Decision (SHAP) →
                      </button>
                    </div>
                  )}

                  {item.component && (
                    <div className="w-full">
                      {renderComponent(item.component)}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start animate-fade-in">
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border bg-emerald-500/10 border-emerald-500/30 text-emerald-500">
                  <Bot className="w-4 h-4" />
                </div>
                <AgentTypingIndicator />
              </div>
            </div>
          )}
          <div ref={bottomRef} className="h-4" />
        </div>

        {/* Input Form */}
        <form onSubmit={handleSendUserMessage} className="p-4 border-t border-white/10 bg-[#0A0A0A] relative shrink-0">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isTyping}
            placeholder="Ask System Intelligence (e.g. 'check remaining EMIs to be loan free')..."
            className="w-full bg-[#111] border border-white/10 rounded-xl pl-4 pr-12 py-3.5 text-sm text-white focus:outline-none focus:border-white/30 placeholder:text-white/30 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!input.trim() || isTyping}
            className="absolute right-6 top-5 text-white/70 hover:text-white disabled:opacity-30 transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

      {/* ── Right: Live DAG Visualizer (lg+) ─────────────────────── */}
      <div className="hidden lg:flex w-72 xl:w-80 shrink-0">
        <GraphVisualizer
          currentPhase={currentPhase}
          nextAgent={nextAgent}
          isStreaming={isTyping}
        />
      </div>

    </div>
  );
}
