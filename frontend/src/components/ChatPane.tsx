import { useState, useRef, useEffect } from 'react';
import type { ChatMessage, AppState } from '../types';
import { Send, Paperclip, FileText, CheckCircle2, UploadCloud, BrainCircuit } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AgentTypingIndicator from './AgentTypingIndicator';

interface Props {
  appState: AppState;
  setAppState: React.Dispatch<React.SetStateAction<AppState>>;
  chatHistory: ChatMessage[];
  onSendMessage: (msg: string) => void;
  onFileUpload: (file: File) => void;
}

export default function ChatPane({ appState, setAppState, chatHistory, onSendMessage, onFileUpload }: Props) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSendMessage(input.trim());
    setInput('');
  };

  return (
    <div className="flex-1 bg-white flex flex-col relative h-full font-sans">
      {/* Header */}
      <div className="h-16 border-b border-slate-100 flex items-center px-8 bg-white/80 backdrop-blur-md sticky top-0 z-10 justify-between">
        <h1 className="text-[17px] font-bold text-slate-800 flex items-center">
          Sales Agent <span className="text-slate-400 text-sm font-semibold ml-2.5 border-l border-slate-200 pl-2.5">Dynamic Command Center</span>
        </h1>
        
        {/* The 'Brain' Visualizer */}
        <AnimatePresence>
          {appState.activeAgent && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }} 
              animate={{ opacity: 1, y: 0 }} 
              exit={{ opacity: 0, y: -10 }}
              className="flex items-center space-x-2 bg-emerald-50 px-4 py-1.5 rounded-full border border-emerald-100 shadow-sm"
            >
              <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 4, ease: "linear" }}>
                <BrainCircuit size={16} className="text-emerald-600" />
              </motion.div>
              <motion.span 
                initial={{ opacity: 0.5 }} 
                animate={{ opacity: 1 }} 
                transition={{ repeat: Infinity, duration: 1, ease: "easeInOut", repeatType: "reverse" }}
                className="text-xs font-bold text-emerald-700 font-mono tracking-tight"
              >
                {appState.activeAgent}
              </motion.span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Chat Feed */}
      <div className="flex-1 overflow-y-auto p-8 space-y-7 flex flex-col pt-10">
        <AnimatePresence initial={false}>
          {chatHistory.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 15, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.25, type: 'spring', damping: 25, stiffness: 300 }}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              {msg.type === 'text' && (
                <div
                  className={`p-4 max-w-[75%] text-[15px] leading-relaxed shadow-sm font-medium ${
                    msg.sender === 'user'
                      ? 'bg-slate-900 text-white rounded-[20px] rounded-br-[4px]'
                      : 'bg-slate-100 text-slate-800 rounded-[20px] rounded-bl-[4px] border border-slate-200/60'
                  }`}
                >
                  {msg.content}
                </div>
              )}

              {msg.type === 'thinking' && (
                <AgentTypingIndicator />
              )}

              {msg.type === 'sanction_letter' && (
                <div className="bg-white/80 backdrop-blur-md border border-slate-200/60 shadow-xl shadow-slate-900/5 rounded-2xl rounded-bl-[4px] p-6 max-w-[85%] w-[460px]">
                  <div className="flex items-center mb-4 pb-4 border-b border-slate-100">
                    <div className="w-10 h-10 bg-red-50 rounded-xl flex items-center justify-center text-red-500 mr-3">
                      <FileText size={20} />
                    </div>
                    <div>
                      <h3 className="font-bold text-[16px] text-slate-800">Sanction Letter</h3>
                      <p className="text-xs font-semibold text-slate-400">PDF Document • 1.2 MB</p>
                    </div>
                  </div>
                  <div className="bg-slate-50 p-4 rounded-xl mb-5 border border-slate-100/50">
                    <div className="text-sm text-slate-600 font-medium mb-1">Approved Amount</div>
                    <div className="text-2xl font-black text-emerald-600 mb-2">₹{new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(appState.requestedAmount)}</div>
                    <p className="text-slate-500 text-[13px] leading-relaxed">
                      {msg.content}
                    </p>
                  </div>
                  <div className="flex space-x-3">
                    <button className="flex-1 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-bold py-2.5 rounded-xl transition-all active:scale-95 shadow-sm">
                      Download PDF
                    </button>
                    <button className="flex-1 bg-emerald-600 hover:bg-emerald-700 shadow-sm shadow-emerald-600/20 text-white text-sm font-bold py-2.5 rounded-xl transition-all flex justify-center items-center active:scale-95">
                      <CheckCircle2 size={16} className="mr-1.5" /> Accept & E-Sign
                    </button>
                  </div>
                </div>
              )}

              {msg.type === 'emi_slider' && (
                <div className="bg-white border text-left border-emerald-100 shadow-xl shadow-emerald-900/5 rounded-2xl rounded-bl-[4px] p-5 max-w-[85%] w-[460px]">
                  <p className="text-slate-800 text-[15px] font-medium leading-relaxed mb-6">
                    {msg.content}
                  </p>
                  <div className="bg-slate-50 p-5 border border-slate-100 rounded-xl mb-2">
                    <div className="flex justify-between items-end mb-4">
                      <div>
                        <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Tenure</div>
                        <div className="text-2xl font-black text-slate-800">{appState.tenure} <span className="text-sm font-semibold text-slate-400">Months</span></div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Monthly EMI</div>
                        <div className="text-2xl font-black text-emerald-600">₹{new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(appState.emi)}</div>
                      </div>
                    </div>
                    
                    <input 
                      type="range" 
                      min="12" 
                      max="60" 
                      step="1"
                      value={appState.tenure}
                      onChange={(e) => {
                        const t = parseInt(e.target.value);
                        const r = appState.roi / 12 / 100;
                        const p = appState.requestedAmount;
                        const calcEmi = Math.round(p * r * Math.pow(1 + r, t) / (Math.pow(1 + r, t) - 1));
                        setAppState(prev => ({ ...prev, tenure: t, emi: calcEmi }));
                      }}
                      className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-500 hover:accent-emerald-600 transition-all"
                    />
                    <div className="flex justify-between text-xs font-semibold text-slate-400 mt-2">
                      <span>12m</span>
                      <span>60m</span>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 px-8 border-t border-slate-100 bg-white">
        <AnimatePresence mode="wait">
          {appState.needsDocument ? (
            <motion.div
              key="dropzone"
              initial={{ opacity: 0, height: 0, scale: 0.95 }}
              animate={{ opacity: 1, height: 'auto', scale: 1 }}
              exit={{ opacity: 0, height: 0, scale: 0.95 }}
              className="w-full mb-4"
            >
              <div 
                className="w-full border-dashed border-2 border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-emerald-400 rounded-2xl flex flex-col items-center justify-center p-8 transition-all cursor-pointer group"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    onFileUpload(e.dataTransfer.files[0]);
                  }
                }}
                onClick={() => {
                  const input = document.createElement('input');
                  input.type = 'file';
                  input.accept = 'application/pdf,image/jpeg,image/png';
                  input.onchange = (e: any) => {
                    const file = e.target.files[0];
                    if (file) onFileUpload(file);
                  };
                  input.click();
                }}
              >
                <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center text-slate-400 group-hover:text-emerald-500 group-hover:scale-110 transition-all mb-3">
                  <UploadCloud size={24} />
                </div>
                <p className="text-sm font-bold text-slate-600 mb-1">Drop your Bank Statement here</p>
                <p className="text-xs font-semibold text-slate-400">PDF, JPG or PNG up to 10MB</p>
              </div>
            </motion.div>
          ) : (
            <motion.form 
              key="chat-input"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onSubmit={handleSubmit} 
              className="flex flex-col relative w-full rounded-2xl shadow-[0_2px_15px_-3px_rgba(0,0,0,0.05)] border border-slate-200 bg-slate-50 focus-within:ring-2 focus-within:ring-emerald-500/20 focus-within:border-emerald-500/50 transition-all overflow-hidden group"
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                placeholder="Talk or type to the Agent..."
                className="w-full bg-transparent p-5 pb-14 outline-none resize-none min-h-[110px] text-[15px] font-medium placeholder:text-slate-400"
              />
              <div className="absolute bottom-3 right-3 left-3 flex justify-between items-center">
                <button type="button" className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200/70 rounded-xl transition-colors">
                  <Paperclip size={20} />
                </button>
                <button 
                  type="submit" 
                  disabled={!input.trim()}
                  className="px-5 py-2.5 bg-slate-900 text-white font-semibold rounded-xl hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-all flex items-center shadow-md shadow-slate-900/20 active:scale-95 group-focus-within:bg-slate-900"
                >
                  Send <Send size={16} className="ml-2" />
                </button>
              </div>
            </motion.form>
          )}
        </AnimatePresence>
        <div className="text-center mt-3 text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center justify-center space-x-1.5">
          <span>Powered by LangGraph</span>
          <span className="w-1 h-1 rounded-full bg-slate-300"></span>
          <span>Agentic Workflow</span>
        </div>
      </div>
    </div>
  );
}
