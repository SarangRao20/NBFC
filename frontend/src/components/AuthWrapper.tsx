import React, { useState } from 'react';
import Login from './Login';
import Onboarding from './Onboarding';
import { BASE_URL } from '../api/client';


interface UserData {
  name: string;
  phone: string;
  dob: string;
  profession: string;
  address: string;
  email: string;
  password: string;
  city?: string;
  salary?: number;
  credit_score?: number;
  pre_approved_limit?: number;
}

interface AuthWrapperProps {
  onAuthComplete: (userData: UserData, sessionId: string) => void;
}

const AuthWrapper: React.FC<AuthWrapperProps> = ({ onAuthComplete }) => {
  const [currentView, setCurrentView] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (userData: UserData) => {
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('phone', userData.phone);
      formData.append('password', userData.password);

      const response = await fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      });
      
      const result = await response.json();
      
      if (response.ok && result.success && result.session_id) {
        onAuthComplete(result.customer_data, result.session_id);
      } else {
        throw new Error(result.detail || result.message || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      alert(error instanceof Error ? error.message : 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (userData: UserData) => {
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('phone', userData.phone);
      formData.append('email', userData.email);
      formData.append('name', userData.name);
      formData.append('password', userData.password);
      if (userData.city) formData.append('city', userData.city);
      if (userData.salary) formData.append('salary', userData.salary.toString());
      if (userData.dob) formData.append('dob', userData.dob);
      if (userData.profession) formData.append('profession', userData.profession);
      if (userData.address) formData.append('address', userData.address);
      
      const response = await fetch(`${BASE_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      });
      
      const result = await response.json();
      
      if (response.ok && result.success) {
        // Auto-login after successful registration
        await handleLogin(userData);
      } else {
        throw new Error(result.detail || result.message || 'Registration failed');
      }
    } catch (error) {
      console.error('Registration error:', error);
      alert(error instanceof Error ? error.message : 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto"></div>
          <p className="text-slate-600">Processing...</p>
        </div>
      </div>
    );
  }

  if (currentView === 'login') {
    return (
      <Login 
        onLogin={handleLogin}
        onSwitchToRegister={() => setCurrentView('register')}
      />
    );
  }

  return (
    <Onboarding 
      onComplete={handleRegister}
      onSwitchToLogin={() => setCurrentView('login')}
    />
  );
};

export default AuthWrapper;
