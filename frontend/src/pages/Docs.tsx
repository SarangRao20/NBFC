import { HelpCircle, User, FileText, Clock, Banknote } from 'lucide-react';

export default function Docs() {
  const faqs = [
    {
      icon: <User className="w-5 h-5 text-emerald-400" />,
      q: "How do I start an application?",
      a: "Click 'Initialize Protocol' on the landing page and complete registration via OTP/email or Google login.",
    },
    {
      icon: <FileText className="w-5 h-5 text-blue-400" />,
      q: "What documents are required?",
      a: "A valid ID (Aadhaar/PAN), income proof (salary slip/form 16), bank statements, and employment details.",
    },
    {
      icon: <Clock className="w-5 h-5 text-yellow-400" />,
      q: "How long does approval take?",
      a: "Our AI system processes applications instantly — decisions appear within seconds. Final disbursement may take 1–2 business days.",
    },
    {
      icon: <Banknote className="w-5 h-5 text-purple-400" />,
      q: "Can I track my loan status?",
      a: "Yes! Once logged in, check 'Active Loans' to track repayment schedules, balances, and status updates in real-time.",
    },
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-10">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-white mb-2">FinServe Borrower Guide</h1>
        <p className="text-white/60">Learn how our intelligent lending platform works</p>
      </div>

      {/* Steps */}
      <div className="space-y-6">
        <h2 className="text-xl font-semibold text-white">Loan Process Overview</h2>
        <ol className="relative border-l border-white/10 ml-4 pl-6 space-y-6">
          <li className="mb-6">
            <span className="absolute w-6 h-6 flex items-center justify-center bg-emerald-500/20 border border-emerald-500/30 rounded-full -left-3 flex-shrink-0">1</span>
            <h3 className="font-medium text-white">Register with OTP</h3>
            <p className="text-sm text-white/70">Enter your phone/email and complete identity verification.</p>
          </li>
          <li className="mb-6">
            <span className="absolute w-6 h-6 flex items-center justify-center bg-emerald-500/20 border border-emerald-500/30 rounded-full -left-3 flex-shrink-0">2</span>
            <h3 className="font-medium text-white">Fill Application Form</h3>
            <p className="text-sm text-white/70">Provide personal info, employment, income, and contact details.</p>
          </li>
          <li className="mb-6">
            <span className="absolute w-6 h-6 flex items-center justify-center bg-emerald-500/20 border border-emerald-500/30 rounded-full -left-3 flex-shrink-0">3</span>
            <h3 className="font-medium text-white">Instant AI Decision</h3>
            <p className="text-sm text-white/70">Within seconds, our AI analyzes your profile and makes an offer decision.</p>
          </li>
          <li className="mb-6">
            <span className="absolute w-6 h-6 flex items-center justify-center bg-emerald-500/20 border border-emerald-500/30 rounded-full -left-3 flex-shrink-0">4</span>
            <h3 className="font-medium text-white">Accept Offer & Disbursement</h3>
            <p className="text-sm text-white/70">Review terms, accept digitally, and receive funds in your linked account.</p>
          </li>
        </ol>
      </div>

      {/* FAQs */}
      <div className="space-y-6">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <HelpCircle className="w-5 h-5" />
          Frequently Asked Questions
        </h2>
        {faqs.map((f, i) => (
          <div key={i} className="border border-white/10 bg-[#111]/60 backdrop-blur-sm rounded-lg p-4 hover:bg-[#111]/80 transition-colors">
            <div className="flex items-start gap-3">
              <div className="mt-0.5">{f.icon}</div>
              <div>
                <p className="font-medium text-white">{f.q}</p>
                <p className="text-sm text-white/70 mt-1">{f.a}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
