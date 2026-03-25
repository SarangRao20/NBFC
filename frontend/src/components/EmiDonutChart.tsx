import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface Props {
  principal: number;
  emi: number;
  tenure: number;
}

export default function EmiDonutChart({ principal, emi, tenure }: Props) {
  const totalAmount = emi * tenure;
  const totalInterest = totalAmount - principal;

  const data = [
    { name: 'Principal', value: principal, color: '#0ea5e9' }, // sky-500
    { name: 'Total Interest', value: Math.max(0, totalInterest), color: '#10b981' } // emerald-500
  ];

  return (
    <div className="w-full bg-white p-3 rounded-lg border border-slate-100 shadow-sm mt-3">
      <h3 className="text-xs font-bold text-slate-700 mb-2">Repayment Summary</h3>
      <div className="grid grid-cols-1 gap-2">
        <div className="flex justify-between items-center p-2 bg-slate-50 rounded-md border border-slate-100">
          <div className="text-xs text-slate-500">Principal Amount</div>
          <div className="text-sm font-bold text-slate-900">₹{new Intl.NumberFormat('en-IN').format(principal)}</div>
        </div>
        <div className="flex justify-between items-center p-2 bg-slate-50 rounded-md border border-slate-100">
          <div className="text-xs text-slate-500">Total Interest</div>
          <div className="text-sm font-bold text-slate-900">₹{new Intl.NumberFormat('en-IN').format(Math.max(0, totalInterest))}</div>
        </div>
        <div className="flex justify-between items-center p-2 bg-slate-50 rounded-md border border-slate-100">
          <div className="text-xs text-slate-500">Total Payable</div>
          <div className="text-sm font-bold text-slate-900">₹{new Intl.NumberFormat('en-IN').format(totalAmount)}</div>
        </div>
      </div>
    </div>
  );
}
