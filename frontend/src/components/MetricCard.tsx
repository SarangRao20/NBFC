import { useEffect, useState, useRef } from 'react';
import CountUp from 'react-countup';
import { motion } from 'framer-motion';

interface Props {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}

export default function MetricCard({ label, value, prefix = '', suffix = '', decimals = 0 }: Props) {
  const [isAnimating, setIsAnimating] = useState(false);
  const prevValue = useRef(value);

  useEffect(() => {
    if (prevValue.current !== value) {
      setIsAnimating(true);
      const timer = setTimeout(() => setIsAnimating(false), 800);
      prevValue.current = value;
      return () => clearTimeout(timer);
    }
  }, [value]);

  return (
    <motion.div 
      className={`bg-white p-2 rounded-lg border shadow-sm flex flex-col justify-center items-start overflow-hidden transition-all duration-300 ${
        isAnimating ? 'border-emerald-400 ring-2 ring-emerald-400/50' : 'border-slate-100'
      }`}
    >
      <span className="text-[9px] text-slate-400 font-bold uppercase tracking-tight mb-0">{label}</span>
      <div className="text-sm font-black text-slate-800 flex items-baseline relative">
        {prefix && <span className="text-xs mr-0.5 text-slate-500">{prefix}</span>}
        <CountUp 
          end={value}
          duration={1}
          preserveValue={true}
          decimals={decimals}
          separator=","
        />
        {suffix && <span className="text-[10px] ml-0.5 text-slate-500 font-bold">{suffix}</span>}
      </div>
    </motion.div>
  );
}
