import { useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import OnboardingWidget from '../widgets/OnboardingWidget';
import KycWidget from '../widgets/KycWidget';
import OffersWidget from '../widgets/OffersWidget';
import SanctionViewer from '../widgets/SanctionViewer';
import { Check, ChevronRight } from 'lucide-react';
import { api } from '../../../lib/api';

export default function LoanApplication() {
  const { sessionId, setSessionId, loanDetails, setAgentActive, addAgentLog, clearAgentLogs } = useLoanStore();
  const [step, setStep] = useState<number>(1);

  const steps = [
    { id: 1, name: 'Capital Selection' },
    { id: 2, name: 'Vision AI KYC' },
    { id: 3, name: 'StateGraph Underwriting' },
    { id: 4, name: 'Facility Sanction' },
  ];

  const runAgentTask = async (logs: string[], taskFn: () => Promise<void>) => {
    clearAgentLogs();
    setAgentActive(true);

    for (const log of logs) {
      addAgentLog(log);
      await new Promise((res) => setTimeout(res, 500));
    }

    try {
      await taskFn();
    } catch (e: any) {
      addAgentLog(`❌ Error: ${e.message}`);
    } finally {
      setTimeout(() => setAgentActive(false), 800);
    }
  };

  const handleParamsSubmit = async () => {
    await runAgentTask([
      'POST /session/start initializing StateGraph workflow...',
      'Invoking Sales Agent (LangGraph node)...',
      'POST /sales/capture-loan-params calculating DTI & FOIR...',
      'Comparing 40,000+ data vectors across partner NBFCs...',
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
      setStep(2);
    });
  };

  const handleKycSubmit = async () => {
    await runAgentTask([
      'POST /documents/upload verifying XML signatures...',
      'Invoking Vision AI Agent (OCR & Fraud Verification)...',
      'Bypass Mode Active: Approved Aadhaar & PAN hashes',
      'POST /session/underwrite running Decision Engine...',
      'StateGraph Underwriter: APPROVED for partner disbursal.',
    ], async () => {
      if (sessionId) {
        await api.underwrite(sessionId);
      }
      setStep(3);
    });
  };

  const handleOfferSelect = async (lenderId: string) => {
    await runAgentTask([
      `POST /session/select-lender selected partner ${lenderId}...`,
      'Executing Smart Contract & eNACH Mandate...',
      'POST /session/sanction generating PDF Sanction Letter...',
    ], async () => {
      if (sessionId) {
        await api.selectLender(sessionId, { selected_lender_id: lenderId });
        await api.generateSanction(sessionId);
      }
      setStep(4);
    });
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto pb-12">
      {/* Step Tracker Header */}
      <div className="bg-[#111] border border-white/10 rounded-2xl p-6">
        <div className="flex justify-between items-center relative">
          {steps.map((s, idx) => (
            <div key={s.id} className="flex items-center gap-3 relative z-10">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs transition-all ${
                  step > s.id
                    ? 'bg-emerald-500 text-black'
                    : step === s.id
                    ? 'bg-white text-black ring-4 ring-white/10'
                    : 'bg-white/5 text-white/40 border border-white/10'
                }`}
              >
                {step > s.id ? <Check className="w-4 h-4" /> : s.id}
              </div>
              <span
                className={`text-sm font-medium hidden sm:block ${
                  step === s.id ? 'text-white' : 'text-white/40'
                }`}
              >
                {s.name}
              </span>
              {idx < steps.length - 1 && (
                <ChevronRight className="w-4 h-4 text-white/20 hidden md:block ml-2" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main Form Display Area */}
      <div className="flex justify-center">
        {step === 1 && (
          <div className="w-full max-w-xl">
             <OnboardingWidget onNext={handleParamsSubmit} />
          </div>
        )}

        {step === 2 && (
          <div className="w-full max-w-xl">
             <KycWidget onNext={handleKycSubmit} />
          </div>
        )}

        {step === 3 && (
          <div className="w-full">
             <OffersWidget onSelect={handleOfferSelect} />
          </div>
        )}

        {step === 4 && (
          <div className="w-full">
             <SanctionViewer />
          </div>
        )}
      </div>
    </div>
  );
}
