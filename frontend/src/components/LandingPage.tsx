import { useState } from 'react';
import { ArrowRight, ShieldCheck, Cpu, Zap, Lock, ChevronRight, BarChart3, Globe2, Fingerprint, BookOpen } from 'lucide-react';
import AuthModal from './auth/AuthModal';
import { useLoanStore } from '../store/useLoanStore';

const Button = ({ children, className = "", variant = "default", size = "default", ...props }: any) => {
  const baseStyle = "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50";
  
  const variants: any = {
    default: "bg-white text-black shadow-lg shadow-white/10 hover:shadow-white/20 hover:scale-[1.02]",
    outline: "border border-white/10 bg-transparent text-white hover:bg-white/5",
    ghost: "text-white/70 hover:text-white hover:bg-white/5"
  };

  const sizes: any = {
    default: "h-11 px-6",
    sm: "h-9 px-4 text-xs",
    lg: "h-14 px-8 text-base",
  };

  return (
    <button className={`${baseStyle} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {children}
    </button>
  );
};

const LandingPage = () => {
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const { setView, setSessionId } = useLoanStore();

  const handleOpenAuth = () => {
    setIsAuthOpen(true);
  };

  const handleOpenDocs = () => {
    // Trigger auth flow and set the target view to DOCS
    localStorage.setItem('postAuthView', 'DOCS');
    setIsAuthOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white selection:bg-white/20 overflow-x-hidden font-sans">
      {/* Absolute Background Effects */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-900/20 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-emerald-900/10 blur-[120px]" />
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay" />
      </div>

      {/* Ultra Minimal Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.05] bg-[#0A0A0A]/80 backdrop-blur-xl">
        <div className="container mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <span className="font-display font-medium text-xl tracking-tight">FinServe<span className="text-white/40">.AI</span></span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#platform" className="text-sm text-white/60 hover:text-white transition-colors tracking-wide">Platform</a>
            <a href="#security" className="text-sm text-white/60 hover:text-white transition-colors tracking-wide">Security</a>
            <a href="#leadership" className="text-sm text-white/60 hover:text-white transition-colors tracking-wide">Company</a>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={handleOpenAuth}>Sign In</Button>
            <Button onClick={handleOpenAuth} className="hidden sm:inline-flex">
              Get Started <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </nav>

      <main className="relative z-10 pt-20">
        {/* Hero Section */}
        <section className="relative pt-32 pb-24 md:pt-48 md:pb-32 px-6">
          <div className="container mx-auto max-w-5xl text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 mb-8 animate-fade-in opacity-0" style={{ animationDelay: '0.1s', animationFillMode: 'forwards' }}>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-medium tracking-widest text-white/70 uppercase">System v2.0 Live</span>
            </div>
            
            <h1 className="font-display text-5xl md:text-7xl lg:text-8xl font-medium tracking-tight mb-8 leading-[1.1] animate-slide-up opacity-0" style={{ animationDelay: '0.2s', animationFillMode: 'forwards' }}>
              Deterministic lending.<br />
              <span className="text-white/40">Zero human latency.</span>
            </h1>
            
            <p className="text-lg md:text-xl text-white/50 max-w-2xl mx-auto mb-12 font-light tracking-wide leading-relaxed animate-slide-up opacity-0" style={{ animationDelay: '0.3s', animationFillMode: 'forwards' }}>
              FinServe orchestrates capital deployment through autonomous StateGraph engines, evaluating risk with cryptographic precision in sub-450ms.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-slide-up opacity-0" style={{ animationDelay: '0.4s', animationFillMode: 'forwards' }}>
              <Button size="lg" onClick={handleOpenAuth} className="w-full sm:w-auto min-w-[200px]">
                Initialize Protocol
              </Button>
               <Button 
                size="lg" 
                variant="outline" 
                className="w-full sm:w-auto min-w-[200px]"
                onClick={() => window.location.href = '/docs'}
              >
                <BookOpen className="w-4 h-4 mr-2" />
                View Documentation
              </Button>
            </div>
          </div>
        </section>

        {/* Bento Grid Features */}
        <section id="platform" className="py-24 px-6 border-t border-white/[0.05]">
          <div className="container mx-auto max-w-6xl">
            <div className="mb-16">
              <h2 className="font-display text-3xl md:text-4xl font-medium tracking-tight mb-4">Institutional Infrastructure</h2>
              <p className="text-white/50 text-lg max-w-xl font-light">Built from the ground up to replace legacy underwriting completely.</p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              <div className="md:col-span-2 group p-8 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.04] transition-colors relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl group-hover:bg-blue-500/20 transition-colors" />
                <Cpu className="w-8 h-8 text-white/70 mb-6" />
                <h3 className="font-display text-2xl font-medium mb-3">StateGraph Underwriting Engine</h3>
                <p className="text-white/50 leading-relaxed max-w-md font-light">
                  Our proprietary engine constructs a multidimensional risk graph by ingesting over 40,000 alternative data points, bypassing traditional CIBIL limitations to evaluate true creditworthiness.
                </p>
              </div>

              <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.04] transition-colors">
                <Zap className="w-8 h-8 text-white/70 mb-6" />
                <h3 className="font-display text-xl font-medium mb-3">Sub-450ms Decisions</h3>
                <p className="text-white/50 leading-relaxed font-light">
                  Capital is committed almost instantly. We've eliminated human bottlenecks entirely from the origination pipeline.
                </p>
              </div>

              <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.04] transition-colors">
                <Fingerprint className="w-8 h-8 text-white/70 mb-6" />
                <h3 className="font-display text-xl font-medium mb-3">Vision AI KYC</h3>
                <p className="text-white/50 leading-relaxed font-light">
                  Automated parsing of identity documents using advanced optical character recognition with 99.9% verifiable accuracy.
                </p>
              </div>

              <div className="md:col-span-2 group p-8 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.04] transition-colors flex flex-col justify-end relative overflow-hidden">
                <div className="absolute top-0 left-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl group-hover:bg-emerald-500/20 transition-colors" />
                <Globe2 className="w-8 h-8 text-white/70 mb-6" />
                <h3 className="font-display text-2xl font-medium mb-3">SHAP Explainability Protocol</h3>
                <p className="text-white/50 leading-relaxed max-w-md font-light">
                  Every decision is completely transparent. Our platform provides Shapley Additive Explanations (SHAP) for every rejection, enabling full regulatory compliance and borrower trust.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Metrics Banner */}
        <section className="py-24 border-y border-white/[0.05] bg-white/[0.01]">
          <div className="container mx-auto max-w-6xl px-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-12">
              <div>
                <p className="text-4xl md:text-5xl font-display font-medium mb-2 tracking-tight">₹250<span className="text-white/40">Cr</span></p>
                <p className="text-sm text-white/50 uppercase tracking-widest font-semibold">Volume Processed</p>
              </div>
              <div>
                <p className="text-4xl md:text-5xl font-display font-medium mb-2 tracking-tight">450<span className="text-white/40">ms</span></p>
                <p className="text-sm text-white/50 uppercase tracking-widest font-semibold">Decision Latency</p>
              </div>
              <div>
                <p className="text-4xl md:text-5xl font-display font-medium mb-2 tracking-tight">0<span className="text-white/40">%</span></p>
                <p className="text-sm text-white/50 uppercase tracking-widest font-semibold">Human Intervention</p>
              </div>
              <div>
                <p className="text-4xl md:text-5xl font-display font-medium mb-2 tracking-tight">12<span className="text-white/40">M+</span></p>
                <p className="text-sm text-white/50 uppercase tracking-widest font-semibold">Data Points Analyzed</p>
              </div>
            </div>
          </div>
        </section>

        {/* Leadership Section */}
        <section id="leadership" className="py-24 px-6 border-b border-white/[0.05]">
          <div className="container mx-auto max-w-6xl">
            <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8">
              <div>
                <h2 className="font-display text-3xl md:text-4xl font-medium tracking-tight mb-4">Core Architecture Team</h2>
                <p className="text-white/50 text-lg max-w-xl font-light">The engineers and quants building the future of autonomous finance.</p>
              </div>
            </div>

            <div className="grid md:grid-cols-3 gap-8">
              {[
                { name: "Sarang Rao", role: "Co-Founder & Systems Architect" },
                { name: "Sanvi Nyati", role: "Co-Founder & AI Engineering Lead" },
                { name: "Sumit Arya", role: "Co-Founder & Product Lead" }
              ].map((founder, i) => (
                <div key={i} className="group border-t border-white/10 pt-6">
                  <h3 className="font-display text-xl font-medium mb-1">{founder.name}</h3>
                  <p className="text-sm text-white/50 font-medium tracking-wide">{founder.role}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

      </main>

      <footer className="py-12 border-t border-white/[0.05] relative z-10 text-center text-white/40 text-sm">
        <div className="container mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <p>© {new Date().getFullYear()} FinServe Technologies Inc.</p>
          <div className="flex gap-6">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="#" className="hover:text-white transition-colors">System Status</a>
          </div>
        </div>
      </footer>

      {/* Auth Modal */}
      <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />
    </div>
  );
};

export default LandingPage;
