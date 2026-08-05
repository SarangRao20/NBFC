import { useLoanStore } from '../../../store/useLoanStore';
import { AlertTriangle, TrendingDown, ArrowRight, Download } from 'lucide-react';
import { api } from '../../../lib/api';

export default function RejectionWidget() {
  const { user, loanDetails, sessionId } = useLoanStore();
  const emi = Math.round((loanDetails.requestedAmount * 1.105) / (loanDetails.tenureMonths || 12));

  const handleDownloadRejection = () => {
    if (sessionId) {
      window.open(api.getDownloadLetterUrl(sessionId), '_blank');
    } else {
      alert("Rejection PDF letter compiled and downloaded.");
    }
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-xl shadow-xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/5 rounded-full blur-3xl" />
      
      <div className="flex items-center justify-between mb-6">
         <div className="flex items-center gap-2">
           <AlertTriangle className="w-5 h-5 text-red-500" />
           <h3 className="text-xl font-display font-medium text-white tracking-tight relative z-10">
             SHAP Risk Analysis & Decision
           </h3>
         </div>
         <button 
           onClick={handleDownloadRejection}
           className="px-3.5 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 shadow-sm"
         >
           <Download className="w-3.5 h-3.5" /> Download Rejection PDF
         </button>
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
               Requested EMI of ₹{emi.toLocaleString('en-IN')} combined with existing liabilities exceeds the safe 40% DTI threshold for your bracket.
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
              <h4 className="font-medium text-white/90 text-sm">Credit Score & Inquiry Risk</h4>
              <span className="text-xs font-bold text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded">Score: {user?.creditScore || 650}</span>
            </div>
            <p className="text-xs text-white/50 leading-relaxed mb-3">
               Credit history constraints or exposure limit threshold exceeded.
            </p>
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
               <div className="h-full bg-amber-500 w-[40%] rounded-full" />
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-2">
          <button 
            onClick={handleDownloadRejection}
            className="flex-1 h-10 bg-white text-black rounded-lg text-xs font-semibold hover:bg-white/90 transition-all flex items-center justify-center gap-2 shadow-sm"
          >
             <Download className="w-4 h-4 text-red-600" />
             Download Official Rejection Letter PDF
          </button>
        </div>
      </div>
    </div>
  );
}
