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
  onLoadSession?: (sessionId: string) => void;
}

export default function DashboardPane({ appState, onLoadSession }: Props) {
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
    <div className="w-[22%] min-w-[240px] max-w-[280px] border-r border-slate-200 bg-slate-50 flex flex-col p-2 overflow-y-auto z-10 scrollbar-hide">
      {/* Header: User Profile */}
      <div className="flex items-center space-x-2.5 mb-2.5 pt-0.5">
        <div className="w-9 h-9 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600 shadow-inner">
          <User size={18} />
        </div>
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-slate-800 truncate">{appState.customerName || 'Guest User'}</h2>
          {appState.customerName && (
            <div className="flex items-center text-[9px] font-bold tracking-tight text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100 w-fit uppercase mt-0.5">
              <BadgeCheck size={10} className="mr-1" /> Existing
            </div>
          )}
        </div>
      </div>

      {/* Financial State */}
      <div className="mb-2.5">
        <div className="grid grid-cols-2 gap-1.5 mb-2">
          <MetricCard label="Requested" value={appState.requestedAmount} prefix="₹" />
          <MetricCard label="Int. Rate" value={appState.roi} decimals={1} suffix="%" />
          <MetricCard label="Tenure" value={appState.tenure} suffix=" Mo" />
          <MetricCard label="Monthly EMI" value={appState.emi} prefix="₹" />
        </div>
        
        {appState.creditScore > 0 && (
          <div className="grid grid-cols-2 gap-1.5 p-2 bg-white rounded-lg border border-slate-100 shadow-sm">
            <div className="text-center border-r border-slate-100">
              <div className="text-[10px] font-bold text-slate-400 uppercase">Credit Score</div>
              <div className="text-lg font-bold text-emerald-600">{appState.creditScore}</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] font-bold text-slate-400 uppercase">Pre-approved</div>
              <div className="text-lg font-bold text-slate-700">₹{(appState.preApprovedLimit / 100000).toFixed(1)}L</div>
            </div>
          </div>
        )}

        <EmiDonutChart principal={appState.requestedAmount} emi={appState.emi} tenure={appState.tenure} />
      </div>

      {/* Underwriting Status */}
      <div className="mb-3">
        <AnimatePresence mode="wait">
          <motion.div
            key={appState.underwritingStatus}
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
          >
            <div
              ref={badgeRef}
              className={clsx(
                "px-2 py-1 rounded-md border flex items-center font-bold text-[10px] transition-colors shadow-sm",
                {
                  'bg-amber-50 border-amber-200 text-amber-700': appState.underwritingStatus === 'Pending Evaluation',
                  'bg-emerald-50 border-emerald-400 text-emerald-700 shadow-emerald-900/10': appState.underwritingStatus === 'Approved',
                  'bg-red-50 border-red-200 text-red-700': appState.underwritingStatus === 'Soft-Rejected',
                }
              )}
            >
              {appState.underwritingStatus === 'Pending Evaluation' && <Circle size={14} className="mr-1.5 animate-pulse" />}
              {appState.underwritingStatus === 'Approved' && <CheckCircle2 size={14} className="mr-1.5" />}
              {(appState.underwritingStatus === 'Soft-Rejected') && <Circle size={14} className="mr-1.5" />}
              {appState.underwritingStatus === 'Approved' ? 'High Approval Probability' : appState.underwritingStatus}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Document Vault */}
      <div className="mb-3">
        <h3 className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">KYC Documents</h3>
        <div className="grid grid-cols-2 gap-1.5">
          <div className="flex items-center justify-between p-1.5 bg-white rounded-md border border-slate-100 shadow-sm">
            <div className="flex items-center text-[10px] font-bold text-slate-600 truncate mr-1">
              <FileText size={12} className="mr-1 text-slate-400" /> PAN
            </div>
            {appState.documents.pan === 'verified' ? (
              <CheckCircle2 size={14} className="text-emerald-500 flex-shrink-0" />
            ) : (
              <Circle size={14} className="text-slate-200 flex-shrink-0" />
            )}
          </div>
          <div className="flex items-center justify-between p-1.5 bg-white rounded-md border border-slate-100 shadow-sm">
            <div className="flex items-center text-[10px] font-bold text-slate-600 truncate mr-1">
              <FileText size={12} className="mr-1 text-slate-400" /> Income
            </div>
            {appState.documents.bankStatement === 'verified' ? (
              <CheckCircle2 size={14} className="text-emerald-500 flex-shrink-0" />
            ) : (
              <Circle size={14} className="text-slate-200 flex-shrink-0" />
            )}
          </div>
        </div>
      </div>

      {/* Past Sessions */}
      {appState.pastLoans && appState.pastLoans.length > 0 && (
        <div className="mt-2 pt-2.5 border-t border-slate-200">
          <h3 className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2">Past Loan History</h3>
          <div className="space-y-1.5">
            {appState.pastLoans.slice(0, 2).map((loan, i) => (
              <div key={i} className="p-1.5 bg-slate-100/50 rounded-md border border-slate-200/60">
                <div className="flex justify-between items-start mb-0.5">
                  <span className="text-[10px] font-bold text-slate-700">₹{loan.amount?.toLocaleString()} ({loan.type})</span>
                  <span className={clsx(
                    "text-[8px] px-1 py-0.5 rounded font-bold uppercase",
                    loan.decision === 'approve' ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-600"
                  )}>
                    {loan.decision}
                  </span>
                </div>
                <div className="text-[9px] text-slate-500 flex justify-between">
                  <span>{new Date(loan.date).toLocaleDateString()}</span>
                  {loan.sanction_letter && (
                    <a href={loan.sanction_letter} target="_blank" className="text-emerald-600 font-bold hover:underline">View</a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {appState.pastRecords && (
        <div className="px-3 py-2 bg-amber-50/50 rounded-lg border border-amber-100/50 italic text-[10px] text-amber-800 mb-3">
          <strong>Note:</strong> {appState.pastRecords}
        </div>
      )}

      {/* System Reasoning Log */}
      <div className="flex-1 flex flex-col min-h-0 mb-3">
        <h3 className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center">
          <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full mr-1.5 animate-pulse" />
          System Reasoning
        </h3>
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 scrollbar-hide text-[10px] bg-white rounded-lg border border-slate-100 p-2 shadow-inner">
          {appState.actionLog && appState.actionLog.length > 0 ? (
            appState.actionLog.map((log, i) => (
              <div key={i} className="flex space-x-2 items-start border-l-2 border-emerald-100 pl-2 py-0.5">
                <span className="text-slate-500 font-mono text-[8px] mt-0.5">[{i+1}]</span>
                <span className="text-slate-600 leading-tight">{log}</span>
              </div>
            ))
          ) : (
            <div className="text-slate-400 italic text-center py-4">Waiting for agent actions...</div>
          )}
        </div>
      </div>

      {/* Recent Chat Sessions */}
      {appState.pastSessions && appState.pastSessions.length > 0 && (
        <div className="flex-1 flex flex-col min-h-0 mt-3 pt-3 border-t border-slate-200">
          <h3 className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2">Recent Chats</h3>
          <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 scrollbar-hide">
            {appState.pastSessions.slice(0, 5).map((session, i) => (
              <button 
                key={i} 
                onClick={() => onLoadSession?.(session.session_id)}
                className="w-full text-left p-1.5 bg-white hover:bg-emerald-50 rounded-md border border-slate-200/60 transition-colors group"
              >
                <div className="flex justify-between items-center mb-0.5">
                  <span className="text-[10px] font-bold text-slate-700 group-hover:text-emerald-700">{new Date(session.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</span>
                  <span className="text-[8px] text-slate-400 font-mono">{session.session_id.slice(0, 8)}</span>
                </div>
                <div className="text-[9px] text-slate-500 flex justify-between">
                  <span>Phase: {session.current_phase.replace('_', ' ')}</span>
                  {session.loan_amount && <span>₹{session.loan_amount / 1000}k</span>}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
