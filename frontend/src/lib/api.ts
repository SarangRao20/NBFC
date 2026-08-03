const API_BASE = 'http://localhost:8000';

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  details?: any;
}

/**
 * Core API Client for MongoDB & FastAPI backend integration
 */
export const api = {
  // ── 1. Authentication & MongoDB Users ─────────────────────────────
  
  async loginWithPassword(phone: string, password: string): Promise<ApiResponse> {
    try {
      const formData = new FormData();
      formData.append('phone', phone);
      formData.append('password', password);

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || 'Login failed');
      }
      return { success: true, data };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async registerCustomer(userData: {
    phone: string;
    email: string;
    name: string;
    password: string;
    city?: string;
    salary?: number;
    dob?: string;
    profession?: string;
    address?: string;
  }): Promise<ApiResponse> {
    try {
      const formData = new FormData();
      Object.entries(userData).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          formData.append(key, String(value));
        }
      });

      const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || 'Registration failed');
      }
      return { success: true, data };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async checkProfileCompleteness(phone: string): Promise<ApiResponse> {
    try {
      const res = await fetch(`${API_BASE}/auth/check-profile/${phone}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Profile check failed');
      return { success: true, data };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async updateProfile(params: {
    phone: string;
    name?: string;
    email?: string;
    city?: string;
    salary?: number;
    credit_score?: number;
  }): Promise<ApiResponse> {
    try {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) queryParams.append(k, String(v));
      });

      const res = await fetch(`${API_BASE}/auth/update-profile?${queryParams.toString()}`, {
        method: 'POST',
      });

      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.detail || data.message || 'Profile update failed');
      }
      return { success: true, data };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async sendOtp(phone: string, email?: string): Promise<ApiResponse> {
    try {
      const formData = new FormData();
      formData.append('phone', phone);
      if (email) formData.append('email', email);

      const res = await fetch(`${API_BASE}/auth/send-otp`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      return { success: data.success ?? res.ok, data };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async verifyOtp(phone: string, otp: string, useDevOtp: boolean = true): Promise<ApiResponse> {
    try {
      const formData = new FormData();
      formData.append('phone', phone);
      formData.append('otp', otp);
      formData.append('use_dev_otp', String(useDevOtp));

      const res = await fetch(`${API_BASE}/auth/verify-otp`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      return { success: data.success ?? res.ok, data };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  // ── 2. Session & StateGraph Workflow ─────────────────────────────
  
  async startSession(): Promise<ApiResponse> {
    try {
      const res = await fetch(`${API_BASE}/session/start`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      return { success: true, data: await res.json() };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async getSessionState(sessionId: string): Promise<ApiResponse> {
    try {
      const res = await fetch(`${API_BASE}/session/${sessionId}/state`);
      if (!res.ok) throw new Error(await res.text());
      return { success: true, data: await res.json() };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  // ── 3. Sales & Loan Parameters ───────────────────────────────────
  
  async updateLoanParams(sessionId: string, params: { requested_amount: number; tenure_months: number; purpose?: string }): Promise<ApiResponse> {
    try {
      const res = await fetch(`${API_BASE}/sales/capture-loan-params/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (!res.ok) throw new Error(await res.text());
      return { success: true, data: await res.json() };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  // ── 4. KYC Upload ────────────────────────────────────────────────
  
  async uploadDocument(sessionId: string, docType: string, file: File): Promise<ApiResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', docType);
      
      const res = await fetch(`${API_BASE}/documents/upload/${sessionId}`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      return { success: true, data: await res.json() };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  // ── 5. Underwriting Decision Engine ──────────────────────────────
  
  async underwrite(sessionId: string): Promise<ApiResponse> {
    try {
      const res = await fetch(`${API_BASE}/session/${sessionId}/underwrite`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      return { success: true, data: await res.json() };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  // ── 6. Lender Selection ──────────────────────────────────────────
  
  async selectLender(sessionId: string, payload: { selected_lender_id: string }): Promise<ApiResponse> {
    try {
      const res = await fetch(`${API_BASE}/session/${sessionId}/select-lender`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text());
      return { success: true, data: await res.json() };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  // ── 7. Sanction & Letter Generation ─────────────────────────────
  
  async generateSanction(sessionId: string): Promise<ApiResponse> {
    try {
      const res = await fetch(`${API_BASE}/session/${sessionId}/sanction`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      return { success: true, data: await res.json() };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  getDownloadLetterUrl(sessionId: string): string {
    return `${API_BASE}/session/${sessionId}/download-letter`;
  },

  // ── 8. Repayments & EMI ──────────────────────────────────────────
  
  async payEmi(sessionId: string): Promise<ApiResponse> {
    try {
      const res = await fetch(`${API_BASE}/session/${sessionId}/pay-emi`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      return { success: true, data: await res.json() };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  },

  async getLoanHistory(phone: string): Promise<ApiResponse> {
    try {
      const res = await fetch(`${API_BASE}/session/loan-history/${phone}`);
      if (!res.ok) throw new Error(await res.text());
      return { success: true, data: await res.json() };
    } catch (e: any) {
      return { success: false, error: e.message };
    }
  }
};
