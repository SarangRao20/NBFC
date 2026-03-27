import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Debug React initialization
declare global {
  interface Window {
    React: any;
    ReactDOM: any;
  }
}

console.log('React available:', !!(typeof window === 'undefined') && (window as Window).React);
console.log('ReactDOM available:', !!(typeof window === 'undefined') && (window as Window).ReactDOM);

const rootElement = document.getElementById('root');
if (!rootElement) {
  console.error('Root element not found!');
}

createRoot(rootElement!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
