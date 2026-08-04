import { useLoanStore } from '../../store/useLoanStore';
import { UserCheck, Sparkles } from 'lucide-react';

export default function DemoPersonaBar() {
  const { setUser, setSessionId, updateLoanDetails } = useLoanStore();

  const personas = [
    {
      id: 'sarang',
      name: '👨‍💼 Sarang (Prime Tier-1)',
      phone: '9876543210',
      email: 'sarang@nbfc-finserve.com',
      salary: 150000,
      city: 'Mumbai',
      creditScore: 800,
      preApprovedLimit: 1500000,
      badge: 'CIBIL 800 • Instant Approval'
    },
    {
      id: 'priya',
      name: '👩‍💻 Priya (Salaried)',
      phone: '9812345678',
      email: 'priya@example.com',
      salary: 85000,
      city: 'Bengaluru',
      creditScore: 740,
      preApprovedLimit: 850000,
      badge: 'CIBIL 740 • Standard'
    },
    {
      id: 'amit',
      name: '🏬 Amit (Business Owner)',
      phone: '9899887766',
      email: 'amit@business.com',
      salary: 45000,
      city: 'Delhi',
      creditScore: 660,
      preApprovedLimit: 300000,
      badge: 'CIBIL 660 • Risk Negotiation'
    }
  ];

  const handleSelectPersona = (p: typeof personas[0]) => {
    setUser({
      name: p.name.replace(/^[^\s]+\s/, ''),
      email: p.email,
      picture: '',
      phone: p.phone,
      salary: p.salary,
      city: p.city,
      creditScore: p.creditScore,
    });
    setSessionId(null);
    updateLoanDetails({ requestedAmount: Math.min(500000, p.preApprovedLimit), tenureMonths: 36 });
  };

  return (
    <div className="bg-[#111]/90 border-b border-white/10 px-6 py-2 flex flex-wrap items-center justify-between gap-3 text-xs z-30">
      <div className="flex items-center gap-2 text-white/50 font-mono">
        <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
        <span>1-Click Evaluator Persona Switcher:</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {personas.map((p) => (
          <button
            key={p.id}
            onClick={() => handleSelectPersona(p)}
            className="px-3 py-1 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-white rounded-lg transition-all flex items-center gap-1.5 font-medium"
            title={`Switch to ${p.name} persona`}
          >
            <span>{p.name}</span>
            <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded font-mono">
              {p.badge}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
