const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = {
  async startSession(): Promise<{ session_id: string; status: string; current_phase: string }> {
    const res = await fetch(`${BASE_URL}/session/start`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to start session');
    return res.json();
  },

  async getState(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/state`);
    if (!res.ok) throw new Error('Failed to get state');
    return res.json();
  },
  
  async getSession(sessionId: string) {
    return this.getState(sessionId);
  },

  async identifyCustomer(sessionId: string, phone: string, email?: string, password?: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/identify-customer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, email, password }),
    });
    return res.json();
  },

  async captureLoan(sessionId: string, loanType: string, amount: number, tenure: number) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/capture-loan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ loan_type: loanType, loan_amount: amount, tenure_months: tenure }),
    });
    return res.json();
  },

  async requestDocuments(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/request-documents`, { method: 'POST' });
    return res.json();
  },

  async extractOcr(sessionId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/session/${sessionId}/extract-ocr`, {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  async checkTampering(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/check-tampering`, { method: 'POST' });
    return res.json();
  },

  async verifyIncome(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/verify-income`, { method: 'POST' });
    return res.json();
  },

  async kycVerify(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/kyc-verify`, { method: 'POST' });
    return res.json();
  },

  async fraudCheck(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/fraud-check`, { method: 'POST' });
    return res.json();
  },

  async underwrite(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/underwrite`, { method: 'POST' });
    return res.json();
  },

  async analyzeRejection(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/persuasion/analyze`, { method: 'POST' });
    return res.json();
  },

  async suggestFix(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/persuasion/suggest`, { method: 'POST' });
    return res.json();
  },

  async respondToOffer(sessionId: string, action: string, amount?: number, tenure?: number) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/persuasion/respond`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, custom_amount: amount, custom_tenure: tenure }),
    });
    return res.json();
  },

  async recalculateTerms(sessionId: string, principal: number, tenure: number, rate?: number) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/recalculate-terms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ principal, tenure_months: tenure, rate }),
    });
    return res.json();
  },

  async sanction(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/sanction`, { method: 'POST' });
    return res.json();
  },

  async advisory(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/advisory`, { method: 'POST' });
    return res.json();
  },

  async endSession(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/end`, { method: 'POST' });
    return res.json();
  },
  
  async chat(sessionId: string, message: string, history: any[] = []) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    });
    return res.json();
  },
  
  async getSessionsByPhone(phone: string) {
    const res = await fetch(`${BASE_URL}/session/by-phone/${phone}`);
    if (!res.ok) throw new Error('Failed to fetch sessions');
    return res.json();
  },

  async getHistory(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/history`);
    if (!res.ok) throw new Error('Failed to fetch history');
    return res.json();
  }
};
