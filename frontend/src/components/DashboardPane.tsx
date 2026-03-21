import { motion, AnimatePresence } from 'framer-motion';
import type { AppState } from '../types';
import { User, CheckCircle2, Circle, FileText, BadgeCheck } from 'lucide-react';
import clsx from 'clsx';
import MetricCard from './MetricCard';
import EmiDonutChart from './EmiDonutChart';
import confetti from 'canvas-confetti';
import { useEffect, useRef } from 'react';

interface Props {
  appState: AppState;
}

export default function DashboardPane({ appState }: Props) {
  const badgeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (appState.underwritingStatus === 'Approved' && badgeRef.current) {
      const rect = badgeRef.current.getBoundingClientRect();
      const x = (rect.left + rect.width / 2) / window.innerWidth;
      const y = (rect.top + rect.height / 2) / window.innerHeight;
      
      confetti({
        particleCount: 120,
        spread: 70,
        origin: { x, y },
        colors: ['#10b981', '#34d399', '#059669', '#fbbf24']
      });
    }
  }, [appState.underwritingStatus]);

  return (
    <div className="w-[30%] min-w-[320px] max-w-[400px] border-r border-slate-200 bg-slate-50 flex flex-col p-6 overflow-y-auto z-10">
      {/* Header: User Profile */}
      <div className="flex items-center space-x-4 mb-8 pt-2">
        <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600 shadow-inner">
          <User size={24} />
        </div>
        <div>
          <h2 className="text-lg font-bold text-slate-800">Sumit</h2>
          <div className="flex items-center text-[11px] font-bold tracking-wide text-emerald-700 bg-emerald-100/80 px-2 py-0.5 rounded-full mt-1 border border-emerald-200 w-fit uppercase">
            <BadgeCheck size={14} className="mr-1" /> Existing Customer
          </div>
        </div>
      </div>

      {/* Financial State */}
      <div className="mb-8">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Financial Overview</h3>
        <div className="grid grid-cols-2 gap-3">
          <MetricCard label="Requested" value={appState.requestedAmount} prefix="₹" />
          <MetricCard label="Int. Rate (ROI)" value={appState.roi} decimals={1} suffix="%" />
          <MetricCard label="Tenure" value={appState.tenure} suffix=" Mo" />
          <MetricCard label="Monthly EMI" value={appState.emi} prefix="₹" />
        </div>
        <EmiDonutChart principal={appState.requestedAmount} emi={appState.emi} tenure={appState.tenure} />
      </div>

      {/* Underwriting Status */}
      <div className="mb-8">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Underwriting Status</h3>
        <AnimatePresence mode="wait">
          <motion.div
            key={appState.underwritingStatus}
            initial={{ scale: 0.9, opacity: 0, x: -20 }}
            animate={{ scale: 1, opacity: 1, x: 0 }}
            exit={{ scale: 0.9, opacity: 0, x: 20 }}
            transition={{ duration: 0.4, type: 'spring' }}
          >
            <div
              ref={badgeRef}
              className={clsx(
                "px-4 py-3 rounded-xl border-2 flex items-center font-bold text-sm transition-colors shadow-sm",
                {
                  'bg-amber-50 border-amber-200 text-amber-700': appState.underwritingStatus === 'Pending Evaluation',
                  'bg-emerald-50 border-emerald-400 text-emerald-700 shadow-emerald-900/10': appState.underwritingStatus === 'Approved',
                  'bg-red-50 border-red-200 text-red-700': appState.underwritingStatus === 'Soft-Rejected',
                }
              )}
            >
              {appState.underwritingStatus === 'Pending Evaluation' && <Circle size={18} className="mr-2 animate-pulse" />}
              {appState.underwritingStatus === 'Approved' && <CheckCircle2 size={18} className="mr-2" />}
              {(appState.underwritingStatus === 'Soft-Rejected') && <Circle size={18} className="mr-2" />}
              {appState.underwritingStatus === 'Approved' ? 'Approved - Low Risk' : appState.underwritingStatus}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Document Vault */}
      <div>
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">KYC Documents</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3.5 bg-white rounded-xl border border-slate-100 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)]">
            <div className="flex items-center text-sm font-semibold text-slate-700">
              <FileText size={16} className="mr-2.5 text-slate-400" /> PAN Card
            </div>
            {appState.documents.pan === 'verified' ? (
              <CheckCircle2 size={20} className="text-emerald-500" />
            ) : (
              <Circle size={20} className="text-slate-300" />
            )}
          </div>
          <div className="flex items-center justify-between p-3.5 bg-white rounded-xl border border-slate-100 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.05)]">
            <div className="flex items-center text-sm font-semibold text-slate-700">
              <FileText size={16} className="mr-2.5 text-slate-400" /> Bank Statement
            </div>
            {appState.documents.bankStatement === 'verified' ? (
              <CheckCircle2 size={20} className="text-emerald-500" />
            ) : (
              <Circle size={20} className="text-slate-300" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
