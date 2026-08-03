import { useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { ArrowRight, Banknote, Calendar } from 'lucide-react';

interface OnboardingWidgetProps {
  onNext?: () => void;
}

export default function OnboardingWidget({ onNext }: OnboardingWidgetProps) {
  const { loanDetails, updateLoanDetails, setState } = useLoanStore();
  const [amount, setAmount] = useState(loanDetails.requestedAmount);
  const [tenure, setTenure] = useState(loanDetails.tenureMonths);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateLoanDetails({ requestedAmount: amount, tenureMonths: tenure });
    setState('DOCUMENT_COLLECTION');
    if (onNext) onNext();
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-xl shadow-xl relative overflow-hidden group">
      <div className="absolute top-0 left-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl group-hover:bg-emerald-500/10 transition-colors" />
      
      <h3 className="text-xl font-display font-medium text-white mb-8 tracking-tight relative z-10 flex items-center gap-2">
        <Banknote className="w-5 h-5 text-emerald-500" />
        Capital Requirements
      </h3>
      
      <form onSubmit={handleSubmit} className="space-y-8 relative z-10">
        <div>
          <div className="flex items-center justify-between mb-4">
            <label className="text-xs font-semibold uppercase tracking-widest text-white/50">Requested Principal</label>
            <span className="font-display text-2xl font-medium tracking-tight text-white">₹{amount.toLocaleString('en-IN')}</span>
          </div>
          <input
            type="range"
            min="50000"
            max="2000000"
            step="10000"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            className="w-full h-1 bg-[#0A0A0A] rounded-lg appearance-none cursor-pointer accent-white"
          />
          <div className="flex justify-between text-xs text-white/30 mt-2 font-medium">
            <span>₹50K</span>
            <span>₹20L</span>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-4">
            <label className="text-xs font-semibold uppercase tracking-widest text-white/50 flex items-center gap-1"><Calendar className="w-3 h-3"/> Tenure</label>
            <span className="font-display text-2xl font-medium tracking-tight text-white">{tenure} Months</span>
          </div>
          <input
            type="range"
            min="6"
            max="60"
            step="6"
            value={tenure}
            onChange={(e) => setTenure(Number(e.target.value))}
            className="w-full h-1 bg-[#0A0A0A] rounded-lg appearance-none cursor-pointer accent-white"
          />
          <div className="flex justify-between text-xs text-white/30 mt-2 font-medium">
            <span>6M</span>
            <span>60M</span>
          </div>
        </div>

        <button 
          type="submit"
          className="w-full mt-6 h-12 bg-white text-black rounded-lg font-medium shadow-lg shadow-white/10 hover:shadow-white/20 hover:scale-[1.02] transition-all flex items-center justify-center gap-2"
        >
          Confirm Parameters
          <ArrowRight className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
