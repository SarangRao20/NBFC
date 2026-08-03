import { useLoanStore } from '../../../store/useLoanStore';
import { AlertTriangle, TrendingDown, ArrowRight } from 'lucide-react';

export default function RejectionWidget() {
  const { loanDetails } = useLoanStore();
  const emi = Math.round((loanDetails.requestedAmount * 1.105) / loanDetails.tenureMonths);

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-xl shadow-xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/5 rounded-full blur-3xl" />
      
      <div className="flex items-center gap-2 mb-6">
         <AlertTriangle className="w-5 h-5 text-red-500" />
         <h3 className="text-xl font-display font-medium text-white tracking-tight relative z-10">
           SHAP Risk Analysis
         </h3>
      </div>
      
      <div className="space-y-4 relative z-10">
        <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/10 flex items-start gap-4">
          <TrendingDown className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <h4 className="font-medium text-white/90 text-sm">Debt-to-Income Ratio (DTI)</h4>
              <span className="text-xs font-bold text-red-500 bg-red-500/10 px-2 py-0.5 rounded">-42 pts</span>
            </div>
            <p className="text-xs text-white/50 leading-relaxed mb-3">
               Requested EMI of ₹{emi.toLocaleString('en-IN')} combined with existing liabilities exceeds the 40% DTI threshold for your bracket.
            </p>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
               <div className="h-full bg-red-500 w-[75%] rounded-full" />
            </div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/10 flex items-start gap-4">
          <TrendingDown className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <h4 className="font-medium text-white/90 text-sm">Credit-Seeking Behavior</h4>
              <span className="text-xs font-bold text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded">-15 pts</span>
            </div>
            <p className="text-xs text-white/50 leading-relaxed mb-3">
               3 hard inquiries detected in the last 30 days.
            </p>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
               <div className="h-full bg-amber-500 w-[40%] rounded-full" />
            </div>
          </div>
        </div>

        <button className="w-full mt-2 h-10 bg-white/5 text-white border border-white/10 rounded-lg text-sm font-medium hover:bg-white/10 transition-all flex items-center justify-center gap-2">
           Restructure Capital Request
           <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
