type WSCallback = (data: any) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private callbacks: Set<WSCallback> = new Set();
  private reconnectTimer: any = null;

  connect(sessionId: string) {
    if (this.socket || !sessionId) return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_API_URL 
      ? import.meta.env.VITE_API_URL.replace(/^https?:\/\//, '') 
      : 'localhost:8000';
    
    const wsUrl = `${protocol}//${host}/ws/${sessionId}`;
    console.log(`🔌 [WS] Connecting to ${wsUrl}...`);

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('✅ [WS] Connected');
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.callbacks.forEach(cb => cb(data));
      } catch (e) {
        console.warn('⚠️ [WS] Failed to parse message:', event.data);
      }
    };

    this.socket.onclose = () => {
      console.log('🔌 [WS] Disconnected');
      this.socket = null;
      // Simple reconnect logic
      this.reconnectTimer = setTimeout(() => this.connect(sessionId), 3000);
    };

    this.socket.onerror = (err) => {
      console.error('❌ [WS] Error:', err);
    };
  }

  subscribe(callback: WSCallback) {
    this.callbacks.add(callback);
    return () => this.callbacks.delete(callback);
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
  }
}

export const wsClient = new WebSocketClient();
