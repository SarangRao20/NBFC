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
    <div className="w-full bg-white p-5 rounded-2xl border border-slate-100 shadow-sm mt-4">
      <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Repayment Breakdown</h3>
      <div className="h-[180px] w-full relative">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <PieChart>
            <Pie
              data={data}
              innerRadius={55}
              outerRadius={80}
              paddingAngle={2}
              dataKey="value"
              stroke="none"
              animationDuration={800}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
              formatter={(value: any) => `₹${new Intl.NumberFormat('en-IN').format(value)}`}
              contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 15px -3px rgba(0,0,0,0.1)' }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-xs text-slate-400 font-bold uppercase">Total</span>
          <span className="text-base font-black text-slate-800">
            ₹{new Intl.NumberFormat('en-IN', { notation: 'compact' }).format(totalAmount)}
          </span>
        </div>
      </div>
      <div className="flex justify-center space-x-4 mt-2">
        <div className="flex items-center text-xs font-semibold text-slate-600">
          <span className="w-2.5 h-2.5 rounded-full bg-sky-500 mr-1.5"></span> Principal
        </div>
        <div className="flex items-center text-xs font-semibold text-slate-600">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-1.5"></span> Interest
        </div>
      </div>
    </div>
  );
}
