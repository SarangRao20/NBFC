
import { motion, AnimatePresence } from 'framer-motion';
import type { AppState } from '../types';
import { User, CheckCircle2, Circle, FileText, BadgeCheck } from 'lucide-react';
import clsx from 'clsx';

interface Props {
  appState: AppState;
}

const StatCard = ({ label, value, prefix = '', suffix = '' }: { label: string; value: string | number; prefix?: string; suffix?: string }) => {
  return (
    <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex flex-col justify-center items-start overflow-hidden">
      <span className="text-sm text-slate-500 font-medium mb-1">{label}</span>
      <div className="text-2xl font-bold text-slate-800 flex items-baseline relative">
        {prefix && <span className="text-lg mr-1 text-slate-600">{prefix}</span>}
        <AnimatePresence mode="popLayout">
          <motion.span
            key={value}
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -20, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className="inline-block"
          >
            {value}
          </motion.span>
        </AnimatePresence>
        {suffix && <span className="text-lg ml-1 text-slate-600">{suffix}</span>}
      </div>
    </div>
  );
};

export default function DashboardPane({ appState }: Props) {
  // Add formatters
  const formatCurrency = (val: number) => new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(val);

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
          <StatCard label="Requested" value={formatCurrency(appState.requestedAmount)} prefix="₹" />
          <StatCard label="Int. Rate (ROI)" value={appState.roi} suffix="%" />
          <StatCard label="Tenure" value={appState.tenure} suffix=" Mo" />
          <StatCard label="Monthly EMI" value={formatCurrency(appState.emi)} prefix="₹" />
        </div>
      </div>

      {/* Underwriting Status */}
      <div className="mb-8">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Underwriting Status</h3>
        <motion.div
          key={appState.underwritingStatus}
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className={clsx(
            "px-4 py-3 rounded-xl border-2 flex items-center font-bold text-sm transition-colors shadow-sm",
            {
              'bg-amber-50 border-amber-200 text-amber-700': appState.underwritingStatus === 'Pending Evaluation',
              'bg-emerald-50 border-emerald-200 text-emerald-700': appState.underwritingStatus === 'Approved',
              'bg-red-50 border-red-200 text-red-700': appState.underwritingStatus === 'Soft-Rejected',
            }
          )}
        >
          {appState.underwritingStatus === 'Pending Evaluation' && <Circle size={18} className="mr-2 animate-pulse" />}
          {appState.underwritingStatus === 'Approved' && <CheckCircle2 size={18} className="mr-2" />}
          {(appState.underwritingStatus === 'Soft-Rejected') && <Circle size={18} className="mr-2" />}
          {appState.underwritingStatus}
        </motion.div>
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
