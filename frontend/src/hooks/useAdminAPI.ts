/**
 * useAdminAPI - Hook for admin API interactions
 */

import { useState, useCallback } from 'react';
import type {
  AdminStatsOverviewResponse,
  LendersListResponse,
  LenderInfoRequest,
  LenderInfoResponse,
  ReportRequest,
  ReportResponse,
  PerformanceMetricsResponse,
  AdminTrendsResponse,
  AdminHealthResponse,
  ConversionFunnelMetrics,
  LoanAnalyticsResponse,
  SystemInfoResponse,
} from '../types/admin';

import { BASE_URL } from '../api/client';

const API_BASE_URL = BASE_URL;

interface UseAdminAPIReturn {
  // State
  loading: boolean;
  error: string | null;
  
  // Data fetching
  getStatsOverview: (days?: number) => Promise<AdminStatsOverviewResponse>;
  getLoanAnalytics: (days?: number) => Promise<LoanAnalyticsResponse>;
  getConversionFunnel: () => Promise<ConversionFunnelMetrics>;
  
  // Lender management
  listLenders: () => Promise<LendersListResponse>;
  getLender: (lenderId: string) => Promise<LenderInfoResponse>;
  createLender: (request: LenderInfoRequest) => Promise<LenderInfoResponse>;
  updateLender: (lenderId: string, request: LenderInfoRequest) => Promise<LenderInfoResponse>;
  deleteLender: (lenderId: string) => Promise<boolean>;
  
  // Performance & trends
  getPerformanceMetrics: (days?: number) => Promise<PerformanceMetricsResponse>;
  getTrends: (days?: number) => Promise<AdminTrendsResponse>;
  
  // Reporting
  generateReport: (request: ReportRequest) => Promise<ReportResponse>;
  getReport: (reportId: string) => Promise<any>;
  downloadReport: (reportId: string, format: string) => Promise<any>;
  
  // System
  healthCheck: () => Promise<AdminHealthResponse>;
  getSystemInfo: () => Promise<SystemInfoResponse>;
  
  // Utilities
  clearError: () => void;
  reset: () => void;
}

export const useAdminAPI = (): UseAdminAPIReturn => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ========================================================================
  // Statistics & Overview
  // ========================================================================

  const getStatsOverview = useCallback(
    async (days: number = 30): Promise<AdminStatsOverviewResponse> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `${API_BASE_URL}/admin/stats/overview?days=${days}`,
          {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch overview');
        }

        const data: AdminStatsOverviewResponse = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const getLoanAnalytics = useCallback(
    async (days: number = 30): Promise<LoanAnalyticsResponse> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `${API_BASE_URL}/admin/stats/loans?days=${days}`,
          {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch loan analytics');
        }

        const data: LoanAnalyticsResponse = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const getConversionFunnel = useCallback(
    async (): Promise<ConversionFunnelMetrics> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_BASE_URL}/admin/stats/conversion`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch conversion funnel');
        }

        const data: ConversionFunnelMetrics = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // ========================================================================
  // Lender Management
  // ========================================================================

  const listLenders = useCallback(async (): Promise<LendersListResponse> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/admin/lenders`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch lenders');
      }

      const data: LendersListResponse = await response.json();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getLender = useCallback(
    async (lenderId: string): Promise<LenderInfoResponse> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_BASE_URL}/admin/lenders/${lenderId}`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch lender');
        }

        const data: LenderInfoResponse = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const createLender = useCallback(
    async (request: LenderInfoRequest): Promise<LenderInfoResponse> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_BASE_URL}/admin/lenders`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to create lender');
        }

        const data: LenderInfoResponse = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const updateLender = useCallback(
    async (
      lenderId: string,
      request: LenderInfoRequest
    ): Promise<LenderInfoResponse> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_BASE_URL}/admin/lenders/${lenderId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to update lender');
        }

        const data: LenderInfoResponse = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const deleteLender = useCallback(
    async (lenderId: string): Promise<boolean> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_BASE_URL}/admin/lenders/${lenderId}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to delete lender');
        }

        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // ========================================================================
  // Performance & Trends
  // ========================================================================

  const getPerformanceMetrics = useCallback(
    async (days: number = 30): Promise<PerformanceMetricsResponse> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `${API_BASE_URL}/admin/performance?days=${days}`,
          {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch performance metrics');
        }

        const data: PerformanceMetricsResponse = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const getTrends = useCallback(
    async (days: number = 30): Promise<AdminTrendsResponse> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `${API_BASE_URL}/admin/trends?days=${days}`,
          {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch trends');
        }

        const data: AdminTrendsResponse = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // ========================================================================
  // Reporting
  // ========================================================================

  const generateReport = useCallback(
    async (request: ReportRequest): Promise<ReportResponse> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_BASE_URL}/admin/reports/generate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to generate report');
        }

        const data: ReportResponse = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const getReport = useCallback(async (reportId: string): Promise<any> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/admin/reports/${reportId}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch report');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const downloadReport = useCallback(
    async (reportId: string, format: string): Promise<any> => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `${API_BASE_URL}/admin/reports/${reportId}/download?format=${format}`,
          {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to download report');
        }

        const data = await response.json();
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error occurred';
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // ========================================================================
  // System
  // ========================================================================

  const healthCheck = useCallback(async (): Promise<AdminHealthResponse> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/admin/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Health check failed');
      }

      const data: AdminHealthResponse = await response.json();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getSystemInfo = useCallback(async (): Promise<SystemInfoResponse> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/admin/system/info`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch system info');
      }

      const data: SystemInfoResponse = await response.json();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // ========================================================================
  // Utilities
  // ========================================================================

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const reset = useCallback(() => {
    setError(null);
    setLoading(false);
  }, []);

  return {
    loading,
    error,
    getStatsOverview,
    getLoanAnalytics,
    getConversionFunnel,
    listLenders,
    getLender,
    createLender,
    updateLender,
    deleteLender,
    getPerformanceMetrics,
    getTrends,
    generateReport,
    getReport,
    downloadReport,
    healthCheck,
    getSystemInfo,
    clearError,
    reset,
  };
};

export default useAdminAPI;
