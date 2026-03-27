import { motion, AnimatePresence } from 'framer-motion';
import type { AppState } from '../types';
import { User, CheckCircle2, Circle, FileText, BadgeCheck, CreditCard, Trash2, Plus, ChevronDown } from 'lucide-react';
import clsx from 'clsx';
import MetricCard from './MetricCard';
import confetti from 'canvas-confetti';
import { useEffect, useRef, useState } from 'react';

interface Props {
  appState: AppState;
  onLoadSession?: (sessionId: string) => void;
  onNewChat?: () => void;
  onPayEmi?: () => void;
  onDeleteSession?: (sessionId: string) => void;
  onSelectLender?: (lenderId: string) => void;
}

export default function DashboardPane({ appState, onLoadSession, onNewChat, onPayEmi, onDeleteSession }: Props) {
  const badgeRef = useRef<HTMLDivElement>(null);
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);

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

  function onSelectLender(_lender_id: any): void {
    throw new Error('Function not implemented.');
  }

  return (
    <div className="w-72 border-r border-slate-200 bg-slate-50 flex flex-col h-screen z-10 overflow-hidden">
      {/* Scrollable Content */}
      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-hide p-5">
        {/* Header: User Profile - Clickable */}
        <button
          onClick={() => setShowProfileDropdown(!showProfileDropdown)}
          className="w-full flex items-center justify-between mb-6 pt-1.5 hover:bg-slate-100 px-2 py-2 rounded-lg transition-colors"
        >
          <div className="flex items-center space-x-3 min-w-0">
            <div className="w-9 h-9 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600 shadow-inner flex-shrink-0">
              <User size={18} />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-slate-800 truncate">{appState.customerName || 'Guest User'}</h2>
              {appState.customerName && (
                <>
                  <div className="flex items-center text-[9px] font-bold tracking-tight text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100 w-fit uppercase mt-0.5">
                    <BadgeCheck size={10} className="mr-1" /> Existing
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1 flex items-center space-x-3">
                    <span>Score: <strong className="text-slate-700">{appState.creditScore || '-'}</strong></span>
                    <span>Salary: <strong className="text-slate-700">{appState.salary ? `₹${Number(appState.salary).toLocaleString()}` : '-'}</strong></span>
                  </div>
                </>
              )}
            </div>
          </div>
          <ChevronDown size={16} className={clsx("text-slate-400 transition-transform flex-shrink-0", showProfileDropdown && "rotate-180")} />
        </button>

        {/* Financial State */}
        <div className="mb-6">
          <div className="grid grid-cols-2 gap-2.5 mb-4">
            <MetricCard label="Principal" value={appState.requestedAmount} prefix="₹" />
            <MetricCard label="Int. Rate" value={appState.roi} decimals={1} suffix="%" />
            <MetricCard label="Monthly EMI" value={appState.emi} prefix="₹" />
            <MetricCard
              label="Est. Total Interest"
              value={Math.max(0, (appState.emi * appState.tenure) - appState.requestedAmount)}
              prefix="₹"
            />
            <MetricCard label="Salary" value={appState.salary || 0} prefix="₹" />
            <MetricCard label="Credit Score" value={appState.creditScore || 0} />
          </div>

          {/* Minimal summary only. Removed redundant repayment summary as per user request. */}

          {/* Payment CTA */}
          {appState.underwritingStatus === 'Approved' && appState.emi > 0 && (
            <div className="mt-4 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
              <div className="flex justify-between items-center mb-2">
                <span className="text-[10px] font-bold text-emerald-800 uppercase">Active Repayment</span>
                <span className="text-[10px] font-bold text-emerald-600">
                  {appState.loan_terms?.payments_made || 0} / {appState.tenure} Paid
                </span>
              </div>
              <button
                onClick={onPayEmi}
                className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-[11px] font-bold flex items-center justify-center transition-all shadow-sm"
              >
                <CreditCard size={14} className="mr-2" /> Pay Next EMI
              </button>
            </div>
          )}
        </div>

        {/* Underwriting Status */}
        <div className="mb-6">
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



        {/* Past Sessions */}
        {appState.pastLoans && appState.pastLoans.length > 0 && (
          <div className="mt-6 pt-5 border-t border-slate-200">
            <h3 className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-3">Past Loan History</h3>
            <div className="space-y-2.5">
              {appState.pastLoans.slice(0, 2).map((loan, i) => (
                <div key={i} className="p-2.5 bg-slate-100/50 rounded-md border border-slate-200/60">
                  <div className="flex justify-between items-start mb-1.5">
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

        {/* Eligible Lenders */}
        {appState.eligible_offers && appState.eligible_offers.length > 0 && (
          <div className="p-4 border-t border-slate-200">
            <h3 className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-3">Eligible Lenders</h3>
            <div className="space-y-2">
              {appState.eligible_offers.map((offer: any) => (
                <div key={offer.lender_id} className="flex items-center justify-between p-2 bg-white rounded-md border border-slate-100">
                  <div>
                    <div className="text-[11px] font-bold text-slate-800">{offer.lender_name}</div>
                    <div className="text-[9px] text-slate-500">Rate: {offer.interest_rate}% • EMI: ₹{Number(offer.emi).toLocaleString()}</div>
                  </div>
                  <div>
                    <button
                      onClick={() => onSelectLender?.(offer.lender_id)}
                      className="text-[11px] font-bold bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded"
                    >
                      Select
                    </button>
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

      </div>

      {/* Profile Dropdown Modal - Previous Chats (Compact) */}
      <AnimatePresence>
        {showProfileDropdown && appState.pastSessions && appState.pastSessions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-[90px] left-5 w-56 max-h-96 bg-white rounded-lg border border-slate-200 shadow-lg z-50 overflow-y-auto"
          >
            <div className="sticky top-0 bg-white border-b border-slate-100 px-3 py-2 flex justify-between items-center">
              <h3 className="text-[10px] font-bold text-slate-600 uppercase tracking-wider">Previous Chats</h3>
              <button
                onClick={onNewChat}
                className="text-[10px] bg-emerald-600 text-white px-1.5 py-0.5 rounded font-bold hover:bg-emerald-700 transition-colors flex items-center"
              >
                <Plus size={10} className="mr-0.5" /> New
              </button>
            </div>
            <div className="space-y-1.5 p-2">
              {appState.pastSessions.map((session, i) => (
                <div key={i} className="flex space-x-1.5 group">
                  <button
                    onClick={() => {
                      onLoadSession?.(session.session_id);
                      setShowProfileDropdown(false);
                    }}
                    className="flex-1 text-left p-2 bg-slate-50 hover:bg-emerald-50 rounded-md border border-slate-150 transition-colors"
                  >
                    {/* Loan Amount & Type - Compact */}
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[9px] font-bold text-slate-900">
                        ₹{session.loan_amount ? (session.loan_amount / 100000).toFixed(1) : '0'}L
                      </span>
                      <span className="text-[6px] font-bold text-slate-500 uppercase tracking-tight bg-slate-100 px-1 py-0.5 rounded">
                        {session.loan_type || 'Personal'}
                      </span>
                    </div>
                    {/* Status - Compact with new labels */}
                    <div className="text-[7px]">
                      <span className={clsx(
                        "inline-block px-1.5 py-0.5 rounded font-semibold",
                        session.display_status === 'approved' ? "bg-emerald-100 text-emerald-700" :
                          session.display_status === 'in_process' ? "bg-blue-100 text-blue-700" :
                            session.display_status === 'rejected' ? "bg-red-100 text-red-700" :
                              "bg-slate-100 text-slate-600"
                      )}>
                        {session.display_status === 'approved' ? 'Approved' :
                          session.display_status === 'in_process' ? 'In Process' :
                            session.display_status === 'rejected' ? 'Rejected' :
                              'Pending'}
                      </span>
                    </div>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm('Delete this chat history?')) {
                        onDeleteSession?.(session.session_id);
                      }
                    }}
                    className="p-1 text-slate-300 hover:text-red-600 hover:bg-red-50 rounded transition-all flex items-center justify-center border border-slate-150 bg-slate-50 hover:border-red-200"
                    title="Delete Chat"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
            {/* KYC Documents in Profile Dropdown */}
            <div className="border-t border-slate-100 mt-2 pt-2">
              <h4 className="text-[8px] font-bold text-slate-400 uppercase tracking-wider mb-2 px-2">KYC Documents</h4>
              <div className="grid grid-cols-2 gap-1.5 px-2 pb-2">
                <div className="flex items-center justify-between p-1.5 bg-slate-50 rounded-md border border-slate-150">
                  <div className="flex items-center text-[9px] font-bold text-slate-600 truncate mr-1">
                    <FileText size={10} className="mr-1 text-slate-400" /> PAN
                  </div>
                  {appState.documents.pan === 'verified' ? (
                    <CheckCircle2 size={12} className="text-emerald-500 flex-shrink-0" />
                  ) : (
                    <Circle size={12} className="text-slate-200 flex-shrink-0" />
                  )}
                </div>
                <div className="flex items-center justify-between p-1.5 bg-slate-50 rounded-md border border-slate-150">
                  <div className="flex items-center text-[9px] font-bold text-slate-600 truncate mr-1">
                    <FileText size={10} className="mr-1 text-slate-400" /> Income
                  </div>
                  {appState.documents.bankStatement === 'verified' ? (
                    <CheckCircle2 size={12} className="text-emerald-500 flex-shrink-0" />
                  ) : (
                    <Circle size={12} className="text-slate-200 flex-shrink-0" />
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
