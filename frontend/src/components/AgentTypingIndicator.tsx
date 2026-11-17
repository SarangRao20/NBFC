import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const AGENT_PHASES = [
  'Intent Agent classifying...',
  'Supervisor routing...',
  'Sales Agent drafting response...',
  'LangGraph StateGraph reasoning...',
  'Loading session state...',
];

export default function AgentTypingIndicator() {
  const [phaseIndex, setPhaseIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPhaseIndex((prev) => (prev + 1) % AGENT_PHASES.length);
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[#0A0A0A] border border-white/10 rounded-2xl rounded-tl-sm p-4 max-w-[75%] flex flex-col space-y-2 relative overflow-hidden shadow-sm">
      <div className="flex space-x-1.5 items-center">
        <motion.div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" animate={{ y: [0, -4, 0], opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 0.8, delay: 0 }} />
        <motion.div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" animate={{ y: [0, -4, 0], opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 0.8, delay: 0.2 }} />
        <motion.div className="w-1.5 h-1.5 bg-emerald-400 rounded-full" animate={{ y: [0, -4, 0], opacity: [0.4, 1, 0.4] }} transition={{ repeat: Infinity, duration: 0.8, delay: 0.4 }} />
      </div>

      <div className="h-5 relative w-full flex items-center min-w-[260px]">
        <AnimatePresence mode="wait">
          <motion.span
            key={phaseIndex}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25 }}
            className="text-xs font-mono text-white/50 uppercase tracking-wide absolute left-0 whitespace-nowrap"
          >
            {AGENT_PHASES[phaseIndex]}
          </motion.span>
        </AnimatePresence>
      </div>
    </div>
  );
}
