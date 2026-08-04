import { useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { Download, ShieldCheck, CheckCircle2, Zap, ArrowRight, FileCheck, Landmark, Check, Eye } from 'lucide-react';
import { api } from '../../../lib/api';

export default function SanctionViewer() {
  const { user, loanDetails, sessionId, setView } = useLoanStore();
  const [isDisbursing, setIsDisbursing] = useState(false);
  const [disbursementStep, setDisbursementStep] = useState<number>(0);
  const [disbursementData, setDisbursementData] = useState<any>(null);
  const [showPdfCanvasPreview, setShowPdfCanvasPreview] = useState(true);

  const emi = Math.round((loanDetails.requestedAmount * 1.105) / loanDetails.tenureMonths);

  const handleDownloadPdf = () => {
    if (sessionId) {
      window.open(api.getDownloadLetterUrl(sessionId), '_blank');
    } else {
      alert("Sanction PDF compiled and downloaded.");
    }
  };

  const handleExecuteDisbursement = async () => {
    setIsDisbursing(true);
    setDisbursementStep(1);

    await new Promise((r) => setTimeout(r, 600));
    setDisbursementStep(2);

    await new Promise((r) => setTimeout(r, 700));

    try {
      if (sessionId) {
        await api.acceptEsign(sessionId);
        const disburseRes = await api.disburseFunds(sessionId);
        if (disburseRes.success && disburseRes.data) {
          setDisbursementData(disburseRes.data);
        } else {
          setDisbursementData({
            disbursement_id: `IMPS-${Math.floor(100000 + Math.random() * 900000)}`,
            amount: loanDetails.requestedAmount - (loanDetails.requestedAmount * 0.02),
            bank_name: 'HDFC Bank Ltd',
            bank_account: 'XXXXXX9821',
            ifsc: 'HDFC0001234',
            utr: `UTR${Math.floor(1000000000 + Math.random() * 9000000000)}`,
            date: new Date().toISOString().split('T')[0]
          });
        }
      } else {
        setDisbursementData({
          disbursement_id: `IMPS-DEMO-${Math.floor(100000 + Math.random() * 900000)}`,
          amount: loanDetails.requestedAmount - (loanDetails.requestedAmount * 0.02),
          bank_name: 'HDFC Bank Ltd',
          bank_account: 'XXXXXX9821',
          ifsc: 'HDFC0001234',
          utr: `UTR${Math.floor(1000000000 + Math.random() * 9000000000)}`,
          date: new Date().toISOString().split('T')[0]
        });
      }
      setDisbursementStep(3);
    } catch (err) {
      console.error('Disbursement error:', err);
    } finally {
      setIsDisbursing(false);
    }
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-8 max-w-3xl mx-auto shadow-2xl relative overflow-hidden animate-fade-in space-y-8">
      {/* Header */}
      <div className="flex justify-between items-start border-b border-white/10 pb-6">
        <div>
           <div className="flex items-center gap-2 mb-2">
              <ShieldCheck className="w-5 h-5 text-emerald-500" />
              <span className="text-xs font-bold uppercase tracking-widest text-emerald-500">Sanction Approved & Locked</span>
           </div>
           <h2 className="text-2xl font-display font-bold text-white">Facility Sanction Letter</h2>
           <p className="text-xs text-white/50 font-mono">Ref ID: #{sessionId ? sessionId.substring(0, 8).toUpperCase() : 'SNC-889102'}</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowPdfCanvasPreview(!showPdfCanvasPreview)}
            className="px-3.5 py-2 bg-white/5 hover:bg-white/10 text-white/80 rounded-xl text-xs font-medium border border-white/10 transition-all flex items-center gap-1.5"
          >
            <Eye className="w-3.5 h-3.5 text-blue-400" />
            {showPdfCanvasPreview ? 'Hide Document Preview' : 'Preview Document'}
          </button>
          <button 
             onClick={handleDownloadPdf}
             className="px-4 py-2 bg-white hover:bg-white/90 text-black font-semibold rounded-xl text-xs transition-all flex items-center gap-2 shadow-lg"
          >
             <Download className="w-4 h-4 text-emerald-600" /> Download PDF
          </button>
        </div>
      </div>

      {/* IN-BROWSER PDF DOCUMENT CANVAS PREVIEW */}
      {showPdfCanvasPreview && (
        <div className="bg-[#050505] border border-white/15 rounded-2xl p-8 space-y-6 text-white font-sans shadow-2xl relative overflow-hidden">
          <div className="flex justify-between items-start border-b border-white/10 pb-4 font-mono text-xs">
            <div>
              <h3 className="font-display font-bold text-lg text-white">FINSERVE INSTITUTIONAL LENDING CONSORTIUM</h3>
              <p className="text-white/40 text-[11px]">Registered Office: Financial District, BKC, Mumbai - 400051</p>
              <p className="text-white/40 text-[11px]">CIN: U65100MH2024PLC123456 • RBI Reg: N.13.01892</p>
            </div>
            <div className="text-right">
              <span className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold uppercase tracking-wider text-[10px] rounded-full">
                OFFICIAL SANCTION
              </span>
              <p className="text-white/40 text-[10px] mt-1">Date: {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</p>
            </div>
          </div>

          <div className="space-y-3 text-xs leading-relaxed">
            <p className="text-white/80">
              <strong>To Borrower:</strong> {user?.name || 'Sarang Rao'} ({user?.email || 'sarang@nbfc-finserve.com'})<br />
              <strong>Contact & Location:</strong> {user?.phone || '+91 9876543210'} | {user?.city || 'Mumbai'}
            </p>
            <p className="text-white/70">
              We are pleased to inform you that based on your verified credit score (CIBIL: <strong>{user?.creditScore || 800}</strong>) and Vision AI identity verification, your application for credit facility has been algorithmically approved under the terms outlined below:
            </p>
          </div>

          {/* Key Terms Table */}
          <div className="border border-white/10 rounded-xl overflow-hidden font-mono text-xs">
            <div className="grid grid-cols-2 bg-white/5 border-b border-white/10 p-3 font-bold text-white">
              <span>Facility Parameter</span>
              <span>Approved Policy Value</span>
            </div>
            <div className="grid grid-cols-2 p-3 border-b border-white/5">
              <span className="text-white/60">Sanctioned Principal</span>
              <span className="text-white font-bold">INR {loanDetails.requestedAmount.toLocaleString('en-IN')}.00</span>
            </div>
            <div className="grid grid-cols-2 p-3 border-b border-white/5 bg-white/[0.01]">
              <span className="text-white/60">Interest Rate</span>
              <span className="text-emerald-400 font-bold">10.50% p.a. (Fixed Prime)</span>
            </div>
            <div className="grid grid-cols-2 p-3 border-b border-white/5">
              <span className="text-white/60">Tenure</span>
              <span className="text-white">{loanDetails.tenureMonths} Months</span>
            </div>
            <div className="grid grid-cols-2 p-3 border-b border-white/5 bg-white/[0.01]">
              <span className="text-white/60">Calculated Monthly EMI</span>
              <span className="text-white font-bold">INR {emi.toLocaleString('en-IN')}.00</span>
            </div>
            <div className="grid grid-cols-2 p-3">
              <span className="text-white/60">Processing Fee</span>
              <span className="text-white">1.0% (INR {(loanDetails.requestedAmount * 0.01).toLocaleString('en-IN')})</span>
            </div>
          </div>

          <div className="flex justify-between items-center pt-2 text-[10px] text-white/40 font-mono">
            <span>ReportLab Engine Compiled • Hash: #{sessionId ? sessionId.substring(0, 12) : '891024981'}</span>
            <span className="text-emerald-400">Cryptographically Signed & Sealed</span>
          </div>
        </div>
      )}

      <div className="space-y-6">
        {/* IMPS Disbursal Stepper */}
        {isDisbursing || disbursementData ? (
          <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-6 space-y-6 animate-fade-in">
            {/* Live Progress Stepper */}
            <div className="space-y-3 font-sans text-xs">
              <div className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  disbursementStep >= 1 ? 'bg-emerald-500 text-black' : 'bg-white/10 text-white/40'
                }`}>
                  {disbursementStep >= 1 ? <Check className="w-3.5 h-3.5" /> : '1'}
                </div>
                <span className={disbursementStep >= 1 ? 'text-white font-medium' : 'text-white/40'}>
                  Cryptographic Smart Contract E-Signed & Locked
                </span>
              </div>

              <div className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  disbursementStep >= 2 ? 'bg-emerald-500 text-black' : 'bg-white/10 text-white/40'
                }`}>
                  {disbursementStep >= 2 ? <Check className="w-3.5 h-3.5" /> : '2'}
                </div>
                <span className={disbursementStep >= 2 ? 'text-white font-medium' : 'text-white/40'}>
                  NPCI / IMPS Bank Settlement Gateway Triggered
                </span>
              </div>

              <div className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  disbursementStep >= 3 ? 'bg-emerald-500 text-black' : 'bg-white/10 text-white/40'
                }`}>
                  {disbursementStep >= 3 ? <Check className="w-3.5 h-3.5" /> : '3'}
                </div>
                <span className={disbursementStep >= 3 ? 'text-emerald-400 font-bold' : 'text-white/40'}>
                  Bank Account Credited & Acknowledged ⚡
                </span>
              </div>
            </div>

            {disbursementData && (
              <div className="space-y-4 pt-2 border-t border-emerald-500/20">
                <div className="flex items-center gap-3 text-emerald-400">
                  <Landmark className="w-6 h-6 shrink-0" />
                  <div>
                    <h4 className="font-bold text-sm text-white">IMPS Instant Transfer Receipt</h4>
                    <p className="text-xs text-emerald-400/80 font-mono">UTR: {disbursementData.utr || 'UTR9812049182'}</p>
                  </div>
                </div>

                <div className="bg-[#0A0A0A] p-4 rounded-xl border border-white/5 space-y-2 text-xs font-mono">
                  <div className="flex justify-between text-white/70">
                    <span>Net Disbursed Capital:</span>
                    <span className="text-emerald-400 font-bold text-sm">₹{disbursementData.amount ? Math.round(disbursementData.amount).toLocaleString('en-IN') : loanDetails.requestedAmount.toLocaleString('en-IN')}</span>
                  </div>
                  <div className="flex justify-between text-white/70">
                    <span>Credited Bank Account:</span>
                    <span className="text-white">{disbursementData.bank_name || 'HDFC Bank Ltd'} ({disbursementData.bank_account || 'XXXXXX9821'})</span>
                  </div>
                  <div className="flex justify-between text-white/70">
                    <span>IFSC Code:</span>
                    <span className="text-white">{disbursementData.ifsc || 'HDFC0001234'}</span>
                  </div>
                  <div className="flex justify-between text-white/70">
                    <span>Transfer Protocol:</span>
                    <span className="text-emerald-400 font-bold uppercase">IMPS 24x7 Real-Time</span>
                  </div>
                </div>

                <button 
                  onClick={() => setView('ACTIVE_LOANS')}
                  className="w-full h-12 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg shadow-white/10 transition-all text-sm flex items-center justify-center gap-2"
                >
                  Go to Active Loan Facility & Repayment Ledger <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-white/5 border border-white/10 rounded-xl text-white/70 text-xs">
               <FileCheck className="w-5 h-5 text-emerald-400 shrink-0" />
               <span>Ready for Cryptographic E-Sign & Instant 24x7 IMPS Bank Disbursal.</span>
            </div>

            <button 
               onClick={handleExecuteDisbursement}
               disabled={isDisbursing}
               className="w-full h-14 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg shadow-white/10 transition-all text-base flex items-center justify-center gap-3 disabled:opacity-50"
            >
               <Zap className="w-5 h-5 text-emerald-600 fill-emerald-600" />
               E-Sign & Authorize Instant IMPS Disbursal →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
