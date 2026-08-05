import { useState } from 'react';
import { useLoanStore } from '../../../store/useLoanStore';
import { User, Phone, Mail, MapPin, Briefcase, TrendingUp, ShieldCheck, CheckCircle2, Save, Building2, CreditCard } from 'lucide-react';
import { api } from '../../../lib/api';

export default function UserProfile() {
  const { user, setUser } = useLoanStore();

  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [phone, setPhone] = useState(user?.phone || '');
  const [city, setCity] = useState(user?.city || 'Mumbai, Maharashtra');
  const [salary, setSalary] = useState(user?.salary || 75000);
  const [picture, setPicture] = useState(user?.picture || '');
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const creditScore = user?.creditScore || 785;
  const preApprovedLimit = user?.salary ? user.salary * 10 : 1500000;

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      const targetIdentifier = phone || user?.phone || email || user?.email || '';
      if (targetIdentifier) {
        await api.updateProfile({
          phone: targetIdentifier,
          name,
          email,
          city,
          salary: Number(salary),
          credit_score: creditScore,
          picture
        });
      }

      setUser({
        ...user!,
        name,
        email,
        phone: phone || user?.phone || '',
        city,
        salary: Number(salary),
        picture,
        creditScore
      });

      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto pb-12 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-medium text-white tracking-tight">Verified Borrower Profile</h1>
        <p className="text-white/60 text-sm mt-1">Manage institutional credit telemetry, verified income, and linked account settings.</p>
      </div>

      {/* Main Profile Card Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Telemetry Card */}
        <div className="bg-[#111] border border-white/10 rounded-2xl p-6 space-y-6">
          <div className="flex flex-col items-center text-center space-y-3 pb-6 border-b border-white/10">
            <div className="w-20 h-20 rounded-full bg-white/10 border-2 border-emerald-500/40 p-1 flex items-center justify-center overflow-hidden relative group">
              {picture || user?.picture ? (
                <img src={picture || user?.picture} alt={name} className="w-full h-full object-cover rounded-full" />
              ) : (
                <span className="font-display font-bold text-2xl text-white">{name.charAt(0) || 'U'}</span>
              )}
            </div>
            <div>
              <h3 className="font-display font-bold text-lg text-white">{name || 'Verified User'}</h3>
              <p className="text-xs text-white/50">{phone || user?.phone || email || 'No phone set'}</p>
            </div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5" /> Tier-1 Verified Entity
            </span>
          </div>

          {/* Telemetry Metrics */}
          <div className="space-y-4 font-mono text-xs">
            <div className="flex justify-between items-center p-3 bg-[#0A0A0A] rounded-xl border border-white/5">
              <span className="text-white/50 font-sans">CIBIL Telemetry</span>
              <span className="font-bold text-emerald-400 text-sm flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5" /> {creditScore}
              </span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[#0A0A0A] rounded-xl border border-white/5">
              <span className="text-white/50 font-sans">Pre-Approved Limit</span>
              <span className="font-bold text-white text-sm">₹{preApprovedLimit.toLocaleString('en-IN')}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[#0A0A0A] rounded-xl border border-white/5">
              <span className="text-white/50 font-sans">Verification Status</span>
              <span className="text-emerald-400 font-bold uppercase font-sans">UIDAI & ITD Verified</span>
            </div>
          </div>
        </div>

        {/* Right Form Editor */}
        <div className="md:col-span-2 bg-[#111] border border-white/10 rounded-2xl p-6 md:p-8 space-y-6">
          <h3 className="text-lg font-display font-medium text-white pb-4 border-b border-white/10">Personal & Financial Telemetry Settings</h3>

          {savedSuccess && (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 font-medium text-xs flex items-center gap-2 animate-fade-in">
              <CheckCircle2 className="w-4 h-4" /> Profile telemetry updated successfully in MongoDB Atlas.
            </div>
          )}

          <form onSubmit={handleSaveProfile} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-white/50">Full Name</label>
                <div className="relative">
                  <User className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-white/50">Email Address</label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-white/50">Phone Number</label>
                <div className="relative">
                  <Phone className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+91 98765 43210"
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-white/50">Profile Picture URL</label>
                <div className="relative">
                  <User className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
                  <input
                    type="text"
                    value={picture}
                    onChange={(e) => setPicture(e.target.value)}
                    placeholder="https://lh3.googleusercontent.com/..."
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-white/50">Monthly Net Income (₹)</label>
                <div className="relative">
                  <Briefcase className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
                  <input
                    type="number"
                    value={salary}
                    onChange={(e) => setSalary(Number(e.target.value))}
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-widest text-white/50">City of Residence</label>
                <div className="relative">
                  <MapPin className="w-4 h-4 text-white/30 absolute left-3 top-3.5" />
                  <input
                    type="text"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="w-full bg-[#0A0A0A] border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm text-white focus:outline-none focus:border-white/30"
                  />
                </div>
              </div>
            </div>

            {/* Linked Bank Telemetry */}
            <div className="pt-4 border-t border-white/10">
              <h4 className="text-xs font-semibold uppercase tracking-widest text-white/50 mb-3">Linked Bank Account Telemetry</h4>
              <div className="grid grid-cols-2 gap-4 bg-[#0A0A0A] p-4 rounded-xl border border-white/5 font-mono text-xs">
                <div>
                  <span className="text-white/40 block font-sans text-[10px]">Bank Partner</span>
                  <span className="text-white font-bold flex items-center gap-1.5 mt-1">
                    <Building2 className="w-3.5 h-3.5 text-blue-400" /> HDFC Bank Ltd
                  </span>
                </div>
                <div>
                  <span className="text-white/40 block font-sans text-[10px]">Account Number</span>
                  <span className="text-white font-bold flex items-center gap-1.5 mt-1">
                    <CreditCard className="w-3.5 h-3.5 text-emerald-400" /> XXXXXX9821
                  </span>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSaving}
              className="w-full h-12 bg-white text-black font-semibold rounded-xl hover:bg-white/90 shadow-lg shadow-white/10 transition-all text-sm flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isSaving ? (
                <>
                  <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                  Saving Profile Telemetry...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" /> Save Profile Telemetry
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
