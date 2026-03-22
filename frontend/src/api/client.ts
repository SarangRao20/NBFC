const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const checkResponse = async (res: Response, url: string) => {
  if (!res.ok) {
    let errorDetail = '';
    try {
      const body = await res.json();
      errorDetail = JSON.stringify(body);
    } catch (e) {
      errorDetail = await res.text();
    }
    const errorMsg = `API Error [${res.status}] at ${url}: ${errorDetail}`;
    console.error(errorMsg);
    throw new Error(errorMsg);
  }
  return res.json();
};

export const apiClient = {
  async startSession(): Promise<{ session_id: string; status: string; current_phase: string }> {
    const res = await fetch(`${BASE_URL}/session/start`, { method: 'POST' });
    return checkResponse(res, '/session/start');
  },

  async getState(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/state`);
    return checkResponse(res, `/session/${sessionId}/state`);
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
    return checkResponse(res, `/session/${sessionId}/identify-customer`);
  },

  async captureLoan(sessionId: string, loanType: string, amount: number, tenure: number) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/capture-loan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ loan_type: loanType, loan_amount: amount, tenure_months: tenure }),
    });
    return checkResponse(res, `/session/${sessionId}/capture-loan`);
  },

  async requestDocuments(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/request-documents`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/request-documents`);
  },

  async extractOcr(sessionId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/session/${sessionId}/extract-ocr`, {
      method: 'POST',
      body: formData,
    });
    return checkResponse(res, `/session/${sessionId}/extract-ocr`);
  },

  async checkTampering(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/check-tampering`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/check-tampering`);
  },

  async verifyIncome(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/verify-income`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/verify-income`);
  },

  async kycVerify(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/kyc-verify`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/kyc-verify`);
  },

  async fraudCheck(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/fraud-check`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/fraud-check`);
  },

  async underwrite(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/underwrite`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/underwrite`);
  },

  async analyzeRejection(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/persuasion/analyze`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/persuasion/analyze`);
  },

  async suggestFix(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/persuasion/suggest`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/persuasion/suggest`);
  },

  async respondToOffer(sessionId: string, action: string, amount?: number, tenure?: number) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/persuasion/respond`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, custom_amount: amount, custom_tenure: tenure }),
    });
    return checkResponse(res, `/session/${sessionId}/persuasion/respond`);
  },

  async recalculateTerms(sessionId: string, principal: number, tenure: number, rate?: number) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/recalculate-terms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ principal, tenure_months: tenure, rate }),
    });
    return checkResponse(res, `/session/${sessionId}/recalculate-terms`);
  },

  async sanction(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/sanction`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/sanction`);
  },

  async advisory(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/advisory`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/advisory`);
  },

  async endSession(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/end`, { method: 'POST' });
    return checkResponse(res, `/session/${sessionId}/end`);
  },
  
  async chat(sessionId: string, message: string, history: any[] = []) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    });
    return checkResponse(res, `/session/${sessionId}/chat`);
  },
  
  async getSessionsByPhone(phone: string) {
    const res = await fetch(`${BASE_URL}/session/by-phone/${phone}`);
    return checkResponse(res, `/session/by-phone/${phone}`);
  },

  async getHistory(sessionId: string) {
    const res = await fetch(`${BASE_URL}/session/${sessionId}/history`);
    return checkResponse(res, `/session/${sessionId}/history`);
  }
};

