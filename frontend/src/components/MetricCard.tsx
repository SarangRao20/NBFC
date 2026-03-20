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
      className={`bg-white p-4 rounded-2xl border shadow-sm flex flex-col justify-center items-start overflow-hidden transition-all duration-300 ${
        isAnimating ? 'border-emerald-400 ring-2 ring-emerald-400/50' : 'border-slate-100'
      }`}
    >
      <span className="text-sm text-slate-500 font-medium mb-1">{label}</span>
      <div className="text-2xl font-bold text-slate-800 flex items-baseline relative">
        {prefix && <span className="text-lg mr-1 text-slate-600">{prefix}</span>}
        <CountUp 
          end={value}
          duration={1}
          preserveValue={true}
          decimals={decimals}
          separator=","
        />
        {suffix && <span className="text-lg ml-1 text-slate-600">{suffix}</span>}
      </div>
    </motion.div>
  );
}
