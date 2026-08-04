import { useEffect, useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { CreditCard, CheckCircle2, ShieldCheck, Download, X, Lock, Smartphone, Building2 } from 'lucide-react';
import { api } from '../../../lib/api';

export default function ActiveLoans() {
  const { user, loanDetails, sessionId } = useLoanStore();
  const [isPaying, setIsPaying] = useState(false);
  const [paidSuccess, setPaidSuccess] = useState(false);
  const [showRazorpayModal, setShowRazorpayModal] = useState(false);
  const [activeLoanData, setActiveLoanData] = useState<any>(null);
  const [paymentMethod, setPaymentMethod] = useState<'UPI' | 'CARD' | 'NETBANKING'>('UPI');

  useEffect(() => {
    if (user?.phone) {
      api.getLoanHistory(user.phone).then((res) => {
        if (res.success && res.data?.history && res.data.history.length > 0) {
          const approved = res.data.history.find((h: any) => h.status === 'Approved' || h.status === 'Disbursed') || res.data.history[0];
          if (approved) {
            setActiveLoanData(approved);
          }
        }
      });
    }
  }, [user?.phone]);

  const facilityAmount = activeLoanData?.amount || loanDetails.requestedAmount;
  const tenure = activeLoanData?.tenure || loanDetails.tenureMonths;
  const emi = activeLoanData?.emi || Math.round((facilityAmount * 1.105) / tenure);
  const facilityId = activeLoanData?.session_id
    ? `#FAC-${activeLoanData.session_id.substring(0, 8).toUpperCase()}`
    : '#FAC-HDFC-889102';
  const lenderName = activeLoanData?.loan_type || activeLoanData?.lender_name || 'HDFC Bank NBFC';

  const handleExecutePayment = async () => {
    setIsPaying(true);
    try {
      if (sessionId) {
        await api.payEmi(sessionId);
      } else {
        await new Promise((r) => setTimeout(r, 1200));
      }
      setPaidSuccess(true);
      setShowRazorpayModal(false);
      setTimeout(() => setPaidSuccess(false), 5000);
    } catch (e) {
      console.error(e);
    } finally {
      setIsPaying(false);
    }
  };

  const handleDownloadSanction = () => {
    if (sessionId) {
      window.open(api.getDownloadLetterUrl(sessionId), '_blank');
    } else if (activeLoanData?.session_id) {
      window.open(api.getDownloadLetterUrl(activeLoanData.session_id), '_blank');
    } else {
      alert("Sanction PDF generated on backend session.");
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-display font-medium text-white tracking-tight">Active Loan Facilities</h1>
          <p className="text-white/60 text-sm mt-1">Manage eNACH mandates, automated EMI repayments, and facility ledgers.</p>
        </div>
        <button
          onClick={handleDownloadSanction}
          className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-xl text-xs font-medium border border-white/10 transition-all flex items-center gap-2"
        >
          <Download className="w-4 h-4 text-emerald-400" /> Download Facility Sanction
        </button>
      </div>

      {/* Main Ledger Card */}
      <div className="bg-[#111] border border-white/10 rounded-2xl p-8 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-white/10 pb-8 mb-8">
           <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-emerald-400 uppercase tracking-widest bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">Active Facility</span>
                <span className="text-xs font-semibold text-white/50">{lenderName}</span>
              </div>
              <h2 className="text-4xl font-display font-bold text-white tracking-tight mt-3">₹{facilityAmount.toLocaleString('en-IN')}</h2>
              <p className="text-xs text-white/40 mt-1 font-mono">Facility ID: {facilityId}</p>
           </div>
           
           <div className="bg-[#0A0A0A] p-4 rounded-xl border border-white/10 flex items-center gap-6">
              <div>
                 <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold">Next EMI Due</p>
                 <p className="text-lg font-bold text-white font-mono">₹{emi.toLocaleString('en-IN')}</p>
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
                 onClick={() => setShowRazorpayModal(true)}
                 className="w-full h-14 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg shadow-white/10 transition-all flex items-center justify-center gap-3 text-base"
              >
                 <CreditCard className="w-5 h-5" />
                 Pay Monthly EMI via Razorpay (₹{emi.toLocaleString('en-IN')})
              </button>
           )}
        </div>
      </div>

      {/* Repayment Schedule */}
      <div className="bg-[#111] border border-white/10 rounded-2xl p-6">
         <h3 className="text-lg font-display font-medium text-white mb-4">Repayment Amortization Ledger</h3>
         <div className="space-y-3 font-mono text-xs">
            {(activeLoanData?.emi_schedule && activeLoanData.emi_schedule.length > 0
              ? activeLoanData.emi_schedule.slice(0, 6)
              : Array.from({ length: Math.min(tenure, 6) }).map((_, idx) => {
                  const d = new Date();
                  d.setMonth(d.getMonth() + idx + 1);
                  d.setDate(5);
                  return {
                    installment: idx + 1,
                    due_date: d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
                    amount: emi,
                    status: idx === 0 ? 'Upcoming' : 'Scheduled'
                  };
                })
            ).map((item: any, idx: number) => {
               const isFirst = idx === 0;
               const dateStr = item.due_date
                 ? (new Date(item.due_date).toString() !== 'Invalid Date' 
                    ? new Date(item.due_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) 
                    : item.due_date)
                 : '05th Next Month';

               return (
                 <div key={idx} className="flex justify-between items-center p-3 bg-[#0A0A0A] rounded-lg border border-white/5 text-white/70">
                    <span className="text-white font-medium">Installment #{item.installment || idx + 1}</span>
                    <span>{dateStr}</span>
                    <span className={isFirst ? "text-emerald-400 font-bold" : "text-white"}>₹{(item.amount || emi).toLocaleString('en-IN')}</span>
                    <span className={`text-xs px-2 py-0.5 rounded font-sans font-medium ${
                      isFirst ? "text-emerald-400 bg-emerald-500/10" : "text-white/40 bg-white/5"
                    }`}>
                      {item.status === 'pending' || isFirst ? 'Upcoming' : (item.status || 'Scheduled')}
                    </span>
                 </div>
               );
            })}
         </div>
      </div>

      {/* Razorpay Gateway Modal */}
      {showRazorpayModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-fade-in">
          <div className="bg-[#111] border border-white/15 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl relative">
            <div className="p-5 border-b border-white/10 bg-white/[0.02] flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 font-bold text-xs">
                  RZP
                </div>
                <div>
                  <h4 className="font-display font-semibold text-white text-sm">Razorpay Checkout Gateway</h4>
                  <p className="text-[10px] text-white/40 font-mono uppercase">Merchant: FinServe NBFC Facilities</p>
                </div>
              </div>
              <button onClick={() => setShowRazorpayModal(false)} className="text-white/40 hover:text-white transition-all">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              <div className="bg-[#0A0A0A] p-4 rounded-xl border border-white/5 flex justify-between items-center">
                <div>
                  <p className="text-[10px] text-white/40 uppercase tracking-widest font-bold">Total Payable EMI</p>
                  <p className="text-2xl font-bold text-white font-mono">₹{emi.toLocaleString('en-IN')}</p>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                  <Lock className="w-3 h-3" /> 256-Bit Encrypted
                </div>
              </div>

              {/* Payment Method Selector */}
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => setPaymentMethod('UPI')}
                  className={`p-3 rounded-xl border text-xs font-medium flex flex-col items-center gap-1.5 transition-all ${
                    paymentMethod === 'UPI'
                      ? 'bg-blue-500/10 border-blue-500/40 text-blue-400'
                      : 'bg-[#0A0A0A] border-white/10 text-white/60 hover:bg-white/5'
                  }`}
                >
                  <Smartphone className="w-4 h-4" /> UPI Apps
                </button>
                <button
                  onClick={() => setPaymentMethod('CARD')}
                  className={`p-3 rounded-xl border text-xs font-medium flex flex-col items-center gap-1.5 transition-all ${
                    paymentMethod === 'CARD'
                      ? 'bg-blue-500/10 border-blue-500/40 text-blue-400'
                      : 'bg-[#0A0A0A] border-white/10 text-white/60 hover:bg-white/5'
                  }`}
                >
                  <CreditCard className="w-4 h-4" /> Card
                </button>
                <button
                  onClick={() => setPaymentMethod('NETBANKING')}
                  className={`p-3 rounded-xl border text-xs font-medium flex flex-col items-center gap-1.5 transition-all ${
                    paymentMethod === 'NETBANKING'
                      ? 'bg-blue-500/10 border-blue-500/40 text-blue-400'
                      : 'bg-[#0A0A0A] border-white/10 text-white/60 hover:bg-white/5'
                  }`}
                >
                  <Building2 className="w-4 h-4" /> NetBanking
                </button>
              </div>

              {paymentMethod === 'UPI' && (
                <div className="bg-[#0A0A0A] p-4 rounded-xl border border-white/5 space-y-2">
                  <p className="text-xs text-white/70">Select your preferred UPI App:</p>
                  <div className="flex gap-3 text-xs font-medium">
                    <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white">Google Pay</span>
                    <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white">PhonePe</span>
                    <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white">Paytm</span>
                  </div>
                </div>
              )}

              <button
                onClick={handleExecutePayment}
                disabled={isPaying}
                className="w-full h-12 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg shadow-white/10 transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-50"
              >
                {isPaying ? (
                  <>
                    <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                    Authorizing Razorpay Payment...
                  </>
                ) : (
                  <>Pay ₹{emi.toLocaleString('en-IN')} via Razorpay →</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
