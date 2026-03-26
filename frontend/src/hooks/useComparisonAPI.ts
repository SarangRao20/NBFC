/**
 * useComparisonAPI - Hook for loan comparison API interactions
 */

import { useState, useCallback } from 'react';
import type {
  GetLoansRequest,
  GetLoansResponse,
  SelectLoanRequest,
  SelectLoanResponse,
  WhatIfRequest,
  WhatIfResponse,
  LendersInfo,
} from '../types/comparison';

const API_BASE_URL = (import.meta.env.REACT_APP_API_URL as string) || 'http://localhost:8000';

interface UseComparisonAPIReturn {
  // State
  loading: boolean;
  error: string | null;
  comparisonResult: GetLoansResponse | null;
  selectedLender: string | null;
  whatIfResult: WhatIfResponse | null;

  // Methods
  getLoans: (request: GetLoansRequest) => Promise<GetLoansResponse>;
  selectLoan: (request: SelectLoanRequest) => Promise<SelectLoanResponse>;
  runWhatIf: (request: WhatIfRequest) => Promise<WhatIfResponse>;
  checkLenders: () => Promise<LendersInfo>;
  clearError: () => void;
  resetComparison: () => void;
}

export const useComparisonAPI = (): UseComparisonAPIReturn => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<GetLoansResponse | null>(null);
  const [selectedLender, setSelectedLender] = useState<string | null>(null);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResponse | null>(null);

  // Fetch loans comparison
  const getLoans = useCallback(async (request: GetLoansRequest): Promise<GetLoansResponse> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/comparison/get-loans`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch loans');
      }

      const data: GetLoansResponse = await response.json();
      setComparisonResult(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Select loan
  const selectLoan = useCallback(async (request: SelectLoanRequest): Promise<SelectLoanResponse> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/comparison/select-loan`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to select loan');
      }

      const data: SelectLoanResponse = await response.json();
      if (data.success) {
        setSelectedLender(request.selected_lender_id);
      }
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // What-if simulation
  const runWhatIf = useCallback(async (request: WhatIfRequest): Promise<WhatIfResponse> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/comparison/what-if`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to run simulation');
      }

      const data: WhatIfResponse = await response.json();
      setWhatIfResult(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Check available lenders
  const checkLenders = useCallback(async (): Promise<LendersInfo> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/comparison/lenders`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch lenders');
      }

      const data: LendersInfo = await response.json();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const resetComparison = useCallback(() => {
    setComparisonResult(null);
    setSelectedLender(null);
    setWhatIfResult(null);
    setError(null);
  }, []);

  return {
    loading,
    error,
    comparisonResult,
    selectedLender,
    whatIfResult,
    getLoans,
    selectLoan,
    runWhatIf,
    checkLenders,
    clearError,
    resetComparison,
  };
};

export default useComparisonAPI;
