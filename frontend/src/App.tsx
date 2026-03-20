import { useState } from 'react';
import DashboardPane from './components/DashboardPane';
import ChatPane from './components/ChatPane';
import type { AppState, ChatMessage } from './types';

const INITIAL_APP_STATE: AppState = {
  requestedAmount: 500000,
  roi: 12.5,
  tenure: 48,
  emi: 13200,
  underwritingStatus: 'Pending Evaluation',
  activeAgent: null,
  needsDocument: false,
  documents: {
    pan: 'pending',
    bankStatement: 'pending',
  },
};

const INITIAL_CHAT_HISTORY: ChatMessage[] = [
  {
    id: 'msg-1',
    sender: 'agent',
    type: 'text',
    content: 'Hi Sumit! I see you are an existing customer. How can I help you regarding your loan today?',
    timestamp: new Date(),
  }
];

function App() {
  const [appState, setAppState] = useState<AppState>(INITIAL_APP_STATE);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(INITIAL_CHAT_HISTORY);

  const handleSendMessage = (text: string) => {
    // 1. Add user message
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      type: 'text',
      content: text,
      timestamp: new Date(),
    };
    
    setChatHistory((prev) => [...prev, userMsg]);

    // Mock workflows based on keywords
    if (text.toLowerCase().includes('negotiate')) {
      const thinkingMsgId = 'msg-thinking-' + Date.now();
      
      // Step 1: Master Agent routing
      setAppState(prev => ({ ...prev, activeAgent: '🧠 Master Agent is routing...' }));
      
      setTimeout(() => {
        // Step 2: Underwriting Agent
        setAppState(prev => ({ ...prev, activeAgent: '📊 Underwriting Agent is analyzing risk...' }));
      }, 1000);

      setTimeout(() => {
        // Step 3: Sales Agent
        setAppState(prev => ({ ...prev, activeAgent: '🤝 Sales Agent is drafting counter-offer...' }));
        
        setChatHistory((prev) => [
          ...prev,
          {
            id: thinkingMsgId,
            sender: 'agent',
            type: 'thinking',
            content: 'Sales Agent is preparing an interactive offer...',
            timestamp: new Date(),
          }
        ]);
      }, 2000);

      setTimeout(() => {
        setAppState(prev => ({ ...prev, activeAgent: null }));
        setChatHistory((prev) => prev.filter((m) => m.id !== thinkingMsgId));
        
        setChatHistory((prev) => [
          ...prev,
          {
            id: 'msg-response-' + Date.now(),
            sender: 'agent',
            type: 'emi_slider',
            content: "Here is your customized tenure and EMI plan. Adjust the slider to see options.",
            timestamp: new Date(),
          }
        ]);
      }, 4000);

    } else if (text.toLowerCase().includes('document')) {
      setAppState(prev => ({ ...prev, activeAgent: '🔍 Verification Agent is checking requirements...' }));
      
      setTimeout(() => {
        setAppState(prev => ({ ...prev, activeAgent: null, needsDocument: true }));
        setChatHistory((prev) => [
          ...prev,
          {
            id: 'msg-response-' + Date.now(),
            sender: 'agent',
            type: 'text',
            content: "Please upload your Bank Statement for verification.",
            timestamp: new Date(),
          }
        ]);
      }, 1500);

    } else if (text.toLowerCase().includes('too high')) {
      const thinkingMsgId = 'msg-thinking-' + Date.now();
      setAppState(prev => ({ ...prev, activeAgent: '📊 Underwriting Agent evaluating risk boundaries...' }));
      
      setChatHistory((prev) => [
        ...prev,
        {
          id: thinkingMsgId,
          sender: 'agent',
          type: 'thinking',
          content: 'Underwriting Agent evaluating risk boundaries...',
          timestamp: new Date(),
        }
      ]);

      setTimeout(() => {
        setAppState(prev => ({ ...prev, activeAgent: null }));
        setChatHistory((prev) => prev.filter((m) => m.id !== thinkingMsgId));

        setChatHistory((prev) => [
          ...prev,
          {
            id: 'msg-response-' + Date.now(),
            sender: 'agent',
            type: 'text',
            content: "I've negotiated a lower rate for you based on your excellent repayment history.",
            timestamp: new Date(),
          }
        ]);

        setAppState((prev) => ({
          ...prev,
          roi: 11.5,
          emi: 13000
        }));
      }, 2000);
    } else {
      setTimeout(() => {
        setChatHistory((prev) => [
          ...prev,
          {
            id: 'msg-response-' + Date.now(),
            sender: 'agent',
            type: 'text',
            content: "I'm checking that for you. Anything else?",
            timestamp: new Date(),
          }
        ]);
      }, 1000);
    }
  };

  return (
    <div className="w-full h-screen flex overflow-hidden font-sans bg-slate-50 text-slate-900 leading-relaxed">
      <DashboardPane appState={appState} />
      <ChatPane 
        appState={appState} 
        setAppState={setAppState} 
        chatHistory={chatHistory} 
        onSendMessage={handleSendMessage} 
      />
    </div>
  );
}

export default App;
