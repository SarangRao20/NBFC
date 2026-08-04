import { useState } from 'react';
import { api } from '../../lib/api';
import { useLoanStore } from '../../store/useLoanStore';
import { X, Lock, Phone, User, Mail, MapPin, Briefcase, ShieldCheck, ArrowRight } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const { setUser, setSessionId } = useLoanStore();
  const [mode, setMode] = useState<'LOGIN' | 'REGISTER'>('LOGIN');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Login form fields
  const [loginPhone, setLoginPhone] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form fields
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regCity, setRegCity] = useState('');
  const [regSalary, setRegSalary] = useState('');
  const [regDob, setRegDob] = useState('');
  const [regProfession, setRegProfession] = useState('Salaried');

  if (!isOpen) return null;

  const handleGoogleOAuth = () => {
    window.location.href = 'http://localhost:8000/auth/google/login';
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const res = await api.loginWithPassword(loginPhone, loginPassword);
    setLoading(false);

    if (res.success && res.data) {
      const cust = res.data.customer_data || {};
      if (res.data.session_id) {
        setSessionId(res.data.session_id);
      }
      setUser({
        name: cust.name || 'Sarang Rao',
        email: cust.email || 'sarang@nbfc-finserve.com',
        picture: cust.picture || '',
        phone: cust.phone || loginPhone,
        salary: cust.salary || 150000,
        city: cust.city || 'Mumbai',
        creditScore: cust.credit_score || 800,
      });
      onClose();
    } else {
      setError(res.error || 'Invalid credentials');
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const res = await api.registerCustomer({
      name: regName,
      email: regEmail,
      phone: regPhone,
      password: regPassword,
      city: regCity,
      salary: Number(regSalary),
      dob: regDob,
      profession: regProfession,
    });
    setLoading(false);

    if (res.success && res.data) {
      const cust = res.data.customer_data || {};
      if (res.data.session_id) {
        setSessionId(res.data.session_id);
      }
      setUser({
        name: cust.name || regName,
        email: cust.email || regEmail,
        picture: '',
        phone: cust.phone || regPhone,
        salary: cust.salary || Number(regSalary),
        city: cust.city || regCity,
        creditScore: cust.credit_score || 785,
      });
      onClose();
    } else {
      setError(res.error || 'Registration failed');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-[#111] border border-white/10 rounded-2xl max-w-md w-full p-8 shadow-2xl relative overflow-hidden text-white">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-white/40 hover:text-white rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-white">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-display font-medium text-xl tracking-tight">Access FinServe<span className="text-white/40">.AI</span></h3>
            <p className="text-xs text-white/40">Autonomous Institutional Lending Platform</p>
          </div>
        </div>

        {/* Google OAuth Button */}
        <button
          onClick={handleGoogleOAuth}
          className="w-full h-12 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-3 mb-6 shadow-sm"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.6 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.4 9 5 12 5z" />
            <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z" />
            <path fill="#FBBC05" d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12.4 0 15.2s.7 5.5 1.9 7.9l3.7-2.9c-.6-1.1-1-2.4-1-3.7z" />
            <path fill="#34A853" d="M12 23.5c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.4-6.4-5.2L1.9 16.5C3.7 20.2 7.5 23.5 12 23.5z" />
          </svg>
          Continue with Google OAuth
        </button>

        <div className="relative flex items-center justify-center mb-6">
          <div className="border-t border-white/10 w-full" />
          <span className="bg-[#111] px-3 text-[10px] uppercase tracking-widest text-white/40 font-bold shrink-0">Or Instant Authentication</span>
          <div className="border-t border-white/10 w-full" />
        </div>

        {/* Mode Switcher */}
        <div className="flex bg-[#0A0A0A] p-1 rounded-xl border border-white/10 mb-6">
          <button
            onClick={() => { setMode('LOGIN'); setError(null); }}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
              mode === 'LOGIN' ? 'bg-white text-black shadow' : 'text-white/50 hover:text-white'
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => { setMode('REGISTER'); setError(null); }}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
              mode === 'REGISTER' ? 'bg-white text-black shadow' : 'text-white/50 hover:text-white'
            }`}
          >
            Register
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs font-medium">
            {error}
          </div>
        )}

        {/* PASSWORD LOGIN FORM */}
        {mode === 'LOGIN' && (
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">Email or Phone Number</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
                <input
                  required
                  type="text"
                  value={loginPhone}
                  onChange={(e) => setLoginPhone(e.target.value)}
                  placeholder="rahul@example.com or 99999 99999"
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
                <input
                  required
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 mt-2 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 text-sm"
            >
              {loading ? 'Authenticating...' : 'Sign In to Dashboard'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}

        {/* REGISTER FORM */}
        {mode === 'REGISTER' && (
          <form onSubmit={handleRegisterSubmit} className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">Full Name</label>
              <div className="relative">
                <User className="w-4 h-4 text-white/30 absolute left-3 top-3" />
                <input
                  required
                  type="text"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="Rahul Sharma"
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">Email</label>
                <div className="relative">
                  <Mail className="w-3.5 h-3.5 text-white/30 absolute left-3 top-3" />
                  <input
                    required
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="rahul@example.com"
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">Phone</label>
                <div className="relative">
                  <Phone className="w-3.5 h-3.5 text-white/30 absolute left-3 top-3" />
                  <input
                    required
                    type="tel"
                    value={regPhone}
                    onChange={(e) => setRegPhone(e.target.value)}
                    placeholder="9999999999"
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">Password</label>
              <div className="relative">
                <Lock className="w-3.5 h-3.5 text-white/30 absolute left-3 top-3" />
                <input
                  required
                  type="password"
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">Monthly Salary</label>
                <div className="relative">
                  <Briefcase className="w-3.5 h-3.5 text-white/30 absolute left-3 top-3" />
                  <input
                    required
                    type="number"
                    value={regSalary}
                    onChange={(e) => setRegSalary(e.target.value)}
                    placeholder="150000"
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] font-bold uppercase tracking-widest text-white/50 block mb-1">City</label>
                <div className="relative">
                  <MapPin className="w-3.5 h-3.5 text-white/30 absolute left-3 top-3" />
                  <input
                    required
                    type="text"
                    value={regCity}
                    onChange={(e) => setRegCity(e.target.value)}
                    placeholder="Bengaluru"
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-white/30 placeholder:text-white/20"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 mt-2 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50 text-xs"
            >
              {loading ? 'Creating MongoDB Record...' : 'Complete Registration'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
