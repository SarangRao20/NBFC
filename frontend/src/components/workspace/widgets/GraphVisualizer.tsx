import { useEffect, useState } from 'react';
import {
  UserCheck, Brain, ShieldCheck, FileSearch, Scale,
  Landmark, BadgeCheck, Banknote, CheckCircle2, Circle, Loader2,
  GitBranch
} from 'lucide-react';

// ─── DAG Node Definitions ────────────────────────────────────────────────────
const NODES = [
  { id: 'load_session',       label: 'Load Session',         sub: 'CRM Context / Profile Hydration',    icon: UserCheck },
  { id: 'intent_agent',       label: 'Intent Classifier',    sub: 'NLP → LoanRequest / EMI / General',  icon: Brain },
  { id: 'sales_agent',        label: 'Sales Agent',          sub: 'Arjun — Terms Discovery & Lenders',  icon: Landmark },
  { id: 'document_agent',     label: 'Document Agent',       sub: 'DigiLocker · OCR · Aadhaar / PAN',   icon: FileSearch },
  { id: 'kyc_agent',          label: 'KYC & Fraud Agent',    sub: 'Identity Verification · AML Check',  icon: ShieldCheck },
  { id: 'underwriting_agent', label: 'Underwriting Agent',   sub: 'FOIR · DTI · CIBIL Risk Engine',     icon: Scale },
  { id: 'sanction_agent',     label: 'Sanction Agent',       sub: 'ReportLab PDF · SMTP Dispatch',      icon: BadgeCheck },
  { id: 'bank_verification',  label: 'Bank Verification',    sub: 'Penny Drop ₹1 · eNACH Mandate',     icon: BadgeCheck },
  { id: 'disbursement',       label: 'Disbursement Node',    sub: 'Fund Release · Ledger Entry',        icon: Banknote },
];

// Map backend phase/agent identifiers → which node is active
const PHASE_TO_NODE: Record<string, string> = {
  load_session:           'load_session',
  intent:                 'intent_agent',
  sales:                  'sales_agent',
  kyc_verification:       'document_agent',
  document_verification:  'document_agent',
  kyc_agent:              'kyc_agent',
  underwriting:           'underwriting_agent',
  underwriting_agent:     'underwriting_agent',
  sanction:               'sanction_agent',
  sanction_agent:         'sanction_agent',
  bank_verification:      'bank_verification',
  bank_verification_agent:'bank_verification',
  disbursement:           'disbursement',
  active:                 'intent_agent',
};

type NodeStatus = 'done' | 'active' | 'pending';

interface GraphVisualizerProps {
  currentPhase: string;       // e.g. 'sales', 'underwriting'
  nextAgent?: string;         // e.g. 'underwriting_agent'
  isStreaming?: boolean;      // true while agent is responding
}

export default function GraphVisualizer({ currentPhase, nextAgent, isStreaming }: GraphVisualizerProps) {
  const [tickIdx, setTickIdx] = useState(0);

  // Pulse animation tick for active node
  useEffect(() => {
    const iv = setInterval(() => setTickIdx(i => i + 1), 800);
    return () => clearInterval(iv);
  }, []);

  // Determine which node is active
  const activeNodeId =
    PHASE_TO_NODE[nextAgent || ''] ||
    PHASE_TO_NODE[currentPhase] ||
    'load_session';

  const activeIdx = NODES.findIndex(n => n.id === activeNodeId);

  const getStatus = (idx: number): NodeStatus => {
    if (idx < activeIdx) return 'done';
    if (idx === activeIdx) return 'active';
    return 'pending';
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl flex flex-col overflow-hidden h-full shadow-2xl">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 bg-white/[0.02] flex items-center gap-2.5 shrink-0">
        <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
          <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-white leading-none">LangGraph DAG</p>
          <p className="text-[9px] text-white/40 font-mono uppercase tracking-wider mt-0.5">Multi-Agent Orchestration</p>
        </div>
        {isStreaming && (
          <div className="ml-auto flex items-center gap-1.5">
            <Loader2 className="w-3 h-3 text-emerald-400 animate-spin" />
            <span className="text-[9px] text-emerald-400 font-mono uppercase tracking-wide">Processing</span>
          </div>
        )}
      </div>

      {/* Node flow */}
      <div className="flex-1 overflow-y-auto p-3 space-y-0.5 scrollbar-hide">
        {NODES.map((node, idx) => {
          const status = getStatus(idx);
          const Icon = node.icon;
          const pulse = status === 'active' && tickIdx % 2 === 0;

          return (
            <div key={node.id}>
              <div
                className={`flex items-start gap-3 px-3 py-2.5 rounded-xl transition-all duration-500 ${
                  status === 'active'
                    ? 'bg-emerald-500/10 border border-emerald-500/20'
                    : status === 'done'
                    ? 'bg-white/[0.02] border border-transparent'
                    : 'border border-transparent opacity-40'
                }`}
              >
                {/* Status dot / icon */}
                <div className="shrink-0 mt-0.5">
                  {status === 'done' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  ) : status === 'active' ? (
                    <div className={`w-4 h-4 rounded-full border-2 border-emerald-400 flex items-center justify-center ${pulse ? 'shadow-[0_0_8px_2px_rgba(52,211,153,0.5)]' : ''} transition-all`}>
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    </div>
                  ) : (
                    <Circle className="w-4 h-4 text-white/20" />
                  )}
                </div>

                {/* Node info */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Icon className={`w-3 h-3 shrink-0 ${
                      status === 'done' ? 'text-emerald-400' :
                      status === 'active' ? 'text-emerald-300' :
                      'text-white/30'
                    }`} />
                    <p className={`text-xs font-semibold leading-none ${
                      status === 'done' ? 'text-white/70' :
                      status === 'active' ? 'text-white' :
                      'text-white/30'
                    }`}>{node.label}</p>
                    {status === 'active' && isStreaming && (
                      <span className="text-[8px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded-full font-mono uppercase tracking-wide ml-auto shrink-0">
                        running
                      </span>
                    )}
                    {status === 'done' && (
                      <span className="text-[8px] bg-white/5 text-white/30 px-1.5 py-0.5 rounded-full font-mono uppercase tracking-wide ml-auto shrink-0">
                        done
                      </span>
                    )}
                  </div>
                  <p className={`text-[9px] mt-1 leading-snug font-mono ${
                    status === 'active' ? 'text-emerald-400/70' :
                    status === 'done' ? 'text-white/30' :
                    'text-white/15'
                  }`}>{node.sub}</p>
                </div>
              </div>

              {/* Connector line between nodes */}
              {idx < NODES.length - 1 && (
                <div className="ml-[22px] pl-3 py-0.5">
                  <div className={`w-px h-3 ${
                    getStatus(idx) === 'done' ? 'bg-emerald-500/40' : 'bg-white/10'
                  }`} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer: active phase label */}
      <div className="px-4 py-2.5 border-t border-white/5 bg-black/20 shrink-0">
        <p className="text-[9px] text-white/30 font-mono uppercase tracking-widest">
          Phase: <span className="text-white/60">{currentPhase || 'initializing'}</span>
        </p>
      </div>
    </div>
  );
}
