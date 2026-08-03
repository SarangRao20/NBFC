import { useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { ArrowRight, Building, MapPin, Phone, Briefcase } from 'lucide-react';

export default function ProfileWidget() {
  const { setState, setUser, user } = useLoanStore();
  const [phone, setPhone] = useState('');
  const [salary, setSalary] = useState('');
  const [city, setCity] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    // Simulate instant verification and credit score pulling
    setTimeout(() => {
      setUser({
        ...user!,
        phone,
        salary: Number(salary),
        city,
        creditScore: 785 // Requested default Tier-1 prime score
      });
      setIsSubmitting(false);
      setState('ONBOARDING');
    }, 1500);
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-lg shadow-xl relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl group-hover:bg-blue-500/10 transition-colors" />
      
      <h3 className="text-xl font-display font-medium text-white mb-6 tracking-tight relative z-10">
        Identity & Income Verification
      </h3>
      
      <form onSubmit={handleSubmit} className="space-y-4 relative z-10">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-widest text-white/50">Phone Number</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Phone className="w-4 h-4 text-white/30" />
            </div>
            <input 
              required
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30 transition-colors placeholder:text-white/20"
              placeholder="+91 99999 99999"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-widest text-white/50">Monthly Net Income</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Briefcase className="w-4 h-4 text-white/30" />
            </div>
            <input 
              required
              type="number"
              value={salary}
              onChange={(e) => setSalary(e.target.value)}
              className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30 transition-colors placeholder:text-white/20"
              placeholder="₹ 1,50,000"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-widest text-white/50">City of Residence</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <MapPin className="w-4 h-4 text-white/30" />
            </div>
            <input 
              required
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30 transition-colors placeholder:text-white/20"
              placeholder="Bengaluru, Karnataka"
            />
          </div>
        </div>

        <button 
          type="submit"
          disabled={isSubmitting || !phone || !salary || !city}
          className="w-full mt-6 h-12 bg-white text-black rounded-lg font-medium shadow-lg shadow-white/10 hover:shadow-white/20 hover:scale-[1.02] transition-all disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
              Initializing Profile...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              Sync Credit Profile
              <ArrowRight className="w-4 h-4" />
            </span>
          )}
        </button>
      </form>
    </div>
  );
}
