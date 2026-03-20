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

    // 2. Mock Agent Logic based on keyword
    if (text.toLowerCase().includes('too high')) {
      // Show thinking state
      const thinkingMsgId = 'msg-thinking-' + Date.now();
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

      // Simulate a 2-second delay
      setTimeout(() => {
        // Remove thinking message
        setChatHistory((prev) => prev.filter((m) => m.id !== thinkingMsgId));

        // Add agent response
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

        // Automatically update the ROI in the dashboard app state
        setAppState((prev) => ({
          ...prev,
          roi: 11.5,
          emi: 13000 // mock updated EMI
        }));

      }, 2000);
    } else {
      // Default echo / generic response
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
      <ChatPane chatHistory={chatHistory} onSendMessage={handleSendMessage} />
    </div>
  );
}

export default App;
