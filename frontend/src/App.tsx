import { useEffect, useState } from 'react';
import LandingPage from './components/LandingPage';
import DashboardLayout from './components/workspace/layout/DashboardLayout';
import ProfileCompletionModal from './components/auth/ProfileCompletionModal';
import { useLoanStore } from './store/useLoanStore';

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
