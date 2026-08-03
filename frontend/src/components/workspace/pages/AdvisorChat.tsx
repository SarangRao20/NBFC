import { useState } from 'react';
import { Bot, User, Send, Sparkles } from 'lucide-react';
import { useLoanStore } from '../../../store/useLoanStore';

export default function AdvisorChat() {
  const { user } = useLoanStore();
  const [messages, setMessages] = useState<any[]>([
    {
      id: '1',
      role: 'assistant',
      content: `Hello ${user?.name || 'Partner'}. I am your dedicated Autonomous Financial Advisory Agent. How can I optimize your capital structure or advise on interest rates today?`
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = { id: Date.now().toString(), role: 'user', content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    setTimeout(() => {
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Based on your prime CIBIL score (${user?.creditScore || 785}) and monthly cash flow, maintaining your current tenure of 36 months optimizes tax deductions while keeping your debt-service coverage ratio (DSCR) below 0.35.`
        }
      ]);
    }, 1200);
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-2xl h-[calc(100vh-160px)] flex flex-col overflow-hidden max-w-4xl mx-auto shadow-2xl">
      {/* Header */}
      <div className="p-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
         <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
               <Bot className="w-5 h-5" />
            </div>
            <div>
               <h3 className="font-display font-medium text-white text-sm">Financial Advisory Intelligence</h3>
               <p className="text-[10px] text-white/40 uppercase tracking-widest">LangGraph Advisory Agent Node</p>
            </div>
         </div>
         <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full flex items-center gap-1.5 font-medium">
            <Sparkles className="w-3.5 h-3.5" /> AI Online
         </span>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
         {messages.map((m) => (
            <div key={m.id} className={`flex gap-4 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
               <div className={`max-w-[80%] flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                     m.role === 'user' ? 'bg-white/10 border-white/20' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500'
                  }`}>
                     {m.role === 'user' ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4" />}
                  </div>
                  <div className={`p-4 rounded-2xl text-sm leading-relaxed ${
                     m.role === 'user' ? 'bg-white/10 text-white rounded-tr-sm' : 'bg-[#0A0A0A] border border-white/10 text-white/90 rounded-tl-sm'
                  }`}>
                     {m.content}
                  </div>
               </div>
            </div>
         ))}
         {isTyping && (
            <div className="flex justify-start text-xs text-white/40 font-mono animate-pulse">
               Advisor Agent analyzing cash flow models...
            </div>
         )}
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-4 border-t border-white/10 bg-[#0A0A0A] relative">
         <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask financial advisor about interest rates, tax benefits, or refinancing..."
            className="w-full bg-[#111] border border-white/10 rounded-xl pl-4 pr-12 py-3.5 text-sm text-white focus:outline-none focus:border-white/30 placeholder:text-white/30"
         />
         <button
            type="submit"
            disabled={!input.trim()}
            className="absolute right-6 top-5 text-white/70 hover:text-white disabled:opacity-30"
         >
            <Send className="w-4 h-4" />
         </button>
      </form>
    </div>
  );
}
