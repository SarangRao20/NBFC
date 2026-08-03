import { useEffect, useRef, useState } from 'react';
import { useLoanStore } from '../../store/useLoanStore';
import { ShieldCheck, Bot, User, Send, Loader2 } from 'lucide-react';
import ProfileWidget from './widgets/ProfileWidget';
import OnboardingWidget from './widgets/OnboardingWidget';
import KycWidget from './widgets/KycWidget';
import OffersWidget from './widgets/OffersWidget';
import ActiveContractWidget from './widgets/ActiveContractWidget';
import RejectionWidget from './widgets/RejectionWidget';

export default function Workspace() {
  const { currentState, chatHistory, addChatMessage, user } = useLoanStore();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isTyping]);

  // State Machine Driven Chat Injection
  useEffect(() => {
    // Prevent duplicate injections
    const lastMsg = chatHistory[chatHistory.length - 1];
    
    if (currentState === 'PROFILE_COMPLETION' && lastMsg?.component !== 'PROFILE_FORM') {
      setIsTyping(true);
      setTimeout(() => {
        setIsTyping(false);
        addChatMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: `Welcome to FinServe, ${user?.name || 'User'}. To initialize your cryptographic profile, please verify the following details:`,
          timestamp: Date.now(),
          component: 'PROFILE_FORM'
        });
      }, 1000);
    } 
    else if (currentState === 'ONBOARDING' && lastMsg?.component !== 'ONBOARDING_FORM' && !chatHistory.find(m => m.component === 'ONBOARDING_FORM')) {
      setIsTyping(true);
      setTimeout(() => {
        setIsTyping(false);
        addChatMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: `Identity verified. Your credit profile is active (Score: ${useLoanStore.getState().user?.creditScore}). Please set your capital requirements below:`,
          timestamp: Date.now(),
          component: 'ONBOARDING_FORM'
        });
      }, 1000);
    }
    else if (currentState === 'DOCUMENT_COLLECTION' && lastMsg?.component !== 'KYC_DROPZONE' && !chatHistory.find(m => m.component === 'KYC_DROPZONE')) {
      setIsTyping(true);
      setTimeout(() => {
        setIsTyping(false);
        addChatMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Capital parameters accepted. For sub-second underwriting, please upload your Aadhaar and PAN documents below.',
          timestamp: Date.now(),
          component: 'KYC_DROPZONE'
        });
      }, 1000);
    }
    else if (currentState === 'DECISION_READY' && lastMsg?.component !== 'LENDER_CAROUSEL' && !chatHistory.find(m => m.component === 'LENDER_CAROUSEL')) {
      setIsTyping(true);
      setTimeout(() => {
        setIsTyping(false);
        addChatMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: 'StateGraph underwriting complete. Analyzing 40,000+ data points... Here are your verified institutional offers:',
          timestamp: Date.now(),
          component: 'LENDER_CAROUSEL'
        });
      }, 2000);
    }
    else if (currentState === 'ACTIVE_LOAN' && lastMsg?.component !== 'ACTIVE_CONTRACT' && !chatHistory.find(m => m.component === 'ACTIVE_CONTRACT')) {
      setIsTyping(true);
      setTimeout(() => {
        setIsTyping(false);
        addChatMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Smart contract executed. Funds are being disbursed to your account. Your active facility ledger is available below:',
          timestamp: Date.now(),
          component: 'ACTIVE_CONTRACT'
        });
      }, 1000);
    }
  }, [currentState, addChatMessage, user]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    addChatMessage({
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: Date.now()
    });
    
    setInput('');
    setIsTyping(true);
    
    setTimeout(() => {
       setIsTyping(false);
       addChatMessage({
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Understood. Modifying parameters via StateGraph engine...',
          timestamp: Date.now()
       });
    }, 1500);
  };

  const renderComponent = (componentName?: string) => {
    switch(componentName) {
      case 'PROFILE_FORM': return <ProfileWidget />;
      case 'ONBOARDING_FORM': return <OnboardingWidget />;
      case 'KYC_DROPZONE': return <KycWidget />;
      case 'LENDER_CAROUSEL': return <OffersWidget />;
      case 'ACTIVE_CONTRACT': return <ActiveContractWidget />;
      case 'SHAP_EXPLANATION': return <RejectionWidget />;
      default: return null;
    }
  };

  return (
    <div className="fixed inset-0 flex w-full bg-[#0A0A0A] text-white selection:bg-white/20 font-sans overflow-hidden">
      {/* Background Effects matching Landing Page */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-900/10 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-emerald-900/5 blur-[120px]" />
      </div>

      <main className="flex-1 flex flex-col h-full relative z-10 max-w-4xl mx-auto w-full border-x border-white/[0.05] bg-[#0A0A0A]/50 backdrop-blur-xl shadow-2xl">
        {/* Header */}
        <header className="h-20 border-b border-white/[0.05] bg-[#0A0A0A]/80 backdrop-blur-xl flex items-center justify-between px-8 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
               <span className="font-display font-medium text-lg tracking-tight block leading-tight">FinServe<span className="text-white/40">.AI</span></span>
               <span className="text-xs text-white/40 font-medium tracking-widest uppercase">System Intelligence</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-xs text-emerald-500/80 uppercase tracking-widest font-semibold">Online</span>
          </div>
        </header>
        
        {/* Chat Feed */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 scroll-smooth">
          {chatHistory.length === 0 && !isTyping && (
             <div className="text-center mt-20 opacity-30">
                <Bot className="w-12 h-12 mx-auto mb-4 text-white" />
                <p className="text-sm font-medium tracking-widest uppercase">System Initializing</p>
             </div>
          )}
          
          {chatHistory.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
              <div className={`max-w-[85%] flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                 <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                    msg.role === 'user' ? 'bg-white/10 border-white/20' : 'bg-emerald-500/10 border-emerald-500/30'
                 }`}>
                    {msg.role === 'user' ? <User className="w-4 h-4 text-white/70" /> : <Bot className="w-4 h-4 text-emerald-500" />}
                 </div>
                 
                 <div className="flex flex-col gap-3 min-w-0">
                    {msg.content && (
                       <div className={`px-5 py-3.5 text-[15px] leading-relaxed rounded-2xl shadow-sm ${
                         msg.role === 'user' 
                           ? 'bg-white/10 text-white rounded-tr-sm border border-white/5' 
                           : 'bg-[#111] text-white/90 border border-white/10 rounded-tl-sm'
                       }`}>
                         {msg.content}
                       </div>
                    )}
                    
                    {msg.component && (
                       <div className="mt-2 w-full">
                          {renderComponent(msg.component)}
                       </div>
                    )}
                 </div>
              </div>
            </div>
          ))}

          {isTyping && (
             <div className="flex justify-start animate-fade-in">
               <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border bg-emerald-500/10 border-emerald-500/30">
                     <Bot className="w-4 h-4 text-emerald-500" />
                  </div>
                  <div className="bg-[#111] border border-white/10 rounded-2xl rounded-tl-sm px-5 py-4 text-sm shadow-sm flex items-center gap-3">
                     <Loader2 className="w-4 h-4 animate-spin text-white/50" />
                     <span className="text-white/50 tracking-wide font-medium text-xs uppercase">Processing</span>
                  </div>
               </div>
             </div>
          )}
          <div ref={bottomRef} className="h-4" />
        </div>

        {/* Input Area */}
        <div className="p-6 bg-[#0A0A0A]/90 border-t border-white/[0.05] backdrop-blur-md">
          <form onSubmit={handleSend} className="relative max-w-3xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask System Intelligence to adjust parameters..."
              className="w-full bg-[#111] border border-white/10 rounded-xl pl-5 pr-14 py-4 text-[15px] focus:outline-none focus:ring-1 focus:ring-white/30 shadow-inner text-white placeholder:text-white/30 transition-all"
            />
            <button 
              type="submit"
              disabled={!input.trim()}
              className="absolute right-2 top-2 bottom-2 w-10 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white disabled:opacity-30 transition-all"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
