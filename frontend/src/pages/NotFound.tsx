import { ShieldCheck, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white flex flex-col items-center justify-center px-6 font-sans">
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-900/20 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-red-900/10 blur-[120px]" />
      </div>

      <div className="relative z-10 text-center max-w-lg">
        <div className="flex items-center justify-center gap-3 mb-12">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <span className="font-medium text-xl tracking-tight">
            FinServe<span className="text-white/40">.AI</span>
          </span>
        </div>

        <p className="text-7xl font-bold text-white/10 mb-4 tracking-tighter">404</p>
        <h1 className="text-2xl font-medium tracking-tight mb-3">Page not found</h1>
        <p className="text-white/50 mb-10 leading-relaxed">
          The route you requested doesn't exist in this system. It may have moved or the URL may be incorrect.
        </p>

        <a
          href="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-white text-black font-semibold rounded-xl hover:bg-white/90 transition-all text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Return to Platform
        </a>
      </div>
    </div>
  );
}
