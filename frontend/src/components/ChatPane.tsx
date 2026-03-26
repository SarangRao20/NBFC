import { useState, useRef, useEffect } from 'react';
import type { ChatMessage, AppState } from '../types';
import { apiClient } from '../api/client';
import { Send, Paperclip, FileText, CheckCircle2, UploadCloud, BrainCircuit, ChevronDown, ChevronRight } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import AgentTypingIndicator from './AgentTypingIndicator';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Component for the collapsible agent steps block
const AgentStepsBlock = ({ content }: { content: string }) => {
  const [isOpen, setIsOpen] = useState(true);
  const data = JSON.parse(content);
  const steps: string[] = data.steps || [];

  if (!steps.length) return null;

  return (
    <div className="bg-emerald-50/40 border border-emerald-100/60 rounded-xl overflow-hidden shadow-sm mb-3 w-[460px] max-w-[85%] text-left">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-2.5 flex items-center justify-between bg-white hover:bg-slate-50 transition-colors border-b border-emerald-100/50"
      >
        <div className="flex items-center text-emerald-800 font-bold text-[13px] tracking-wide">
          <BrainCircuit size={15} className="mr-2 text-emerald-600" />
          System Actions ({steps.length})
        </div>
        {isOpen ? <ChevronDown size={15} className="text-emerald-400" /> : <ChevronRight size={15} className="text-emerald-400" />}
      </button>
      
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 space-y-3 bg-white/40">
              {steps.map((step, idx) => {
                // Remove emoji prefix if present, we'll use a neat checkmark
                const cleanStep = step.replace(/^[\u{1f300}-\u{1f5ff}\u{1f900}-\u{1f9ff}\u{1f600}-\u{1f64f}\u{1f680}-\u{1f6ff}\u{2600}-\u{26ff}\u{2700}-\u{27bf}\u{1f1e6}-\u{1f1ff}\u{1f191}-\u{1f251}\u{1f004}\u{1f0cf}\u{1f170}-\u{1f171}\u{1f17e}-\u{1f17f}\u{1f18e}\u{3030}\u{2b50}\u{2b55}\u{2934}-\u{2935}\u{2b05}-\u{2b07}\u{2b1b}-\u{2b1c}\u{3297}\u{3299}\u{303d}\u{00a9}\u{00ae}\u{2122}\u{23f3}\u{24c2}\u{23e9}-\u{23ef}\u{25b6}\u{23f8}-\u{23fa}]\s*/gu, '').trim();
                
                return (
                  <motion.div 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    key={idx} 
                    className="flex items-start"
                  >
                    <CheckCircle2 size={15} className="text-emerald-500 mt-0.5 mr-2.5 flex-shrink-0" />
                    <span className="text-[13px] text-slate-700 font-medium leading-relaxed">{cleanStep}</span>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

interface Props {
  appState: AppState;
  setAppState: React.Dispatch<React.SetStateAction<AppState>>;
  chatHistory: ChatMessage[];
  onSendMessage: (msg: string) => void;
  onFileUpload: (file: File) => void;
  onBatchFileUpload: (files: File[]) => void;
}

export default function ChatPane({ appState, setAppState, chatHistory, onSendMessage, onFileUpload, onBatchFileUpload }: Props) {
  const [input, setInput] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<Record<number, File>>({});
  const [isSigning, setIsSigning] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileUpload(file);
      // Reset input so the same file can be picked again
      e.target.value = '';
    }
  };

  return (
    <div className="flex-1 bg-white flex flex-col relative h-full font-sans">
      {/* Header */}
      <div className="h-16 border-b border-slate-100 flex items-center px-8 bg-white/80 backdrop-blur-md sticky top-0 z-10 justify-between">
        <h1 className="text-[17px] font-bold text-slate-800 flex items-center">
          Loan Assistant <span className="text-slate-400 text-sm font-semibold ml-2.5 border-l border-slate-200 pl-2.5">Customer Support</span>
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
                      : 'bg-white text-slate-800 rounded-[20px] rounded-bl-[4px] border border-slate-200/60'
                  }`}
                >
                  {msg.sender === 'user' ? (
                    msg.content
                  ) : (
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({node, ...props}) => <p className="mb-3 last:mb-0 leading-relaxed" {...props} />,
                        ul: ({node, ...props}) => <ul className="list-disc ml-5 mb-3 space-y-1" {...props} />,
                        ol: ({node, ...props}) => <ol className="list-decimal ml-5 mb-3 space-y-1" {...props} />,
                        li: ({node, ...props}) => <li className="leading-normal mb-1" {...props} />,
                        strong: ({node, ...props}) => <strong className="font-extrabold text-slate-900" {...props} />,
                        h1: ({node, ...props}) => <h1 className="text-xl font-black mb-3 text-slate-900" {...props} />,
                        h2: ({node, ...props}) => <h2 className="text-lg font-black mb-2 text-slate-900" {...props} />,
                        h3: ({node, ...props}) => <h3 className="text-md font-black mb-1 text-slate-900" {...props} />,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>


                  )}
                </div>
              )}

              {msg.type === 'thinking' && (
                <AgentTypingIndicator />
              )}

              {msg.options && msg.options.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3 ml-1">
                  {msg.options.map((option) => (
                    <motion.button
                      key={option}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => onSendMessage(option)}
                      className="px-6 py-2 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[14px] font-bold hover:bg-emerald-100 hover:border-emerald-300 transition-all shadow-sm"
                    >
                      {option}
                    </motion.button>
                  ))}
                </div>
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
                    <button 
                      onClick={async () => {
                        if (!appState.sessionId) return;
                        try {
                          const blob = await apiClient.downloadLetter(appState.sessionId);
                          const url = window.URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `Sanction_Letter_${appState.sessionId.slice(0, 8)}.pdf`;
                          document.body.appendChild(a);
                          a.click();
                          window.URL.revokeObjectURL(url);
                        } catch (err) {
                          console.error('Download failed:', err);
                        }
                      }}
                      className="flex-1 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-bold py-2.5 rounded-xl transition-all active:scale-95 shadow-sm"
                    >
                      Download PDF
                    </button>
                    <button 
                      disabled={isSigning}
                      onClick={async () => {
                        if (!appState.sessionId) return;
                        setIsSigning(true);
                        try {
                          await apiClient.esignAccept(appState.sessionId);
                          onSendMessage("I accept the sanction letter and e-sign it.");
                        } catch (err) {
                          console.error('E-sign failed:', err);
                        } finally {
                          setIsSigning(false);
                        }
                      }}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 shadow-sm shadow-emerald-600/20 text-white text-sm font-bold py-2.5 rounded-xl transition-all flex justify-center items-center active:scale-95">
                      {isSigning ? (
                        <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
                          <BrainCircuit size={16} className="mr-1.5" />
                        </motion.div>
                      ) : (
                        <CheckCircle2 size={16} className="mr-1.5" />
                      )}
                      {isSigning ? 'Signing...' : 'Accept & E-Sign'}
                    </button>
              </div>
            </div>
          )}

          {msg.type === 'rejection_letter' && (
            <div className="bg-white/80 backdrop-blur-md border border-slate-200/60 shadow-xl shadow-slate-900/5 rounded-2xl rounded-bl-[4px] p-6 max-w-[85%] w-[460px]">
              <div className="flex items-center mb-4 pb-4 border-b border-slate-100">
                <div className="w-10 h-10 bg-amber-50 rounded-xl flex items-center justify-center text-amber-600 mr-3">
                  <FileText size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-[16px] text-slate-800">Rejection Letter</h3>
                  <p className="text-xs font-semibold text-slate-400">PDF Document • System-generated</p>
                </div>
              </div>
              <div className="bg-slate-50 p-4 rounded-xl mb-5 border border-slate-100/50">
                <div className="text-sm text-slate-600 font-medium mb-1">Requested Amount</div>
                <div className="text-2xl font-black text-amber-600 mb-2">₹{new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(appState.requestedAmount)}</div>
                <p className="text-slate-500 text-[13px] leading-relaxed">
                  {msg.content}
                </p>
              </div>
              <div className="flex space-x-3">
                <button 
                  onClick={async () => {
                    if (!appState.sessionId) return;
                    try {
                      const blob = await apiClient.downloadLetter(appState.sessionId);
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `Rejection_Letter_${appState.sessionId?.slice(0, 8)}.pdf`;
                      document.body.appendChild(a);
                      a.click();
                      window.URL.revokeObjectURL(url);
                    } catch (err) {
                      console.error('Download failed:', err);
                    }
                  }}
                  className="flex-1 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-bold py-2.5 rounded-xl transition-all active:scale-95 shadow-sm"
                >
                  Download PDF
                </button>
                <button 
                  onClick={() => {
                    onSendMessage('Negotiate');
                  }}
                  className="flex-1 bg-amber-600 hover:bg-amber-700 shadow-sm text-white text-sm font-bold py-2.5 rounded-xl transition-all flex justify-center items-center active:scale-95"
                >
                  Try Negotiation
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
                    const r = (appState.roi || 0) / 12 / 100;
                    const p = appState.requestedAmount || 0;
                    const calcEmi = r === 0 ? Math.round(p / t) : Math.round(p * r * Math.pow(1 + r, t) / (Math.pow(1 + r, t) - 1));
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
          {msg.type === 'agent_steps' && (
            <AgentStepsBlock content={msg.content} />
          )}
        </motion.div>
      ))}
    </AnimatePresence>
    {/* 🟢 HYBRID DISBURSEMENT UI PAUSE INSERTION */}
    <AnimatePresence>
      {appState.disbursement_step === "ui_paused" && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-emerald-50 border-2 border-emerald-200 shadow-xl shadow-emerald-900/5 rounded-2xl p-6 max-w-[85%] w-[460px] mx-auto my-6 text-left"
        >
          <div className="flex items-center mb-4 pb-3 border-b border-emerald-100">
            <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center text-white mr-3">
              <CheckCircle2 size={22} />
            </div>
            <div>
              <h3 className="font-black text-[17px] text-emerald-900 uppercase tracking-tight">RBI Compliance Checklist</h3>
              <p className="text-[11px] font-bold text-emerald-600 uppercase tracking-widest">Final Authorization</p>
            </div>
          </div>

          <div className="bg-white/60 p-4 rounded-xl mb-6 border border-emerald-100">
            <div className="text-xs font-bold text-slate-500 uppercase mb-1">Net Disbursement to Bank</div>
            <div className="text-3xl font-black text-emerald-600">
              ₹{new Intl.NumberFormat('en-IN').format(appState.net_disbursement_amount || 0)}
            </div>
            <p className="text-[12px] text-slate-500 mt-2 leading-relaxed italic">
              *Fees, GST, and Broken Period Interest have been deducted as per the KFS.
            </p>
          </div>

          <div className="space-y-4 mb-6">
            <label className="flex items-start gap-3 cursor-pointer group">
              <input 
                type="checkbox" 
                id="kfs_check"
                className="mt-1 w-5 h-5 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500 transition-all cursor-pointer"
              />
              <span className="text-[14px] font-bold text-slate-700 group-hover:text-emerald-800 transition-colors">
                I accept the Key Fact Statement (KFS)
              </span>
            </label>

            <label className="flex items-start gap-3 cursor-pointer group">
              <input 
                type="checkbox" 
                id="enach_check"
                className="mt-1 w-5 h-5 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500 transition-all cursor-pointer"
              />
              <span className="text-[14px] font-bold text-slate-700 group-hover:text-emerald-800 transition-colors">
                Authorize e-NACH Autopay via NetBanking
              </span>
            </label>
          </div>

          <button 
            onClick={() => {
              const kfs = (document.getElementById('kfs_check') as HTMLInputElement).checked;
              const enach = (document.getElementById('enach_check') as HTMLInputElement).checked;
              
              if(kfs && enach) {
                // Ping backend to resume the LangGraph Subgraph
                onSendMessage("I have signed the KFS and authorized e-NACH.");
              } else {
                alert("Please complete all compliance checkboxes to authorize disbursement.");
              }
            }}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-black py-4 rounded-xl shadow-lg shadow-emerald-600/20 transition-all active:scale-[0.98] flex justify-center items-center gap-2 group"
          >
            Execute Direct Bank Transfer
            <Send size={18} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
    {/* 🟢 END OF INSERTION */}
    <div ref={messagesEndRef} />
  </div>

  {/* Input Area */}
  <div className="p-4 px-8 border-t border-slate-100 bg-white">
    {/* Document Upload Cards - shown above input when needed */}
    <AnimatePresence>
      {appState.needsDocument && (
        <motion.div
          key="dropzone"
          initial={{ opacity: 0, height: 0, scale: 0.95 }}
          animate={{ opacity: 1, height: 'auto', scale: 1 }}
          exit={{ opacity: 0, height: 0, scale: 0.95 }}
        >
          <div className={`w-full mb-4 grid gap-4 ${appState.requiredDocuments?.length && appState.requiredDocuments.length > 2 ? 'grid-cols-2' : 'grid-cols-1 md:grid-cols-2'}`}>
            {appState.requiredDocuments?.map((docType, idx) => {
              const file = selectedFiles[idx];
              return (
                <motion.div 
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`border-dashed border-2 rounded-2xl flex flex-col items-center justify-center p-6 transition-all cursor-pointer group relative overflow-hidden ${
                    file ? 'border-emerald-500 bg-emerald-50/30' : 'border-slate-300 bg-slate-50/50 hover:bg-white hover:border-emerald-400 hover:shadow-md'
                  }`}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                      setSelectedFiles(prev => ({ ...prev, [idx]: e.dataTransfer.files[0] }));
                    }
                  }}
                  onClick={() => {
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = 'application/pdf,image/jpeg,image/png';
                    input.onchange = (e: any) => {
                      const file = e.target.files[0];
                      if (file) setSelectedFiles(prev => ({ ...prev, [idx]: file }));
                    };
                    input.click();
                  }}
                >
                  {file && (
                    <div className="absolute top-0 right-0 p-2">
                      <div className="bg-emerald-500 text-white p-1 rounded-full shadow-sm">
                        <CheckCircle2 size={12} />
                      </div>
                    </div>
                  )}
                  <div className={`w-10 h-10 rounded-full bg-white shadow-sm flex items-center justify-center transition-all mb-3 ${
                    file ? 'text-emerald-500 scale-110' : 'text-slate-400 group-hover:text-emerald-500 group-hover:scale-110'
                  }`}>
                    <UploadCloud size={20} />
                  </div>
                  <p className={`text-[13px] font-bold text-center mb-0.5 ${file ? 'text-emerald-700' : 'text-slate-700'}`}>
                    {file ? file.name : docType}
                  </p>
                  <p className="text-[11px] font-semibold text-slate-400 text-center uppercase tracking-wider">
                    {file ? 'Change file' : 'Tap to select'}
                  </p>
                </motion.div>
              );
            })}
          </div>

          {/* Submit Batch Button */}
          {Object.keys(selectedFiles).length > 0 && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-center mb-6"
            >
              <button
                onClick={() => {
                  const files = Object.values(selectedFiles);
                  onBatchFileUpload(files);
                  setSelectedFiles({});
                }}
                className={`px-8 py-3 rounded-2xl font-black text-[14px] shadow-lg transition-all active:scale-95 flex items-center ${
                  Object.keys(selectedFiles).length >= (appState.requiredDocuments?.length || 0)
                    ? 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-emerald-200'
                    : 'bg-slate-200 text-slate-500 cursor-not-allowed'
                }`}
                disabled={Object.keys(selectedFiles).length < (appState.requiredDocuments?.length || 0)}
              >
                Submit {Object.keys(selectedFiles).length} Document(s) for Verification
                <CheckCircle2 size={18} className="ml-2.5" />
              </button>
            </motion.div>
          )}
        </motion.div>
      )}
    </AnimatePresence>

    {/* Chat Input - always visible */}
    <form 
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
        className="w-full bg-transparent p-4 pb-12 outline-none resize-none min-h-[80px] text-[15px] font-medium placeholder:text-slate-400"
      />
      <div className="absolute bottom-3 right-3 left-3 flex justify-between items-center">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png"
        />
        <button 
          type="button" 
          onClick={handleFileClick}
          className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-200/70 rounded-xl transition-colors"
        >
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
    </form>
        <div className="text-center mt-3 text-[11px] font-bold text-slate-400 uppercase tracking-widest flex items-center justify-center space-x-1.5">
          <span>Secure NBFC Assistant</span>
        </div>
      </div>
    </div>
  );
}
