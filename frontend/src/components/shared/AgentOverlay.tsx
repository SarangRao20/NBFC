import { Bot, Terminal, ChevronRight } from 'lucide-react';
import { useEffect, useState } from 'react';

interface AgentOverlayProps {
  logs: string[];
  isActive: boolean;
  agentName?: string;
}

export default function AgentOverlay({ logs, isActive, agentName = 'System Intelligence' }: AgentOverlayProps) {
  const [displayedLogs, setDisplayedLogs] = useState<string[]>([]);

  useEffect(() => {
    // If active, we progressively reveal the logs to simulate streaming thought process
    if (isActive) {
      if (logs.length > displayedLogs.length) {
        const timer = setTimeout(() => {
          setDisplayedLogs(logs.slice(0, displayedLogs.length + 1));
        }, 300); // 300ms artificial delay per log line for dramatic effect
        return () => clearTimeout(timer);
      }
    } else {
       // Reset when inactive
       if (displayedLogs.length > 0) {
          setTimeout(() => setDisplayedLogs([]), 500);
       }
    }
  }, [isActive, logs, displayedLogs]);

  if (!isActive) return null;

  return (
    <div className="fixed bottom-6 right-6 w-96 bg-[#0A0A0A]/95 border border-white/10 rounded-xl shadow-2xl backdrop-blur-2xl overflow-hidden z-50 animate-in slide-in-from-bottom-5">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10 bg-white/[0.02]">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
          <Bot className="w-4 h-4 text-emerald-500" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-white tracking-tight">{agentName}</h4>
          <p className="text-[10px] text-emerald-500/80 uppercase tracking-widest font-bold flex items-center gap-1">
             <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
             Executing Workflow
          </p>
        </div>
      </div>
      
      <div className="p-4 font-mono text-[11px] leading-relaxed max-h-64 overflow-y-auto">
         {displayedLogs.map((log, idx) => (
            <div key={idx} className="flex gap-2 text-white/70 animate-fade-in mb-2">
               <ChevronRight className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" />
               <span className="break-words">{log}</span>
            </div>
         ))}
         
         {/* Blinking Cursor */}
         {isActive && displayedLogs.length === logs.length && (
            <div className="flex gap-2 text-white/40 mt-2">
               <Terminal className="w-3 h-3 text-white/30 shrink-0 mt-0.5" />
               <span className="animate-pulse">Processing context via LangGraph...</span>
            </div>
         )}
      </div>
    </div>
  );
}
