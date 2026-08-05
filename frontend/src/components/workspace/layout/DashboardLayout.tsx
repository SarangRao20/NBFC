import { ShieldCheck, LayoutDashboard, FileText, CreditCard, Bot, LogOut, Book } from 'lucide-react';
import { useLoanStore } from '../../../store/useLoanStore';
import AgentOverlay from '../../shared/AgentOverlay';
import AnalyticsDashboard from '../pages/AnalyticsDashboard';
import GenUiApplication from '../pages/GenUiApplication';
import ActiveLoans from '../pages/ActiveLoans';
import UserProfile from '../pages/UserProfile';
import Docs from '../../../pages/Docs';

export default function DashboardLayout() {
  const { user, currentView, setView, agentLogs, isAgentActive, clearSession } = useLoanStore();

  const navigation = [
    { name: 'Dashboard', id: 'DASHBOARD', icon: LayoutDashboard },
    { name: 'System Intelligence', id: 'APPLICATION', icon: Bot },
    { name: 'Active Loans & Ledgers', id: 'ACTIVE_LOANS', icon: CreditCard },
  ];

  const renderContent = () => {
    switch (currentView) {
      case 'DASHBOARD': return <AnalyticsDashboard />;
      case 'APPLICATION': return <GenUiApplication />;
      case 'ACTIVE_LOANS': return <ActiveLoans />;
      case 'PROFILE': return <UserProfile />;
      case 'DOCS': return <Docs />;
      default: return <AnalyticsDashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white font-sans selection:bg-white/20">
      {/* Background Ambience */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-900/10 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-emerald-900/5 blur-[120px]" />
      </div>

      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Vercel-style Top Navigation */}
        <header className="sticky top-0 h-16 border-b border-white/10 bg-[#0A0A0A]/80 backdrop-blur-xl flex items-center px-6 lg:px-10 z-40">
          <div className="flex items-center gap-8 w-full max-w-7xl mx-auto">
            {/* Logo */}
            <div className="flex items-center gap-3 shrink-0 cursor-pointer" onClick={() => setView('DASHBOARD')}>
              <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
                <ShieldCheck className="w-4 h-4 text-white" />
              </div>
              <span className="font-display font-medium tracking-tight">FinServe<span className="text-white/40">.AI</span></span>
            </div>

            {/* Nav Links */}
            <nav className="hidden md:flex items-center gap-1">
              {navigation.map((item) => {
                const isActive = currentView === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setView(item.id as any)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                      isActive 
                        ? 'bg-white/10 text-white' 
                        : 'text-white/60 hover:bg-white/5 hover:text-white'
                    }`}
                  >
                    <item.icon className={`w-4 h-4 ${isActive ? 'text-emerald-500' : 'opacity-70'}`} />
                    {item.name}
                  </button>
                );
              })}
            </nav>

            {/* Profile Menu: Click on User Name / Avatar to Open Profile */}
            <div className="ml-auto flex items-center gap-4">
              <div 
                onClick={() => setView('PROFILE')}
                className="flex items-center gap-3 cursor-pointer p-1.5 rounded-xl hover:bg-white/5 transition-all group"
                title="Click to view & edit borrower profile"
              >
                <div className="text-right hidden sm:block">
                  <p className="text-sm font-medium text-white leading-none group-hover:text-emerald-400 transition-colors">{user?.name || 'Partner'}</p>
                  <p className="text-[10px] text-white/40 uppercase tracking-widest mt-1 font-mono">View Profile →</p>
                </div>
                <div className="w-9 h-9 rounded-full bg-white/10 border border-white/20 overflow-hidden flex items-center justify-center group-hover:border-emerald-500/50 transition-colors">
                   {user?.picture ? (
                      <img src={user.picture} alt="Profile" className="w-full h-full object-cover" />
                   ) : (
                      <span className="font-display font-bold text-sm">{user?.name?.charAt(0) || 'U'}</span>
                   )}
                </div>
              </div>
              <button onClick={clearSession} title="Sign Out" className="p-2 text-white/40 hover:text-white hover:bg-white/10 rounded-lg transition-all ml-1">
                 <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 w-full max-w-7xl mx-auto px-6 lg:px-10 py-8 relative">
          <div className="animate-fade-in slide-in-from-bottom-2">
             {renderContent()}
          </div>
        </main>
      </div>

      {/* Global Agent Overlay (Tool Calling UI) */}
      <AgentOverlay logs={agentLogs} isActive={isAgentActive} />
    </div>
  );
}
