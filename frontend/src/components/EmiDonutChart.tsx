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
    <div className="w-full bg-white p-2 rounded-lg border border-slate-100 shadow-sm mt-3">
      <h3 className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Repayment Breakdown</h3>
      <div className="h-[100px] w-full relative">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <PieChart>
            <Pie
              data={data}
              innerRadius={28}
              outerRadius={40}
              paddingAngle={1}
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
              contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 15px -3px rgba(0,0,0,0.1)', fontSize: '10px' }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-sm font-black text-slate-800">
            ₹{new Intl.NumberFormat('en-IN', { notation: 'compact' }).format(totalAmount)}
          </span>
        </div>
      </div>
      <div className="flex justify-center space-x-2 mt-0.5">
        <div className="flex items-center text-[8px] font-bold text-slate-500 uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-500 mr-1"></span> Principal
        </div>
        <div className="flex items-center text-[8px] font-bold text-slate-500 uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1"></span> Interest
        </div>
      </div>
    </div>
  );
}
