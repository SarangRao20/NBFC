import { useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { CreditCard, CheckCircle2, FileText, Download, Calendar } from 'lucide-react';
import { api } from '../../../lib/api';

export default function ActiveLoans() {
  const { loanDetails, sessionId } = useLoanStore();
  const [isPaying, setIsPaying] = useState(false);
  const [paidSuccess, setPaidSuccess] = useState(false);

  const emi = Math.round((loanDetails.requestedAmount * 1.105) / loanDetails.tenureMonths);

  const handlePay = async () => {
    setIsPaying(true);
    if (sessionId) {
      await api.payEmi(sessionId);
    } else {
      await new Promise((r) => setTimeout(r, 1200));
    }
    setIsPaying(false);
    setPaidSuccess(true);
    setTimeout(() => setPaidSuccess(false), 4000);
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-medium text-white tracking-tight">Active Loan Facilities</h1>
        <p className="text-white/60 text-sm mt-1">Manage eNACH mandates, automated EMI repayments, and facility ledgers.</p>
      </div>

      {/* Main Ledger Card */}
      <div className="bg-[#111] border border-white/10 rounded-2xl p-8 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/10 pb-8 mb-8">
           <div>
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-widest bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">Active Facility</span>
              <h2 className="text-4xl font-display font-bold text-white tracking-tight mt-3">₹{loanDetails.requestedAmount.toLocaleString('en-IN')}</h2>
              <p className="text-xs text-white/40 mt-1">Facility ID: #HDFC-FAC-889102</p>
           </div>
           
           <div className="bg-[#0A0A0A] p-4 rounded-xl border border-white/10 flex items-center gap-6">
              <div>
                 <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold">Next EMI Due</p>
                 <p className="text-lg font-bold text-white">₹{emi.toLocaleString('en-IN')}</p>
              </div>
              <div className="h-8 w-px bg-white/10" />
              <div>
                 <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold">Due Date</p>
                 <p className="text-sm font-medium text-emerald-400">05th Next Month</p>
              </div>
           </div>
        </div>

        {/* EMI Action Button */}
        <div className="max-w-md">
           {paidSuccess ? (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 font-medium flex items-center justify-center gap-2 animate-fade-in text-sm">
                 <CheckCircle2 className="w-5 h-5" /> EMI Payment Successfully Received & Recorded
              </div>
           ) : (
              <button
                 onClick={handlePay}
                 disabled={isPaying}
                 className="w-full h-14 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg shadow-white/10 transition-all flex items-center justify-center gap-3 text-base disabled:opacity-50"
              >
                 {isPaying ? (
                    <>
                       <span className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                       Connecting to Gateway...
                    </>
                 ) : (
                    <>
                       <CreditCard className="w-5 h-5" />
                       Pay Current Monthly EMI (₹{emi.toLocaleString('en-IN')})
                    </>
                 )}
              </button>
           )}
        </div>
      </div>

      {/* Repayment Schedule */}
      <div className="bg-[#111] border border-white/10 rounded-2xl p-6">
         <h3 className="text-lg font-display font-medium text-white mb-4">Repayment Amortization Ledger</h3>
         <div className="space-y-3 font-mono text-xs">
            <div className="flex justify-between items-center p-3 bg-[#0A0A0A] rounded-lg border border-white/5 text-white/70">
               <span className="text-white font-medium">Installment #1</span>
               <span>05 Sep 2026</span>
               <span className="text-emerald-400">₹{emi.toLocaleString('en-IN')}</span>
               <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-sans">Upcoming</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[#0A0A0A] rounded-lg border border-white/5 text-white/70">
               <span className="text-white font-medium">Installment #2</span>
               <span>05 Oct 2026</span>
               <span className="text-white">₹{emi.toLocaleString('en-IN')}</span>
               <span className="text-xs text-white/40 bg-white/5 px-2 py-0.5 rounded font-sans">Scheduled</span>
            </div>
         </div>
      </div>
    </div>
  );
}
