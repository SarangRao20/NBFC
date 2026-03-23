import React, { useState, useEffect } from 'react';
import Onboarding from './Onboarding';
import Login from './Login';
import type { UserData, AuthState } from '../types';

interface AuthProps {
  onAuthenticated: (userData: UserData) => void;
}

const Auth: React.FC<AuthProps> = ({ onAuthenticated }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    isLoading: true,
    error: null,
  });
  const [showLogin, setShowLogin] = useState(true);

  useEffect(() => {
    // Check if user is already logged in (from localStorage or session)
    const checkAuthStatus = () => {
      const savedUser = localStorage.getItem('nbfc_user');
      if (savedUser) {
        try {
          const userData = JSON.parse(savedUser);
          setAuthState({
            isAuthenticated: true,
            user: userData,
            isLoading: false,
            error: null,
          });
          onAuthenticated(userData);
        } catch (error) {
          localStorage.removeItem('nbfc_user');
          setAuthState(prev => ({ ...prev, isLoading: false }));
        }
      } else {
        setAuthState(prev => ({ ...prev, isLoading: false }));
      }
    };

    checkAuthStatus();
  }, [onAuthenticated]);

  const handleLogin = (userData: UserData) => {
    localStorage.setItem('nbfc_user', JSON.stringify(userData));
    setAuthState({
      isAuthenticated: true,
      user: userData,
      isLoading: false,
      error: null,
    });
    onAuthenticated(userData);
  };

  const handleRegistrationComplete = (userData: UserData) => {
    localStorage.setItem('nbfc_user', JSON.stringify(userData));
    setAuthState({
      isAuthenticated: true,
      user: userData,
      isLoading: false,
      error: null,
    });
    onAuthenticated(userData);
  };

  const handleSwitchToRegister = () => {
    setShowLogin(false);
  };

  const handleSwitchToLogin = () => {
    setShowLogin(true);
  };

  if (authState.isLoading) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (authState.isAuthenticated && authState.user) {
    return null; // App will render the main interface
  }

  return showLogin ? (
    <Login onLogin={handleLogin} onSwitchToRegister={handleSwitchToRegister} />
  ) : (
    <Onboarding onComplete={handleRegistrationComplete} onSwitchToLogin={handleSwitchToLogin} />
  );
};

export default Auth;