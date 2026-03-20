import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const AGENT_PHASES = [
  '🤖 Master Agent analyzing...',
  '📊 Underwriting Agent calculating risk...',
  '🤝 Sales Agent drafting response...'
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
    <div className="bg-slate-50 border border-slate-200/60 shadow-sm text-slate-500 rounded-[20px] rounded-bl-[4px] p-4 max-w-[75%] flex flex-col space-y-2 relative overflow-hidden">
      <div className="flex space-x-1.5 items-center mr-1">
        <motion.div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" animate={{ y: [0, -4, 0], opacity: [0.5, 1, 0.5] }} transition={{ repeat: Infinity, duration: 0.8, delay: 0 }} />
        <motion.div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" animate={{ y: [0, -4, 0], opacity: [0.5, 1, 0.5] }} transition={{ repeat: Infinity, duration: 0.8, delay: 0.2 }} />
        <motion.div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" animate={{ y: [0, -4, 0], opacity: [0.5, 1, 0.5] }} transition={{ repeat: Infinity, duration: 0.8, delay: 0.4 }} />
      </div>

      <div className="h-5 relative w-full flex items-center min-w-[300px]">
        <AnimatePresence mode="wait">
          <motion.span
            key={phaseIndex}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="text-sm font-semibold text-slate-600 absolute left-0 whitespace-nowrap"
          >
            {AGENT_PHASES[phaseIndex]}
          </motion.span>
        </AnimatePresence>
      </div>
    </div>
  );
}
