import { useEffect, useState } from 'react';
import LandingPage from './components/LandingPage';
import DashboardLayout from './components/workspace/layout/DashboardLayout';
import ProfileCompletionModal from './components/auth/ProfileCompletionModal';
import Docs from './pages/Docs';
import { useLoanStore } from './store/useLoanStore';
import { ShieldCheck } from 'lucide-react';
import { api } from './lib/api';

function App() {
  const { currentState, user, setUser, setSessionId } = useLoanStore();
  const [showProfileCompletion, setShowProfileCompletion] = useState(false);

  useEffect(() => {
    // Check URL for OAuth callback parameters
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    const name = params.get('name');
    const email = params.get('email');
    const picture = params.get('picture');
    const phone = params.get('phone');

    if (sessionId) {
      setSessionId(sessionId);
      
      api.verifySession(sessionId).then((res) => {
        if (res.success && res.data?.customer_data) {
          const cust = res.data.customer_data;
          const userObj = {
            name: cust.name || name || 'Borrower',
            email: cust.email || email || '',
            picture: cust.picture || picture || '',
            phone: cust.phone || phone || '',
            salary: cust.salary || 75000,
            city: cust.city || 'Mumbai',
            creditScore: cust.credit_score || 750,
            preApprovedLimit: cust.pre_approved_limit || 500000,
          };
          setUser(userObj);

          // Only prompt for profile completion if phone is missing or contains dummy placeholder
          if (!userObj.phone || userObj.phone.startsWith('g_') || userObj.phone.length < 10) {
            setShowProfileCompletion(true);
          } else {
            setShowProfileCompletion(false);
          }
        } else if (name || email) {
          const userObj = {
            name: name || 'Borrower',
            email: email || '',
            picture: picture || '',
            phone: phone || '',
            salary: 75000,
            creditScore: 750,
          };
          setUser(userObj);
          if (!userObj.phone || userObj.phone.length < 10) {
            setShowProfileCompletion(true);
          }
        }
      });

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
