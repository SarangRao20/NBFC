import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { LogIn, Phone, Lock, ArrowRight } from 'lucide-react';

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
}

interface LoginProps {
  onLogin: (userData: UserData) => void;
  onSwitchToRegister: () => void;
}

const Login: React.FC<LoginProps> = ({ onLogin, onSwitchToRegister }) => {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone || !password) {
      setError('Please enter both phone number and password.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await onLogin({ phone, password } as UserData);
    } catch (err) {
      setError('Login failed. Please try again.');
    }
    setLoading(false);
  };

  return (
    <div className="w-full h-screen flex overflow-hidden font-sans bg-slate-50 text-slate-900">
      {/* Left Sidebar */}
      <div className="w-[280px] border-r border-slate-200 bg-white flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <h1 className="text-xl font-bold text-slate-800">NBFC Login</h1>
          <p className="text-sm text-slate-600 mt-1">Welcome back</p>
        </div>

        <div className="flex-1 p-6 flex flex-col justify-center">
          <div className="space-y-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <LogIn size={32} className="text-emerald-600" />
              </div>
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Sign In to Your Account</h2>
              <p className="text-sm text-slate-600">
                Access your loan dashboard and continue your application
              </p>
            </div>

            <div className="space-y-4">
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <div className="flex items-center space-x-3 mb-2">
                  <Phone size={16} className="text-emerald-600" />
                  <span className="text-sm font-medium text-emerald-800">Phone & Password</span>
                </div>
                <p className="text-xs text-emerald-700">
                  Use the credentials you created during registration
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <div className="flex items-center space-x-3 mb-2">
                  <Lock size={16} className="text-slate-600" />
                  <span className="text-sm font-medium text-slate-800">Secure Access</span>
                </div>
                <p className="text-xs text-slate-600">
                  Your information is protected with bank-level security
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 flex items-center justify-center p-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-md space-y-8"
          >
            <div className="text-center">
              <h1 className="text-3xl font-bold text-slate-800 mb-2">Welcome Back</h1>
              <p className="text-slate-600">Sign in to your NBFC account</p>
            </div>

            <form onSubmit={handleLogin} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Phone Number
                </label>
                <input
                  type="tel"
                  placeholder="Enter your phone number"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-lg"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-lg"
                  required
                />
              </div>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-red-50 border border-red-200 rounded-xl p-4"
                >
                  <p className="text-red-600 text-sm">{error}</p>
                </motion.div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-emerald-600 text-white py-4 rounded-xl font-semibold hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2 shadow-lg hover:shadow-xl"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    <span>Signing In...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight size={20} />
                  </>
                )}
              </button>
            </form>

            <div className="text-center">
              <p className="text-slate-600">
                Don't have an account?{' '}
                <button
                  onClick={onSwitchToRegister}
                  className="text-emerald-600 font-semibold hover:text-emerald-700 transition-colors"
                >
                  Sign Up
                </button>
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Login;