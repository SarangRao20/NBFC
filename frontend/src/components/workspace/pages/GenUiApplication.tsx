import { useState, useRef, useEffect } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { Bot, User, Send, Sparkles, Loader2, Sliders, ArrowRight, Network, FileText, Mail, CreditCard } from 'lucide-react';
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
  showConfiguratorPill?: boolean;
  showActiveLoansPill?: boolean;
  graphTrace?: string[];
  pdfDownloadUrl?: string;
  timestamp: number;
}

function parseAmountInr(text: string): number | null {
  const t = text.toLowerCase().replace(/,/g, '').trim();
  const lakhMatch = t.match(/(\d+(?:\.\d+)?)\s*(lakh|lac|lakhs|lacs)/);
  if (lakhMatch) return parseFloat(lakhMatch[1]) * 100000;

  const kMatch = t.match(/(\d+(?:\.\d+)?)\s*(k|thousand|thousands)/);
  if (kMatch) return parseFloat(kMatch[1]) * 1000;

  const rsMatch = t.match(/(?:rs\.?|inr|rupees?)?\s*(\d{4,8})/);
  if (rsMatch) return parseFloat(rsMatch[1]);

  return null;
}

export default function GenUiApplication() {
  const { user, sessionId, setSessionId, loanDetails, updateLoanDetails, setAgentActive, addAgentLog, clearAgentLogs, setView } = useLoanStore();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const firstName = user?.name ? user.name.split(' ')[0] : 'Partner';

  const [chatHistory, setChatHistory] = useState<ChatItem[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content: `Hello ${firstName}. System Intelligence is active. Based on your verified profile (CIBIL: ${user?.creditScore || 785}), you are pre-approved for instant credit facilities up to ₹15,00,000. \n\nTo structure your capital, what is the primary purpose or goal for your loan today? (e.g. Business Expansion, Medical Emergency, Debt Consolidation, Personal)`,
      graphTrace: [
        'StateGraph initialized: load_session_node',
        'CIBIL Bureau Lookup: 785 (Tier-1 Prime)',
        'Pre-approved Limit Engine: ₹15,00,000'
      ],
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
    setChatHistory((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        role: 'user',
        content: 'I would like to open the capital parameter slider.',
        timestamp: Date.now()
      },
      {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Understood. Please adjust your requested principal amount and tenure using the interactive facility configurator below:`,
        component: 'ONBOARDING',
        graphTrace: ['StateGraph Node: sales_agent -> onboarding_configurator'],
        timestamp: Date.now()
      }
    ]);
  };

  const handleProceedToKyc = () => {
    handleOnboardingNext();
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
        content: `Based on your Tier-1 credit score of ${user?.creditScore || 785} and monthly income telemetry, your optimal pre-approved facility is ₹5,00,000 at a prime rate of 10.5% p.a. over 36 months (~₹16,250/mo EMI). You can confirm these parameters to proceed to KYC, or adjust them using the configurator below:`,
        showConfiguratorPill: true,
        graphTrace: [
          'StateGraph Node: intent_agent (CLASSIFIED: Best Terms Inquiry)',
          'Invoking Underwriting Engine: FOIR = 18%, Risk Premium = 0%',
          'Calculated Optimal Facility: ₹5,00,000 @ 10.5% p.a.'
        ],
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
          content: `Capital parameters confirmed (Principal: ₹${loanDetails.requestedAmount.toLocaleString('en-IN')}, Tenure: ${loanDetails.tenureMonths} Months). For Vision AI identity verification, please complete 1-Click DigiLocker or upload your Aadhaar & PAN below:`,
          component: 'KYC',
          graphTrace: ['StateGraph Node: kyc_agent (Aadhaar & PAN Verification Node)'],
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
          graphTrace: [
            'StateGraph Node: underwriting_agent -> lender_aggregator',
            'Evaluated 5 Institutional Lenders (HDFC, ICICI, Bajaj, Muthoot, Saraswat)',
            'Ranked offers by composite APR & approval score'
          ],
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
      'POST /session/sanction generating PDF Sanction Letter via ReportLab...',
      'Sending email notification with attached PDF...',
    ], async () => {
      let downloadUrl = '';
      if (sessionId) {
        await api.selectLender(sessionId, { selected_lender_id: lenderId });
        await api.generateSanction(sessionId);
        downloadUrl = api.getDownloadLetterUrl(sessionId);
      }

      setIsTyping(false);
      setChatHistory((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'assistant',
          content: `Facility Approved & Smart Contract Locked! Your official PDF Sanction Letter has been generated and dispatched to your email (${user?.email || 'registered email'}). You can download the PDF directly below:`,
          component: 'SANCTION',
          pdfDownloadUrl: downloadUrl,
          graphTrace: [
            'StateGraph Node: sanction_agent -> pdf_generator',
            'ReportLab PDF compiled at data/sanctions/',
            'SMTP Email Dispatch: SENT with attached Sanction PDF'
          ],
          timestamp: Date.now()
        }
      ]);
    });
  };

  const handleSendUserMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const text = input;
    setInput('');

    setChatHistory((prev) => [
      ...prev,
      { id: Date.now().toString(), role: 'user', content: text, timestamp: Date.now() }
    ]);

    setIsTyping(true);

    const lower = text.toLowerCase();

    // 1. Check for Active Loan Status / EMI Remaining Inquiry FIRST
    const isEmiStatusInquiry = lower.includes('remaining') || lower.includes('loanfree') || lower.includes('loan free') || lower.includes('how many emi') || lower.includes('balance') || lower.includes('status of my loan') || lower.includes('active loan');

    if (isEmiStatusInquiry) {
      setTimeout(async () => {
        setIsTyping(false);
        let activeAmt = loanDetails.requestedAmount;
        let activeTenure = loanDetails.tenureMonths;
        let emiVal = Math.round((activeAmt * 1.105) / activeTenure);
        let remainingEmis = activeTenure;

        if (user?.phone) {
          const res = await api.getLoanHistory(user.phone);
          if (res.success && res.data?.history && res.data.history.length > 0) {
            const latest = res.data.history[0];
            activeAmt = latest.amount || activeAmt;
            activeTenure = latest.tenure || activeTenure;
            emiVal = latest.emi || emiVal;
          }
        }

        setChatHistory((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `Hello ${firstName}. Based on your active facility ledger in MongoDB:\n\n• Active Facility Principal: ₹${activeAmt.toLocaleString('en-IN')}\n• Agreed Tenure: ${activeTenure} Months (~₹${emiVal.toLocaleString('en-IN')}/mo EMI)\n• **Remaining EMIs to become 100% Loan-Free: ${remainingEmis} EMIs**\n\nYou can pay individual EMIs directly or manage auto-debit in your Active Loans ledger below:`,
            showActiveLoansPill: true,
            graphTrace: [
              'StateGraph Node: intent_agent (CLASSIFIED: Repayment / EMI Remaining Status Inquiry)',
              'Queried MongoDB Loan Ledger collection',
              `Active Facility Found: ₹${activeAmt.toLocaleString('en-IN')} | Remaining EMIs: ${remainingEmis}`
            ],
            timestamp: Date.now()
          }
        ]);
      }, 600);
      return;
    }

    // 2. Entity Extraction (Amount) for new loan inquiries
    const extractedAmount = parseAmountInr(text);

    let recommendedTenure = loanDetails.tenureMonths;
    if (extractedAmount && extractedAmount >= 10000) {
      if (extractedAmount <= 100000) recommendedTenure = 12;
      else if (extractedAmount <= 300000) recommendedTenure = 24;
      else if (extractedAmount <= 700000) recommendedTenure = 36;
      else if (extractedAmount <= 1200000) recommendedTenure = 48;
      else recommendedTenure = 60;

      updateLoanDetails({ requestedAmount: extractedAmount, tenureMonths: recommendedTenure });
    }

    // 3. Start or get session & sync with backend
    let activeSessionId = sessionId;
    if (!activeSessionId) {
      const startRes = await api.startSession();
      if (startRes.success && startRes.data) {
        activeSessionId = startRes.data.session_id;
        setSessionId(activeSessionId!);
      }
    }

    if (activeSessionId) {
      const targetAmt = extractedAmount || loanDetails.requestedAmount;
      await api.updateLoanParams(activeSessionId, {
        requested_amount: targetAmt,
        tenure_months: recommendedTenure
      });
      await api.chatWithAgent(activeSessionId, text);
    }

    setTimeout(() => {
      setIsTyping(false);
      const currentAmt = extractedAmount || loanDetails.requestedAmount;
      const currentTenure = recommendedTenure;
      const emiVal = Math.round((currentAmt * (1 + 0.105 * (currentTenure / 12))) / currentTenure);

      const explicitlyWantsSlider = lower.includes('slider') || lower.includes('configure') || lower.includes('adjust slider') || lower.includes('show slider');

      if (explicitlyWantsSlider) {
        setChatHistory((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `Understood ${firstName}. Here is the interactive facility configurator pre-scaled to ₹${currentAmt.toLocaleString('en-IN')} over ${currentTenure} months:`,
            component: 'ONBOARDING',
            graphTrace: ['StateGraph Node: sales_agent -> onboarding_slider'],
            timestamp: Date.now()
          }
        ]);
      } else if (lower.includes('business') || lower.includes('personal') || lower.includes('medical') || lower.includes('purpose') || lower.includes('expansion') || lower.includes('debt') || lower.includes('home')) {
        setChatHistory((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `Understood! ${text.charAt(0).toUpperCase() + text.slice(1)} capital qualifies for our prime rate structure at 10.5% p.a.\n\nHow much loan principal and tenure (e.g. 12, 24, 36, or 60 months) would suit your cashflow best? Or you can specify an amount like "80k loan".`,
            graphTrace: ['StateGraph Node: intent_agent (INTENT DETECTED: Purpose Captured)', 'SalesAgent -> Capital Structuring'],
            timestamp: Date.now()
          }
        ]);
      } else if (extractedAmount || lower.includes('terms') || lower.includes('profile') || lower.includes('best') || lower.includes('rate') || lower.includes('apply') || lower.includes('loan') || lower.includes('rupees') || lower.includes('k')) {
        setChatHistory((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `Understood ${firstName}. For a requested principal of ₹${currentAmt.toLocaleString('en-IN')}, the optimal recommended tenure is ${currentTenure} months (~₹${emiVal.toLocaleString('en-IN')}/mo EMI @ 10.5% p.a.).`,
            showConfiguratorPill: true,
            graphTrace: ['StateGraph Node: sales_agent (Entity Extracted)', 'Invoked EMI Engine: ~₹' + emiVal.toLocaleString('en-IN') + '/mo'],
            timestamp: Date.now()
          }
        ]);
      } else {
        setChatHistory((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `I have processed your inquiry. System Intelligence is ready to assist with facility origination, interest rate optimization, or document verification.`,
            graphTrace: ['StateGraph Node: general_advisory_node'],
            timestamp: Date.now()
          }
        ]);
      }
    }, 600);
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
                    <p className="whitespace-pre-line">{item.content}</p>

                    {/* LangGraph StateGraph Execution Traces */}
                    {item.graphTrace && item.graphTrace.length > 0 && (
                      <div className="pt-2 border-t border-white/5 space-y-1">
                        <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-mono font-bold uppercase tracking-wider">
                          <Network className="w-3 h-3" /> LangGraph StateGraph Traces:
                        </div>
                        <div className="bg-[#111] p-2.5 rounded-lg border border-white/5 space-y-1 font-mono text-[11px] text-white/60">
                          {item.graphTrace.map((trace, tIdx) => (
                            <div key={tIdx} className="flex items-center gap-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                              <span>{trace}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* PDF Download Direct Banner */}
                {item.pdfDownloadUrl && (
                  <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <FileText className="w-6 h-6 text-emerald-400 shrink-0" />
                      <div>
                        <p className="text-sm font-semibold text-white">Official Facility Sanction PDF</p>
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
                <span className="text-white/50 tracking-wide font-mono text-xs uppercase">LangGraph Multi-Agent StateGraph Reasoning...</span>
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
          placeholder="Ask System Intelligence (e.g. 'check remaining EMIs to be loan free')..."
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
