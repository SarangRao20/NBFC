import { useState, useRef, useEffect } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { Bot, User, Send, Sparkles, Loader2, Sliders, CheckCircle2, ArrowRight } from 'lucide-react';
import OnboardingWidget from '../widgets/OnboardingWidget';
import KycWidget from '../widgets/KycWidget';
import OffersWidget from '../widgets/OffersWidget';
import SanctionViewer from '../widgets/SanctionViewer';
import { api } from '../../../lib/api';

interface ChatItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  component?: 'ONBOARDING' | 'KYC' | 'OFFERS' | 'SANCTION';
  timestamp: number;
}

export default function GenUiApplication() {
  const { user, sessionId, setSessionId, loanDetails, setAgentActive, addAgentLog, clearAgentLogs } = useLoanStore();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const firstName = user?.name ? user.name.split(' ')[0] : 'Partner';

  const [chatHistory, setChatHistory] = useState<ChatItem[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content: `Hello ${firstName}. System Intelligence is active. Based on your verified profile (CIBIL: ${user?.creditScore || 785}), you are pre-approved for instant credit facilities with sub-second decisioning. How would you like to structure your capital today?`,
      timestamp: Date.now()
    }
  ]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isTyping]);

  const runAgentStream = async (logs: string[], taskFn: () => Promise<void>) => {
    clearAgentLogs();
    setAgentActive(true);

    for (const log of logs) {
      addAgentLog(log);
      await new Promise((res) => setTimeout(res, 500));
    }

    try {
      await taskFn();
    } catch (e: any) {
      addAgentLog(`❌ Error: ${e.message}`);
    } finally {
      setTimeout(() => setAgentActive(false), 800);
    }
  };

  const handleStartConfigurator = () => {
    setChatHistory((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        role: 'user',
        content: 'I would like to configure my capital parameters.',
        timestamp: Date.now()
      },
      {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Understood. Please adjust your requested principal amount and tenure using the interactive facility configurator below:`,
        component: 'ONBOARDING',
        timestamp: Date.now()
      }
    ]);
  };

  const handleCheckBestTerms = () => {
    setChatHistory((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        role: 'user',
        content: 'Considering my profile, what are the best terms you can provide me?',
        timestamp: Date.now()
      },
      {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Based on your Tier-1 credit score of ${user?.creditScore || 785} and verified income telemetry, your optimal pre-approved facility is ₹5,00,000 at a prime rate of 10.5% p.a. over 36 months (~₹16,250/mo EMI). You can confirm or customize these terms below:`,
        component: 'ONBOARDING',
        timestamp: Date.now()
      }
    ]);
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
        await api.updateLoanParams(activeSessionId, {
          requested_amount: loanDetails.requestedAmount,
          tenure_months: loanDetails.tenureMonths,
        });
      }

      setIsTyping(false);
      setChatHistory((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: `Capital parameters confirmed (Principal: ₹${loanDetails.requestedAmount.toLocaleString('en-IN')}, Tenure: ${loanDetails.tenureMonths} Months). For Vision AI identity verification, please upload your Aadhaar & PAN below:`,
          component: 'KYC',
          timestamp: Date.now()
        }
      ]);
    });
  };

  const handleKycNext = async () => {
    setIsTyping(true);
    await runAgentStream([
      'POST /documents/upload verifying XML signatures...',
      'Invoking Vision AI Agent (OCR & Fraud Verification)...',
      'Bypass Mode Active: Approved Aadhaar & PAN hashes',
      'POST /session/underwrite running Decision Engine...',
      'StateGraph Underwriter: APPROVED for partner disbursal.',
    ], async () => {
      if (sessionId) {
        await api.underwrite(sessionId);
      }

      setIsTyping(false);
      setChatHistory((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: `StateGraph Underwriting Complete! Verified CIBIL Score: ${user?.creditScore || 785}. Evaluated 40,000+ risk vectors across partner lenders. Here are your pre-approved institutional offers:`,
          component: 'OFFERS',
          timestamp: Date.now()
        }
      ]);
    });
  };

  const handleOfferSelect = async (lenderId: string) => {
    setIsTyping(true);
    await runAgentStream([
      `POST /session/select-lender selected partner ${lenderId}...`,
      'Executing Smart Contract & eNACH Mandate...',
      'POST /session/sanction generating PDF Sanction Letter...',
    ], async () => {
      if (sessionId) {
        await api.selectLender(sessionId, { selected_lender_id: lenderId });
        await api.generateSanction(sessionId);
      }

      setIsTyping(false);
      setChatHistory((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: `Facility Approved & Smart Contract Locked! Your official Facility Sanction Letter has been compiled and is available below for digital signature and PDF download:`,
          component: 'SANCTION',
          timestamp: Date.now()
        }
      ]);
    });
  };

  const handleSendUserMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const text = input;
    setInput('');
    
    setChatHistory((prev) => [
      ...prev,
      { id: Date.now().toString(), role: 'user', content: text, timestamp: Date.now() }
    ]);

    setIsTyping(true);
    
    setTimeout(() => {
      setIsTyping(false);
      const lower = text.toLowerCase();

      if (lower.includes('terms') || lower.includes('profile') || lower.includes('best') || lower.includes('rate') || lower.includes('apply') || lower.includes('loan')) {
        setChatHistory((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `Based on your prime CIBIL score of ${user?.creditScore || 785} and monthly income telemetry, your optimal pre-approved facility is ₹5,00,000 at a prime rate of 10.5% p.a. over 36 months (~₹16,250/mo EMI). I have rendered the facility configurator below so you can customize your terms:`,
            component: 'ONBOARDING',
            timestamp: Date.now()
          }
        ]);
      } else {
        setChatHistory((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `I have processed your message regarding "${text}". System Intelligence is ready to assist with facility origination, interest rates, or KYC validation.`,
            timestamp: Date.now()
          }
        ]);
      }
    }, 1000);
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
      default:
        return null;
    }
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl h-[calc(100vh-140px)] flex flex-col overflow-hidden max-w-4xl mx-auto shadow-2xl relative">
      {/* Console Header */}
      <div className="p-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-display font-medium text-white text-sm">System Intelligence Console</h3>
            <p className="text-[10px] text-white/40 uppercase tracking-widest font-mono">LangGraph Multi-Agent Orchestrator</p>
          </div>
        </div>
        <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full flex items-center gap-1.5 font-medium">
          <Sparkles className="w-3.5 h-3.5" /> Generative Agent Active
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
                      : 'bg-[#0A0A0A] text-white/90 border border-white/10 rounded-tl-sm'
                  }`}>
                    {item.content}
                  </div>
                )}

                {/* Initial Action Pills for Quick Interaction */}
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
              <div className="bg-[#0A0A0A] border border-white/10 rounded-2xl rounded-tl-sm px-5 py-4 text-sm shadow-sm flex items-center gap-3">
                <Loader2 className="w-4 h-4 animate-spin text-white/50" />
                <span className="text-white/50 tracking-wide font-mono text-xs uppercase">System Intelligence Reasoning...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} className="h-4" />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSendUserMessage} className="p-4 border-t border-white/10 bg-[#0A0A0A] relative">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask System Intelligence about terms or type your request..."
          className="w-full bg-[#111] border border-white/10 rounded-xl pl-4 pr-12 py-3.5 text-sm text-white focus:outline-none focus:border-white/30 placeholder:text-white/30"
        />
        <button
          type="submit"
          disabled={!input.trim()}
          className="absolute right-6 top-5 text-white/70 hover:text-white disabled:opacity-30 transition-all"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
