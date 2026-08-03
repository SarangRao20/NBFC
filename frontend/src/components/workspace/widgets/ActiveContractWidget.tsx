import { useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { CreditCard, CheckCircle2 } from 'lucide-react';

export default function ActiveContractWidget() {
  const { loanDetails } = useLoanStore();
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentSuccess, setPaymentSuccess] = useState(false);

  const emiAmount = Math.round((loanDetails.requestedAmount * 1.105) / loanDetails.tenureMonths);

  const handlePayEmi = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      setPaymentSuccess(true);
      setTimeout(() => setPaymentSuccess(false), 3000);
    }, 2000);
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-lg shadow-xl relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl" />
      
      <div className="flex justify-between items-start mb-8 relative z-10">
        <div>
           <p className="text-xs font-semibold uppercase tracking-widest text-white/50 mb-1">Total Outstanding</p>
           <h3 className="text-3xl font-display font-medium text-white">₹{loanDetails.requestedAmount.toLocaleString('en-IN')}</h3>
        </div>
        <div className="text-right">
           <p className="text-xs font-semibold uppercase tracking-widest text-white/50 mb-1">Next EMI Due</p>
           <p className="text-sm font-medium text-white">05 {new Date().toLocaleString('en-us', { month: 'short' })}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6 relative z-10">
        <div className="p-4 rounded-xl bg-[#0A0A0A] border border-white/5">
           <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold mb-1">EMI Amount</p>
           <p className="text-base font-medium text-white">₹{emiAmount.toLocaleString('en-IN')}</p>
        </div>
        <div className="p-4 rounded-xl bg-[#0A0A0A] border border-white/5">
           <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold mb-1">Tenure Left</p>
           <p className="text-base font-medium text-white">{loanDetails.tenureMonths} Months</p>
        </div>
      </div>

      <div className="relative z-10 pt-2">
        {paymentSuccess ? (
           <button disabled className="w-full h-12 bg-emerald-500/20 text-emerald-500 border border-emerald-500/30 rounded-lg font-medium shadow-lg flex items-center justify-center gap-2 transition-all">
              <CheckCircle2 className="w-4 h-4" />
              Payment Successful
           </button>
        ) : (
           <button 
              onClick={handlePayEmi}
              disabled={isProcessing}
              className="w-full h-12 bg-white text-black rounded-lg font-medium shadow-lg shadow-white/10 hover:shadow-white/20 hover:scale-[1.02] flex items-center justify-center gap-2 transition-all disabled:opacity-50"
           >
              {isProcessing ? (
                 <>
                    <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                    Initializing Secure Gateway...
                 </>
              ) : (
                 <>
                    <CreditCard className="w-4 h-4" />
                    Pay EMI Now
                 </>
              )}
           </button>
        )}
      </div>
    </div>
  );
}
