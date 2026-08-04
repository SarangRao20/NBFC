import { BookOpen, Users, Zap, Shield, BarChart3, Globe2, Cpu, Lock, FileText, ArrowRight, Globe } from 'lucide-react';

export default function Docs() {
  return (
    <div className="max-w-5xl mx-auto space-y-16 py-8">
      {/* Hero */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-white tracking-tight">FinServe Platform</h1>
        <p className="text-lg text-white/60 max-w-2xl mx-auto">
          An autonomous lending infrastructure powered by state-graph orchestration,
          real-time credit profiling, and cryptographic-grade risk underwriting.
        </p>
        <div className="flex items-center justify-center gap-4 text-sm text-white/40 pt-2">
          <span className="flex items-center gap-1.5"><Globe className="w-4 h-4" /> Production</span>
          <span className="flex items-center gap-1.5"><Cpu className="w-4 h-4" /> v1.0.0</span>
        </div>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: Zap, label: 'Quick Start', desc: 'Get loan in 4 steps' },
          { icon: FileText, label: 'API Endpoints', desc: 'REST interface' },
          { icon: BarChart3, label: 'Analytics', desc: 'Dashboard overview' },
          { icon: Shield, label: 'Security', desc: 'Encryption & auth' },
        ].map((item, i) => (
          <div key={i} className="border border-white/10 bg-white/[0.02] rounded-lg p-4 text-center hover:bg-white/5 transition-colors cursor-pointer">
            <item.icon className="w-6 h-6 text-emerald-400 mb-2 mx-auto" />
            <p className="text-xs font-medium text-white/70">{item.label}</p>
            <p className="text-xs text-white/40">{item.desc}</p>
          </div>
        ))}
      </div>

      {/* Workflow */}
      <section className="space-y-6">
        <h2 className="text-2xl font-semibold text-white tracking-tight">Borrower Workflow</h2>
        <div className="border border-white/10 bg-[#0d0d0d] rounded-lg p-6">
          <ol className="space-y-6 ml-0">
            {[
              { step: 1, title: 'Create Account', icon: Globe, description: 'Register using phone OTP or Google SSO to secure your identity.' },
              { step: 2, title: 'Complete Profile', icon: FileText, description: 'Provide income, employment, PAN, Aadhar, and upload documents.' },
              { step: 3, title: 'AI Underwriting', icon: Cpu, description: 'Dual‑LLM decisioning engine evaluates credit worthiness in under 400ms.' },
              { step: 4, title: 'Accept & Disburse', icon: ArrowRight, description: 'Review offer, e‑sign the sanction letter, and receive funds.' },
            ].map((s) => (
              <li key={s.step} className="flex items-start gap-4">
                <div className="mt-1 w-10 h-10 flex-shrink-0 rounded-full border border-emerald-500/30 bg-emerald-500/10 flex items-center justify-center">
                  <span className="text-xs font-mono text-emerald-300">{s.step}</span>
                </div>
                <div>
                  <p className="font-medium text-white">{s.title}</p>
                  <p className="text-sm text-white/50 mt-0.5">{s.description}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* API Table */}
      <section className="space-y-6">
        <h2 className="text-2xl font-semibold text-white">Core API Routes</h2>
        <div className="border border-white/10 rounded-lg overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="bg-white/5">
              <tr>
                <th className="py-3 px-4 font-medium text-white/80">Endpoint</th>
                <th className="py-3 px-4 font-medium text-white/80">Method</th>
                <th className="py-3 px-4 font-medium text-white/80">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['/api/auth/signup', 'POST', 'Create new borrower account'],
                ['/api/auth/login', 'POST', 'Authenticate existing user'],
                ['/api/auth/google', 'GET', 'Initiate OAuth flow'],
                ['/api/underwriting/evaluate', 'POST', 'AI risk scoring'],
                ['/api/sanction/generate', 'POST', 'Issue loan agreement'],
                ['/api/loan/repay', 'POST', 'Process EMI payment'],
                ['/api/admin/dashboard', 'GET', 'Administrator overview'],
              ].map(([endpoint, method, desc]) => (
                <tr key={`${endpoint}`} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 px-4 font-mono text-emerald-300 text-xs">{endpoint}</td>
                  <td className="py-3 px-4 text-xs">
                    <span className="bg-white/10 text-white/70 px-2 py-0.5 rounded text-xs font-mono">{method}</span>
                  </td>
                  <td className="py-3 px-4 text-white/50">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Security & Compliance */}
      <section className="space-y-6">
        <h2 className="text-2xl font-semibold text-white">Security & Compliance</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: Lock, title: 'End‑to‑end Encryption', description: 'All data in transit is protected by TLS 1.3 and at rest by AES‑256.' },
            { icon: Shield, title: 'GDPR / PDP Bill', description: 'We comply with Indian DPDP Act 2023 and global data privacy rules.' },
            { icon: BarChart3, title: 'Audit Logs', description: 'Every underwriting decision is recorded immutably for regulatory reporting.' },
          ].map((item, i) => (
            <div key={i} className="border border-white/10 rounded-lg p-4 bg-[#0d0d0d]">
              <item.icon className="w-6 h-6 text-blue-400 mb-2" />
              <p className="font-medium text-white text-sm">{item.title}</p>
              <p className="text-xs text-white/50 mt-1">{item.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ — compact */}
      <section className="space-y-6">
        <h2 className="text-2xl font-semibold text-white">FAQ</h2>
        {[
          { q: 'How are interest rates determined?', a: 'Our dual‑LLM engine computes prime‑adjusted rates using 18 financial variables, including CIBIL, DTI, and employer‑class.' },
          { q: 'Can I prepay my loan?', a: 'Yes. Pre‑closure is permitted any time subject to a 24‑hour cooling period. Visit Active Loans → Prepay.' },
          { q: 'What is the maximum loan amount?', a: 'Self‑employed: ₹50L. Salaried: up to ₹1Cr, based on exposure‑multiplier and bureau score.' },
        ].map((item, i) => (
          <div key={i} className="border-b border-white/10 pb-4 last:border-0">
            <p className="text-white font-medium text-sm">{item.q}</p>
            <p className="text-white/50 text-sm mt-1">{item.a}</p>
          </div>
        ))}
      </section>

      {/* Bottom CTA */}
      <div className="text-center pb-12">
        <a href="/" className="inline-flex items-center gap-2 px-6 py-3 rounded-full border border-white/10 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-sm font-medium transition-colors">
          <Globe className="w-4 h-4" />
          Back to FinServe AI
          <ArrowRight className="w-4 h-4" />
        </a>
      </div>
    </div>
  );
}
