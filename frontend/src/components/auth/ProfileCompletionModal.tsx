import { useState } from 'react';
import { api } from '../../lib/api';
import { useLoanStore } from '../../store/useLoanStore';
import { ShieldCheck, Phone, Briefcase, MapPin, ArrowRight } from 'lucide-react';

interface ProfileCompletionModalProps {
  isOpen: boolean;
  phoneInitial?: string;
  onCompleted: () => void;
}

export default function ProfileCompletionModal({ isOpen, phoneInitial = '', onCompleted }: ProfileCompletionModalProps) {
  const { user, setUser } = useLoanStore();
  const [phone, setPhone] = useState(phoneInitial || user?.phone || '');
  const [salary, setSalary] = useState(user?.salary ? String(user.salary) : '');
  const [city, setCity] = useState(user?.city || '');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const targetPhone = phone || user?.phone || 'g_user';
    const res = await api.updateProfile({
      phone: targetPhone,
      salary: Number(salary),
      city,
    });

    setLoading(false);

    setUser({
      ...user!,
      phone: targetPhone,
      salary: Number(salary),
      city,
    });

    onCompleted();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in">
      <div className="bg-[#111] border border-white/10 rounded-2xl max-w-md w-full p-8 shadow-2xl relative text-white">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-display font-medium text-lg text-white">Complete Google OAuth Profile</h3>
            <p className="text-xs text-white/40">Verify identity parameters to enable underwriting</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">Phone Number</label>
            <div className="relative">
              <Phone className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
              <input
                required
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 99999 99999"
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
              />
            </div>
          </div>

          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">Monthly Net Income</label>
            <div className="relative">
              <Briefcase className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
              <input
                required
                type="number"
                value={salary}
                onChange={(e) => setSalary(e.target.value)}
                placeholder="₹ 1,50,000"
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
              />
            </div>
          </div>

          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">City of Residence</label>
            <div className="relative">
              <MapPin className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
              <input
                required
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Bengaluru"
                className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-12 mt-4 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg transition-all flex items-center justify-center gap-2 text-sm disabled:opacity-50"
          >
            {loading ? 'Updating MongoDB...' : 'Save Profile & Enter Workspace'}
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
