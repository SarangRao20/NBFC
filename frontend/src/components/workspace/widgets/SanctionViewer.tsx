import { useLoanStore } from '../../../store/useLoanStore';
import { Download, ShieldCheck, CheckCircle2 } from 'lucide-react';

import { api } from '../../../lib/api';

export default function SanctionViewer() {
  const { user, loanDetails, sessionId, setView } = useLoanStore();

  const emi = Math.round((loanDetails.requestedAmount * 1.105) / loanDetails.tenureMonths);

  const handleDownloadPdf = () => {
    if (sessionId) {
      window.open(api.getDownloadLetterUrl(sessionId), '_blank');
    } else {
      alert("Sanction PDF generated on backend session.");
    }
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-8 max-w-2xl mx-auto shadow-2xl relative overflow-hidden">
      <div className="flex justify-between items-start border-b border-white/10 pb-6 mb-6">
        <div>
           <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-5 h-5 text-emerald-500" />
              <span className="text-xs font-bold uppercase tracking-widest text-emerald-500">Sanction Approved</span>
           </div>
           <h2 className="text-2xl font-display font-bold text-white">Facility Sanction Letter</h2>
           <p className="text-xs text-white/50">Ref ID: #{sessionId ? sessionId.substring(0, 8).toUpperCase() : 'SNC-889102'}</p>
        </div>
        <button 
           onClick={handleDownloadPdf}
           className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-xs font-medium transition-all flex items-center gap-2 border border-white/10"
        >
           <Download className="w-4 h-4" /> Download PDF
        </button>
      </div>

      <div className="space-y-6">
        <p className="text-sm text-white/70 leading-relaxed">
           Dear <strong className="text-white">{user?.name || 'Borrower'}</strong>, we are pleased to confirm that your credit facility has been algorithmically approved based on your CIBIL profile ({user?.creditScore || 785}) and Vision AI document verification.
        </p>

        <div className="grid grid-cols-2 gap-4 bg-[#0A0A0A] p-6 rounded-xl border border-white/5">
           <div>
              <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold mb-1">Sanctioned Amount</p>
              <p className="text-xl font-bold text-white">₹{loanDetails.requestedAmount.toLocaleString('en-IN')}</p>
           </div>
           <div>
              <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold mb-1">Interest Rate</p>
              <p className="text-xl font-bold text-emerald-400">10.5% p.a.</p>
           </div>
           <div>
              <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold mb-1">Tenure</p>
              <p className="text-xl font-bold text-white">{loanDetails.tenureMonths} Months</p>
           </div>
           <div>
              <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold mb-1">Monthly EMI</p>
              <p className="text-xl font-bold text-white">₹{emi.toLocaleString('en-IN')}</p>
           </div>
        </div>

        <div className="flex items-center gap-3 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-xs">
           <CheckCircle2 className="w-5 h-5 shrink-0" />
           <span>eNACH Mandate & eSign completed via Cryptographic Key Signature.</span>
        </div>

        <button 
           onClick={() => setView('ACTIVE_LOANS')}
           className="w-full h-12 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg shadow-white/10 transition-all text-sm"
        >
           Go to Active Loan Facility & Repayments →
        </button>
      </div>
    </div>
  );
}
