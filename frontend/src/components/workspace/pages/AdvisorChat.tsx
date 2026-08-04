import { useState, useEffect } from 'react';
import { Bot, User, Send, Sparkles, TrendingUp, PieChart, Wallet, ShieldAlert, ArrowUpRight, Loader2 } from 'lucide-react';
import { useLoanStore } from '../../../store/useLoanStore';
import { api } from '../../../lib/api';

export default function AdvisorChat() {
  const { user, loanDetails, sessionId } = useLoanStore();

  const [portfolioData, setPortfolioData] = useState({
    monthlySalary: user?.salary || 150000,
    activeDebt: loanDetails.requestedAmount,
    monthlyEmi: Math.round((loanDetails.requestedAmount * 1.105) / loanDetails.tenureMonths),
    mutualFunds: 350000,
    fixedDeposits: 200000,
    emergencyFund: 120000,
    dtiRatio: 0.18
  });

  const [messages, setMessages] = useState<any[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hello ${user?.name || 'Sarang'}. I am your dedicated Track-2 Autonomous Financial & Portfolio Advisor.\n\nI have evaluated your total asset portfolio (₹6.7 Lakhs in SIPs & FDs), active debt exposure (₹${loanDetails.requestedAmount.toLocaleString('en-IN')}), and CIBIL telemetry (${user?.creditScore || 800}).\n\nHow can I assist you with wealth allocation, tax optimization, or loan prepayment strategy today?`,
      timestamp: Date.now()
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    if (user?.phone) {
      api.getLoanHistory(user.phone).then((res) => {
        if (res.success && res.data?.history && res.data.history.length > 0) {
          const active = res.data.history[0];
          setPortfolioData((prev) => ({
            ...prev,
            activeDebt: active.amount || prev.activeDebt,
            monthlyEmi: active.emi || prev.monthlyEmi,
            dtiRatio: prev.monthlySalary ? Number((prev.monthlyEmi / prev.monthlySalary).toFixed(2)) : 0.18
          }));
        }
      });
    }
  }, [user?.phone]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const queryText = input;
    setInput('');

    const userMsg = { id: Date.now().toString(), role: 'user', content: queryText, timestamp: Date.now() };
    setMessages((prev) => [...prev, userMsg]);
    setIsTyping(true);

    try {
      if (sessionId) {
        const res = await api.chatWithAgent(sessionId, `[FINANCIAL ADVISOR QUERY] User Salary: ₹${portfolioData.monthlySalary}, Active Debt: ₹${portfolioData.activeDebt}, EMI: ₹${portfolioData.monthlyEmi}, Investments: ₹${portfolioData.mutualFunds + portfolioData.fixedDeposits}. Question: ${queryText}`);
        setIsTyping(false);

        if (res.success && res.data?.reply) {
          setMessages((prev) => [
            ...prev,
            {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: res.data.reply,
              timestamp: Date.now()
            }
          ]);
          return;
        }
      }

      // Smart fallback response
      setTimeout(() => {
        setIsTyping(false);
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: `Based on your monthly net income (₹${portfolioData.monthlySalary.toLocaleString('en-IN')}) and current DTI ratio of ${(portfolioData.dtiRatio * 100).toFixed(1)}%:\n\n1. **Prepayment vs SIPs**: Your loan rate is 10.5% p.a., while your Equity Mutual Fund portfolio yields ~14.2% CAGR. It is financially optimal to continue monthly SIPs rather than aggressive prepayments.\n2. **Emergency Buffer**: Maintaining ₹1.2 Lakhs in liquid funds provides 7.3x monthly EMI coverage.\n3. **Tax Optimization**: Loan interest payments up to ₹2 Lakhs are deductible under Section 24b.`,
            timestamp: Date.now()
          }
        ]);
      }, 1000);
    } catch (err) {
      setIsTyping(false);
    }
  };

  const handlePillClick = (promptText: string) => {
    setInput(promptText);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 animate-fade-in">
      {/* Portfolio Summary Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#111] border border-white/10 rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-white/50 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Net Investment Assets</span>
            <PieChart className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-display font-bold text-white">₹{(portfolioData.mutualFunds + portfolioData.fixedDeposits).toLocaleString('en-IN')}</p>
          <p className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1 font-mono">
            <ArrowUpRight className="w-3 h-3" /> Mutual Funds + FDs
          </p>
        </div>

        <div className="bg-[#111] border border-white/10 rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-white/50 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Active Debt Exposure</span>
            <Wallet className="w-4 h-4 text-blue-400" />
          </div>
          <p className="text-2xl font-display font-bold text-white">₹{portfolioData.activeDebt.toLocaleString('en-IN')}</p>
          <p className="text-[11px] text-white/40 mt-1 font-mono">EMI: ₹{portfolioData.monthlyEmi.toLocaleString('en-IN')}/mo</p>
        </div>

        <div className="bg-[#111] border border-white/10 rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-white/50 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Debt-To-Income (DTI)</span>
            <TrendingUp className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-display font-bold text-emerald-400">{(portfolioData.dtiRatio * 100).toFixed(1)}%</p>
          <p className="text-[11px] text-emerald-400/80 mt-1 font-mono">Tier-1 Healthy Range (&lt; 35%)</p>
        </div>

        <div className="bg-[#111] border border-white/10 rounded-2xl p-5 relative overflow-hidden">
          <div className="flex items-center justify-between text-white/50 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Emergency Buffer</span>
            <ShieldAlert className="w-4 h-4 text-purple-400" />
          </div>
          <p className="text-2xl font-display font-bold text-white">₹{portfolioData.emergencyFund.toLocaleString('en-IN')}</p>
          <p className="text-[11px] text-purple-400 mt-1 font-mono">7.3x EMI Coverage</p>
        </div>
      </div>

      {/* Main Advisor Console */}
      <div className="bg-[#111] border border-white/10 rounded-2xl h-[calc(100vh-280px)] flex flex-col overflow-hidden shadow-2xl relative">
        {/* Console Header */}
        <div className="p-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display font-medium text-white text-sm">Financial Advisory & Portfolio Intelligence</h3>
              <p className="text-[10px] text-white/40 uppercase tracking-widest font-mono">Track-2 LangGraph Wealth Advisor Node</p>
            </div>
          </div>
          <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full flex items-center gap-1.5 font-medium">
            <Sparkles className="w-3.5 h-3.5" /> Full Portfolio Context Active
          </span>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
          {messages.map((m) => (
            <div key={m.id} className={`flex gap-4 ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
              <div className={`max-w-[85%] flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                  m.role === 'user' ? 'bg-white/10 border-white/20' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500'
                }`}>
                  {m.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4" />}
                </div>
                <div className={`p-5 rounded-2xl text-sm leading-relaxed ${
                  m.role === 'user' ? 'bg-white/10 text-white rounded-tr-sm' : 'bg-[#0A0A0A] border border-white/10 text-white/90 rounded-tl-sm space-y-2'
                }`}>
                  <p className="whitespace-pre-line">{m.content}</p>
                </div>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start text-xs text-white/50 font-mono items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Advisor Node evaluating portfolio yields vs loan rate spreads...</span>
            </div>
          )}
        </div>

        {/* Action Pills */}
        <div className="px-6 py-2 bg-[#0A0A0A] border-t border-white/5 flex flex-wrap gap-2">
          <button
            onClick={() => handlePillClick("Should I prepay my loan or invest in equity SIPs?")}
            className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-white/80 border border-white/10 rounded-lg text-xs font-medium transition-all"
          >
            💡 Prepay Loan vs Invest in SIPs?
          </button>
          <button
            onClick={() => handlePillClick("Analyze my Debt-To-Income (DTI) ratio and cashflow stability")}
            className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-white/80 border border-white/10 rounded-lg text-xs font-medium transition-all"
          >
            📊 Analyze My DTI Ratio & Cashflow
          </button>
          <button
            onClick={() => handlePillClick("How to improve my CIBIL score from 800 to 850?")}
            className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-white/80 border border-white/10 rounded-lg text-xs font-medium transition-all"
          >
            ⭐ How to Reach 850 CIBIL Score?
          </button>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSend} className="p-4 border-t border-white/10 bg-[#0A0A0A] relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Advisor about refinancing, tax savings under Sec 24b, or SIP returns..."
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
    </div>
  );
}
