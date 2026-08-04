import { useEffect, useState } from 'react';
import LandingPage from './components/LandingPage';
import DashboardLayout from './components/workspace/layout/DashboardLayout';
import ProfileCompletionModal from './components/auth/ProfileCompletionModal';
import Docs from './pages/Docs';
import { useLoanStore } from './store/useLoanStore';
import { ShieldCheck } from 'lucide-react';

function App() {
  const { currentState, user, setUser, setSessionId } = useLoanStore();
  const [showProfileCompletion, setShowProfileCompletion] = useState(false);

  useEffect(() => {
    // Check URL for OAuth callback parameters
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    const token = params.get('token');
    const name = params.get('name');

    if (sessionId && name) {
      if (sessionId) setSessionId(sessionId);
      
      setUser({
        name,
        email: 'user@example.com',
        picture: '',
        creditScore: 785,
      });

      // Prompt for remaining fields if missing
      setShowProfileCompletion(true);

      // Clean up URL parameters
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [setUser, setSessionId]);

  // Public routes accessible without authentication
  const isDocsPath = window.location.pathname === '/docs';
  if (isDocsPath) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] text-white font-sans">
        <header className="border-b border-white/10 bg-[#0A0A0A]/80 backdrop-blur-xl flex items-center px-6 lg:px-10 h-16">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => window.location.href = '/'}>
            <ShieldCheck className="w-6 h-6 text-emerald-400" />
            <span className="font-display font-bold text-xl">FinServe<span className="text-white/40">.AI</span></span>
          </div>
        </header>
        <main className="py-24 px-6">
          <Docs />
        </main>
      </div>
    );
  }

  if (currentState === 'UNAUTHENTICATED') {
    return <LandingPage />;
  }

  return (
    <>
      <DashboardLayout />
      <ProfileCompletionModal
        isOpen={showProfileCompletion}
        onCompleted={() => setShowProfileCompletion(false)}
      />
    </>
  );
}

export default App;
