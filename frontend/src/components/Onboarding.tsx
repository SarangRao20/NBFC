import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Phone, Mail, FileText, Lock, CheckCircle2, ArrowRight, ArrowLeft } from 'lucide-react';
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

interface OnboardingProps {
  onComplete: (userData: UserData) => void;
  onSwitchToLogin?: () => void;
}

type Step = 'welcome' | 'phone' | 'otp-phone' | 'email' | 'otp-email' | 'details' | 'password' | 'complete';

const Onboarding: React.FC<OnboardingProps> = ({ onComplete, onSwitchToLogin }) => {
  const [currentStep, setCurrentStep] = useState<Step>('welcome');
  const [userData, setUserData] = useState<Partial<UserData>>({});
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [isDevMode, setIsDevMode] = useState(false);

  const updateUserData = (field: keyof UserData, value: string) => {
    setUserData(prev => ({ ...prev, [field]: value }));
  };

  const handleSendPhoneOTP = async () => {
    if (!userData.phone) return;

    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${BASE_URL}/auth/send-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `phone=${userData.phone}&email=${userData.email || ''}`
      });
      
      const result = await response.json();
      const devMode = Boolean(result.dev_mode);
      setIsDevMode(devMode);

      if (devMode && result.dev_otp) {
        setDevOtp(result.dev_otp);
      } else {
        setDevOtp(null);
      }
      setCurrentStep('otp-phone');
    } catch (err) {
      setError('Failed to send OTP. Please try again.');
    }
    setLoading(false);
  };

  const handleVerifyPhoneOTP = async () => {
    if (!otp || !userData.phone) return;

    setLoading(true);
    setError('');
    try {
      const formData = new URLSearchParams();
      formData.append('phone', userData.phone);
      formData.append('otp', otp);
      if (isDevMode) formData.append('use_dev_otp', 'true');

      const response = await fetch(`${BASE_URL}/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      });

      const result = await response.json();
      if (result.success) {
        setCurrentStep('email');
      } else {
        setError('Invalid OTP. Please try again.');
      }
    } catch (err) {
      setError('Failed to verify OTP. Please try again.');
    }
    setLoading(false);
  };

  const handleSendEmailOTP = async () => {
    if (!userData.email) return;

    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${BASE_URL}/auth/send-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `phone=${userData.phone!}&email=${userData.email}`
      });
      
      const result = await response.json();
      const devMode = Boolean(result.dev_mode);
      setIsDevMode(devMode);

      if (devMode && result.dev_otp) {
        setDevOtp(result.dev_otp);
      } else {
        setDevOtp(null);
      }
      setCurrentStep('otp-email');
    } catch (err) {
      setError('Failed to send OTP. Please try again.');
    }
    setLoading(false);
  };

  const handleVerifyEmailOTP = async () => {
    if (!otp || !userData.phone) return;

    setLoading(true);
    setError('');
    try {
      const formData = new URLSearchParams();
      formData.append('phone', userData.phone);
      formData.append('otp', otp);
      if (isDevMode) formData.append('use_dev_otp', 'true');

      const response = await fetch(`${BASE_URL}/auth/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      });

      const result = await response.json();
      if (result.success) {
        setCurrentStep('details');
      } else {
        setError('Invalid OTP. Please try again.');
      }
    } catch (err) {
      setError('Failed to verify OTP. Please try again.');
    }
    setLoading(false);
  };

  const handleCompleteRegistration = async () => {
    if (!userData.name || !userData.dob || !userData.profession || !userData.address || !userData.salary || !userData.password) {
      setError('Please fill in all required fields.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await onComplete(userData as UserData);
    } catch (err) {
      setError('Registration failed. Please try again.');
    }
    setLoading(false);
  };

  const steps = [
    { key: 'welcome', label: 'Welcome', icon: User },
    { key: 'phone', label: 'Phone', icon: Phone },
    { key: 'otp-phone', label: 'Verify', icon: CheckCircle2 },
    { key: 'email', label: 'Email', icon: Mail },
    { key: 'otp-email', label: 'Verify', icon: CheckCircle2 },
    { key: 'details', label: 'Details', icon: FileText },
    { key: 'password', label: 'Password', icon: Lock },
    { key: 'complete', label: 'Complete', icon: CheckCircle2 },
  ];

  const currentStepIndex = steps.findIndex(step => step.key === currentStep);

  const renderWelcome = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center h-full text-center space-y-8"
    >
      <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center shadow-inner">
        <User size={32} className="text-emerald-600" />
      </div>
      <div className="space-y-4">
        <h1 className="text-4xl font-bold text-slate-800">Welcome to NBFC</h1>
        <p className="text-lg text-slate-600 max-w-md">
          Let's get you set up with your account for seamless loan processing
        </p>
      </div>
      <button
        onClick={() => setCurrentStep('phone')}
        className="bg-emerald-600 text-white px-8 py-4 rounded-xl font-semibold hover:bg-emerald-700 transition-colors shadow-lg hover:shadow-xl flex items-center space-x-2"
      >
        <span>Get Started</span>
        <ArrowRight size={20} />
      </button>

      {onSwitchToLogin && (
        <p className="text-slate-600 text-center">
          Already have an account?{' '}
          <button
            onClick={onSwitchToLogin}
            className="text-emerald-600 font-semibold hover:text-emerald-700 transition-colors"
          >
            Sign In
          </button>
        </p>
      )}
    </motion.div>
  );

  const renderPhoneInput = () => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex flex-col justify-center h-full space-y-8"
    >
      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center">
            <Phone size={24} className="text-emerald-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Enter Your Phone Number</h2>
            <p className="text-slate-600">We'll send you an OTP to verify your number</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <input
          type="tel"
          placeholder="Enter your phone number"
          value={userData.phone || ''}
          onChange={(e) => updateUserData('phone', e.target.value)}
          className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-lg"
        />

        <div className="flex space-x-4">
          <button
            onClick={() => setCurrentStep('welcome')}
            className="px-6 py-3 border border-slate-200 text-slate-600 rounded-xl hover:bg-slate-50 transition-colors flex items-center space-x-2"
          >
            <ArrowLeft size={18} />
            <span>Back</span>
          </button>
          <button
            onClick={handleSendPhoneOTP}
            disabled={!userData.phone || loading}
            className="flex-none w-44 bg-emerald-100 text-emerald-700 py-2 rounded-lg font-semibold hover:bg-emerald-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-emerald-700"></div>
                <span className="text-sm">Sending...</span>
              </>
            ) : (
              <>
                <span className="text-sm">Send OTP</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
      </div>
    </motion.div>
  );

  const renderOTPInput = (title: string, subtitle: string, onVerify: () => void, onResend: () => void) => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex flex-col justify-center h-full space-y-8"
    >
      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center">
            <CheckCircle2 size={24} className="text-emerald-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-800">{title}</h2>
            <p className="text-slate-600">{subtitle}</p>
          </div>
        </div>

        {devOtp && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
            <p className="text-amber-800 font-medium text-sm">Development Mode</p>
            <p className="text-amber-700 text-sm">Use OTP: <span className="font-mono font-bold">{devOtp}</span></p>
          </div>
        )}
      </div>

      <div className="space-y-6">
        <input
          type="text"
          placeholder="Enter 6-digit OTP"
          value={otp}
          onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
          className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-center text-2xl font-mono tracking-widest"
          maxLength={6}
        />

        <div className="flex space-x-4">
          <button
            onClick={() => setCurrentStep(currentStep === 'otp-phone' ? 'phone' : 'email')}
            className="px-6 py-3 border border-slate-200 text-slate-600 rounded-xl hover:bg-slate-50 transition-colors flex items-center space-x-2"
          >
            <ArrowLeft size={18} />
            <span>Back</span>
          </button>
          <div className="flex-1 space-y-3">
            <button
              onClick={onVerify}
              disabled={otp.length !== 6 || loading}
              className="w-44 bg-emerald-100 text-emerald-700 py-2 rounded-lg font-semibold hover:bg-emerald-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-emerald-700"></div>
                  <span className="text-sm">Verifying...</span>
                </>
              ) : (
                <>
                  <span className="text-sm">Verify OTP</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
            <button
              onClick={onResend}
              disabled={loading}
              className="w-full bg-slate-100 text-slate-700 py-2 rounded-xl font-medium hover:bg-slate-200 transition-colors text-sm"
            >
              Resend OTP
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
      </div>
    </motion.div>
  );

  const renderEmailInput = () => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex flex-col justify-center h-full space-y-8"
    >
      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center">
            <Mail size={24} className="text-emerald-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Enter Your Email</h2>
            <p className="text-slate-600">We'll send you an OTP to verify your email address</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <input
          type="email"
          placeholder="Enter your email address"
          value={userData.email || ''}
          onChange={(e) => updateUserData('email', e.target.value)}
          className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-lg"
        />

        <div className="flex space-x-4">
          <button
            onClick={() => setCurrentStep('otp-phone')}
            className="px-6 py-3 border border-slate-200 text-slate-600 rounded-xl hover:bg-slate-50 transition-colors flex items-center space-x-2"
          >
            <ArrowLeft size={18} />
            <span>Back</span>
          </button>
          <button
            onClick={handleSendEmailOTP}
            disabled={!userData.email || loading}
            className="flex-1 bg-emerald-600 text-white py-3 rounded-xl font-semibold hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Sending...</span>
              </>
            ) : (
              <>
                <span>Send OTP</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
      </div>
    </motion.div>
  );

  const renderDetailsForm = () => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex flex-col justify-center h-full space-y-8"
    >
      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center">
            <FileText size={24} className="text-emerald-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Personal Details</h2>
            <p className="text-slate-600">Please provide your information as per Aadhaar</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            placeholder="Full Name (as per Aadhaar)"
            value={userData.name || ''}
            onChange={(e) => updateUserData('name', e.target.value)}
            className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
          <input
            type="date"
            placeholder="Date of Birth"
            value={userData.dob || ''}
            onChange={(e) => updateUserData('dob', e.target.value)}
            className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </div>

        <input
          type="text"
          placeholder="Profession"
          value={userData.profession || ''}
          onChange={(e) => updateUserData('profession', e.target.value)}
          className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
        />

        <div className="relative">
          <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-bold">₹</span>
          <input
            type="number"
            placeholder="Monthly Salary"
            value={userData.salary || ''}
            onChange={(e) => updateUserData('salary', e.target.value)}
            className="w-full pl-8 pr-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </div>

        <textarea
          placeholder="Complete Address"
          value={userData.address || ''}
          onChange={(e) => updateUserData('address', e.target.value)}
          rows={4}
          className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent resize-none"
        />

        <div className="flex space-x-4">
          <button
            onClick={() => setCurrentStep('otp-email')}
            className="px-6 py-3 border border-slate-200 text-slate-600 rounded-xl hover:bg-slate-50 transition-colors flex items-center space-x-2"
          >
            <ArrowLeft size={18} />
            <span>Back</span>
          </button>
          <button
            onClick={() => setCurrentStep('password')}
            disabled={!userData.name || !userData.dob || !userData.profession || !userData.address || !userData.salary}
            className="flex-1 bg-emerald-600 text-white py-3 rounded-xl font-semibold hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
          >
            <span>Continue</span>
            <ArrowRight size={18} />
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
      </div>
    </motion.div>
  );

  const renderPasswordSetup = () => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex flex-col justify-center h-full space-y-8"
    >
      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-emerald-100 rounded-xl flex items-center justify-center">
            <Lock size={24} className="text-emerald-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Set Your Password</h2>
            <p className="text-slate-600">Create a secure password for your account</p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <input
          type="password"
          placeholder="Enter your password"
          value={userData.password || ''}
          onChange={(e) => updateUserData('password', e.target.value)}
          className="w-full px-4 py-4 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-transparent text-lg"
        />

        <div className="flex space-x-4">
          <button
            onClick={() => setCurrentStep('details')}
            className="px-6 py-3 border border-slate-200 text-slate-600 rounded-xl hover:bg-slate-50 transition-colors flex items-center space-x-2"
          >
            <ArrowLeft size={18} />
            <span>Back</span>
          </button>
          <button
            onClick={handleCompleteRegistration}
            disabled={!userData.password || userData.password.length < 6 || loading}
            className="flex-1 bg-emerald-600 text-white py-3 rounded-xl font-semibold hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Creating Account...</span>
              </>
            ) : (
              <>
                <span>Create Account</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}
      </div>
    </motion.div>
  );

  const renderComplete = () => (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center h-full text-center space-y-8"
    >
      <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center shadow-inner">
        <CheckCircle2 size={40} className="text-emerald-600" />
      </div>
      <div className="space-y-4">
        <h1 className="text-4xl font-bold text-slate-800">Account Created!</h1>
        <p className="text-lg text-slate-600">Welcome to NBFC, {userData.name}</p>
        <p className="text-slate-500">Redirecting you to your dashboard...</p>
      </div>
    </motion.div>
  );

  return (
    <div className="w-full h-screen flex overflow-hidden font-sans bg-slate-50 text-slate-900">
      {/* Left Sidebar - Progress */}
      <div className="w-[280px] border-r border-slate-200 bg-white flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <h1 className="text-xl font-bold text-slate-800">NBFC Onboarding</h1>
          <p className="text-sm text-slate-600 mt-1">Step {currentStepIndex + 1} of {steps.length}</p>
        </div>

        <div className="flex-1 p-6 space-y-3">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isCompleted = index < currentStepIndex;
            const isCurrent = index === currentStepIndex;

            return (
              <motion.div
                key={step.key}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`flex items-center space-x-3 p-3 rounded-xl transition-colors ${
                  isCurrent
                    ? 'bg-emerald-50 border border-emerald-200'
                    : isCompleted
                    ? 'bg-emerald-50/50'
                    : 'hover:bg-slate-50'
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  isCompleted
                    ? 'bg-emerald-600 text-white'
                    : isCurrent
                    ? 'bg-emerald-100 text-emerald-600'
                    : 'bg-slate-100 text-slate-400'
                }`}>
                  {isCompleted ? (
                    <CheckCircle2 size={16} />
                  ) : (
                    <Icon size={16} />
                  )}
                </div>
                <div className="flex-1">
                  <p className={`text-sm font-medium ${
                    isCurrent ? 'text-emerald-800' : isCompleted ? 'text-emerald-700' : 'text-slate-600'
                  }`}>
                    {step.label}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 p-12">
          <AnimatePresence mode="wait">
            {currentStep === 'welcome' && renderWelcome()}
            {currentStep === 'phone' && renderPhoneInput()}
            {currentStep === 'otp-phone' && renderOTPInput(
              'Verify Phone Number',
              'Enter the 6-digit code sent to your phone',
              handleVerifyPhoneOTP,
              handleSendPhoneOTP
            )}
            {currentStep === 'email' && renderEmailInput()}
            {currentStep === 'otp-email' && renderOTPInput(
              'Verify Email Address',
              'Enter the 6-digit code sent to your email',
              handleVerifyEmailOTP,
              handleSendEmailOTP
            )}
            {currentStep === 'details' && renderDetailsForm()}
            {currentStep === 'password' && renderPasswordSetup()}
            {currentStep === 'complete' && renderComplete()}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default Onboarding;