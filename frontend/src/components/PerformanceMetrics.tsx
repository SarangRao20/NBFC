/**
 * PerformanceMetrics - System-wide performance metrics
 */

import React, { useState, useEffect } from 'react';
import useAdminAPI from '../hooks/useAdminAPI';
import type { PerformanceMetricsResponse } from '../types/admin';

interface PerformanceMetricsProps {
  periodDays?: number;
}

const PerformanceMetrics: React.FC<PerformanceMetricsProps> = ({ periodDays = 30 }) => {
  const { getPerformanceMetrics, loading } = useAdminAPI();
  const [metrics, setMetrics] = useState<PerformanceMetricsResponse | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await getPerformanceMetrics(periodDays);
        setMetrics(data);
      } catch (err) {
        console.error('Failed to fetch metrics:', err);
      }
    };

    fetchMetrics();
    // Refresh every 5 minutes
    const interval = setInterval(fetchMetrics, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [periodDays]);

  if (loading || !metrics) {
    return (
      <div className="flex justify-center py-20">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-700 font-semibold">Loading metrics...</p>
        </div>
      </div>
    );
  }

  const getStatusColor = (value: number, threshold: number = 70) => {
    if (value >= threshold) return 'text-green-600 bg-green-50 border-green-200';
    if (value >= threshold - 20) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-red-600 bg-red-50 border-red-200';
  };

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-gray-900">📊 Performance Metrics</h2>

      {/* Key Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          label="Total Loans Compared"
          value={metrics.kpis.total_loans_compared}
          subtitle="All time"
          icon="📱"
        />
        <MetricCard
          label="Conversion Rate"
          value={`${metrics.kpis.conversion_rate.toFixed(2)}%`}
          subtitle="Current period"
          icon="📈"
        />
        <MetricCard
          label="Avg EMI Offered"
          value={`₹${metrics.kpis.avg_emi.toLocaleString()}`}
          subtitle="System average"
          icon="💰"
        />
        <MetricCard
          label="Lenders Connected"
          value={metrics.lender_performance.length}
          subtitle="Active partnerships"
          icon="🏦"
        />
      </div>

      {/* Lender Performance */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-6">🏦 Top Performing Lenders</h3>
        <div className="space-y-4">
          {metrics.lender_performance.slice(0, 5).map((lender) => (
            <div key={lender.lender_id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-gray-900">{lender.lender_name}</h4>
                <span className="text-sm text-gray-600">{lender.selection_rate.toFixed(1)}% rate</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${lender.selection_rate}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-xs text-gray-600 mt-2">
                <span>{lender.selections} selections</span>
                <span>Market Share: {lender.market_share.toFixed(1)}%</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Efficiency Scores */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-6">⭐ Efficiency Scores</h3>
        <div className="space-y-4">
          {metrics.efficiency_scores.slice(0, 5).map((score) => (
            <div key={score.lender_id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-gray-900">{score.lender_name}</h4>
                <span className="text-lg font-bold text-blue-600">{score.efficiency_score.toFixed(1)}</span>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-gray-600">EMI Score</p>
                  <p className="font-semibold text-gray-900">{score.emi_score.toFixed(1)}</p>
                </div>
                <div>
                  <p className="text-gray-600">Rate Score</p>
                  <p className="font-semibold text-gray-900">{score.rate_score.toFixed(1)}</p>
                </div>
                <div>
                  <p className="text-gray-600">Approval Score</p>
                  <p className="font-semibold text-gray-900">{score.approval_score.toFixed(1)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Performers */}
      {metrics.top_performers.length > 0 && (
        <div className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">🏆 Top Performers</h3>
          <div className="flex flex-wrap gap-2">
            {metrics.top_performers.map((lender, idx) => (
              <span
                key={idx}
                className="bg-green-100 text-green-800 px-4 py-2 rounded-full font-semibold text-sm"
              >
                #{idx + 1} {lender}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

interface MetricCardProps {
  label: string;
  value: string | number;
  subtitle: string;
  icon: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, subtitle, icon }) => (
  <div className="bg-white rounded-lg shadow-lg p-6 border-l-4 border-blue-600">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-gray-600 text-sm font-medium">{label}</p>
        <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
        <p className="text-gray-500 text-xs mt-2">{subtitle}</p>
      </div>
      <div className="text-4xl opacity-50">{icon}</div>
    </div>
  </div>
);

export default PerformanceMetrics;
