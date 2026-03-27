/**
 * AdminAnalytics - Analytics visualization component with trends and insights
 */

import React, { useState, useEffect } from 'react';
import useAdminAPI from '../hooks/useAdminAPI';
import type { AdminTrendsResponse, LoanAnalyticsResponse } from '../types/admin';

interface AdminAnalyticsProps {
  periodDays: number;
}

const AdminAnalytics: React.FC<AdminAnalyticsProps> = ({ periodDays }) => {
  const { getTrends, getLoanAnalytics, loading, error } = useAdminAPI();
  const [trends, setTrends] = useState<AdminTrendsResponse | null>(null);
  const [analytics, setAnalytics] = useState<LoanAnalyticsResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'trends' | 'users' | 'efficiency'>('trends');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [trendsData, analyticsData] = await Promise.all([
          getTrends(periodDays),
          getLoanAnalytics(periodDays),
        ]);
        setTrends(trendsData);
        setAnalytics(analyticsData);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
      }
    };

    fetchData();
  }, [periodDays]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-700 font-semibold">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error || !trends || !analytics) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <p className="text-red-900 font-semibold">Failed to load analytics</p>
        <p className="text-red-700 text-sm">{error || 'No data available'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-gray-900">Analytics & Insights</h2>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-lg border-b border-gray-200">
        <div className="flex">
          {(['trends', 'users', 'efficiency'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-4 px-6 font-semibold capitalize transition-colors ${
                activeTab === tab
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-700 hover:text-gray-900'
              }`}
            >
              {tab === 'trends' && '📈 Trends'}
              {tab === 'users' && '👥 User Profiles'}
              {tab === 'efficiency' && '⚡ Efficiency'}
            </button>
          ))}
        </div>
      </div>

      {/* Trends Tab */}
      {activeTab === 'trends' && (
        <div className="space-y-6">
          <TrendsSection trends={trends} />
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="space-y-6">
          <UserProfilesSection userStats={analytics.user_profile_stats} />
        </div>
      )}

      {/* Efficiency Tab */}
      {activeTab === 'efficiency' && (
        <div className="space-y-6">
          <EfficiencySection trends={trends} />
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Trends Section
// ============================================================================

interface TrendsSectionProps {
  trends: AdminTrendsResponse;
}

const TrendsSection: React.FC<TrendsSectionProps> = ({ trends }) => {
  const { summary } = trends;

  return (
    <>
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <SummaryCard
          label="Total Loans Compared"
          value={summary.total_loans.toLocaleString()}
          icon="📊"
          color="blue"
        />
        <SummaryCard
          label="Total Conversions"
          value={summary.total_conversions.toLocaleString()}
          icon="✓"
          color="green"
        />
        <SummaryCard
          label="Avg Daily Loans"
          value={summary.avg_daily_loans.toFixed(0)}
          icon="📅"
          color="purple"
        />
        <SummaryCard
          label="Peak Day Loans"
          value={summary.peak_day_loans.toLocaleString()}
          subtitle={summary.peak_day_loans_date}
          icon="🔥"
          color="yellow"
        />
      </div>

      {/* Trend Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrendChart
          title="Loans Compared Over Time"
          data={trends.trends.dates}
          values={trends.trends.loans_compared}
          color="rgb(59, 130, 246)"
          unit=""
        />
        <TrendChart
          title="Conversion Rate Trend"
          data={trends.trends.dates}
          values={trends.trends.conversions}
          color="rgb(34, 197, 94)"
          unit="conversions"
        />
        <TrendChart
          title="Average EMI Offered"
          data={trends.trends.dates}
          values={trends.trends.avg_emi}
          color="rgb(168, 85, 247)"
          unit="₹"
        />
        <TrendChart
          title="Average Interest Rate"
          data={trends.trends.dates}
          values={trends.trends.avg_rate}
          color="rgb(239, 68, 68)"
          unit="%"
        />
      </div>

      {/* Detailed Metrics Table */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">Detailed Metrics</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-gray-300">
                <th className="text-left py-3 px-4 font-semibold text-gray-700">Date</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Loans</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Conversions</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Avg EMI</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Avg Rate</th>
                <th className="text-right py-3 px-4 font-semibold text-gray-700">Approvals</th>
              </tr>
            </thead>
            <tbody>
              {trends.trends.dates.map((date: string, index: number) => (
                <tr key={date} className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="py-3 px-4 text-gray-900">{date}</td>
                  <td className="text-right py-3 px-4 text-gray-900">
                    {trends.trends.loans_compared[index]}
                  </td>
                  <td className="text-right py-3 px-4 text-green-600 font-semibold">
                    {trends.trends.conversions[index]}
                  </td>
                  <td className="text-right py-3 px-4 text-gray-900">
                    ₹{trends.trends.avg_emi[index].toLocaleString()}
                  </td>
                  <td className="text-right py-3 px-4 text-gray-900">
                    {trends.trends.avg_rate[index].toFixed(2)}%
                  </td>
                  <td className="text-right py-3 px-4 text-gray-900">
                    {(trends.trends.avg_approval[index] * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
};

// ============================================================================
// User Profiles Section
// ============================================================================

interface UserProfilesSectionProps {
  userStats: any;
}

const UserProfilesSection: React.FC<UserProfilesSectionProps> = ({ userStats }) => {
  const stats = [
    { label: 'Average Loan Amount', value: `₹${userStats.avg_loan_amount.toLocaleString()}`, icon: '💰' },
    { label: 'Average Tenure', value: `${userStats.avg_tenure} months`, icon: '📅' },
    { label: 'Average Salary', value: `₹${userStats.avg_salary.toLocaleString()}`, icon: '💵' },
    { label: 'Average Credit Score', value: `${userStats.avg_credit_score}`, icon: '📊' },
    { label: 'Average Obligations', value: `₹${userStats.avg_obligations.toLocaleString()}`, icon: '⚖️' },
    { label: 'Average Age', value: `${userStats.avg_age} years`, icon: '👤' },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {stats.map((stat) => (
        <div key={stat.label} className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-semibold mb-2">{stat.label}</p>
              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
            </div>
            <span className="text-3xl">{stat.icon}</span>
          </div>
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// Efficiency Section
// ============================================================================

interface EfficiencySectionProps {
  trends: AdminTrendsResponse;
}

const EfficiencySection: React.FC<EfficiencySectionProps> = ({ trends }) => {
  const { avg_rate, avg_emi, avg_approval } = trends.trends;

  // Calculate efficiency metrics
  const avgRate = avg_rate.reduce((a: number, b: number) => a + b, 0) / avg_rate.length;
  const avgEMI = avg_emi.reduce((a: number, b: number) => a + b, 0) / avg_emi.length;
  const avgApproval = avg_approval.reduce((a: number, b: number) => a + b, 0) / avg_approval.length;

  // Efficiency score (lower rate & EMI, higher approval = better)
  const minRate = Math.min(...avg_rate);
  const maxRate = Math.max(...avg_rate);
  const minEMI = Math.min(...avg_emi);
  const maxEMI = Math.max(...avg_emi);

  const rateScore = ((maxRate - avgRate) / (maxRate - minRate)) * 100;
  const emiScore = ((maxEMI - avgEMI) / (maxEMI - minEMI)) * 100;
  const approvalScore = avgApproval * 100;

  const overallScore = (rateScore * 0.3 + emiScore * 0.3 + approvalScore * 0.4);

  return (
    <>
      {/* Overall Efficiency Score */}
      <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg border-2 border-green-200 p-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-green-700 font-semibold text-lg mb-2">Overall Efficiency Score</p>
            <p className="text-gray-600">Based on interest rates, EMI, and approval probabilities</p>
          </div>
          <div className="text-center">
            <p className="text-6xl font-bold text-green-600">{overallScore.toFixed(1)}</p>
            <p className="text-green-700 font-semibold mt-2">/100</p>
          </div>
        </div>
      </div>

      {/* Efficiency Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <EfficiencyMeter
          label="Interest Rate Efficiency"
          score={rateScore}
          subtitle={`Avg Rate: ${avgRate.toFixed(2)}%`}
          color="blue"
        />
        <EfficiencyMeter
          label="EMI Efficiency"
          score={emiScore}
          subtitle={`Avg EMI: ₹${avgEMI.toLocaleString()}`}
          color="purple"
        />
        <EfficiencyMeter
          label="Approval Efficiency"
          score={approvalScore}
          subtitle={`Avg Approval: ${(avgApproval * 100).toFixed(1)}%`}
          color="green"
        />
      </div>

      {/* Insights */}
      <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
        <h3 className="text-lg font-bold text-blue-900 mb-4">💡 Efficiency Insights</h3>
        <ul className="space-y-3 text-blue-900">
          <li className="flex items-start gap-3">
            <span className="text-xl">📊</span>
            <span>
              <strong>Interest Rates:</strong> The average interest rate is {avgRate.toFixed(2)}%, 
              which is {avgRate < 8.5 ? 'below' : 'above'} market average.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-xl">💰</span>
            <span>
              <strong>EMI Amounts:</strong> Average EMI of ₹{avgEMI.toLocaleString()} shows 
              {avgEMI < 12000 ? ' competitive' : ' reasonable'} loan sizing.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-xl">✅</span>
            <span>
              <strong>Approval Rate:</strong> {(avgApproval * 100).toFixed(1)}% average approval 
              probability indicates {avgApproval > 0.85 ? 'excellent' : avgApproval > 0.75 ? 'good' : 'moderate'} credit risk management.
            </span>
          </li>
        </ul>
      </div>
    </>
  );
};

// ============================================================================
// Reusable Components
// ============================================================================

interface SummaryCardProps {
  label: string;
  value: string;
  icon: string;
  color: 'blue' | 'green' | 'purple' | 'yellow';
  subtitle?: string;
}

const SummaryCard: React.FC<SummaryCardProps> = ({
  label,
  value,
  icon,
  color,
  subtitle,
}) => {
  const colorMap = {
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    purple: 'bg-purple-50 border-purple-200',
    yellow: 'bg-yellow-50 border-yellow-200',
  };

  return (
    <div className={`rounded-lg border-2 p-6 ${colorMap[color]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-gray-600 text-sm font-semibold mb-1">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="text-xs text-gray-600 mt-1">{subtitle}</p>}
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
};

interface TrendChartProps {
  title: string;
  data: string[];
  values: number[];
  color: string;
  unit: string;
}

const TrendChart: React.FC<TrendChartProps> = ({ title, data, values, color, unit }) => {
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue || 1;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-lg font-bold text-gray-900 mb-4">{title}</h3>

      {/* Simple chart */}
      <div className="space-y-2 mb-6">
        {values.slice(-7).map((value, idx) => {
          const percentage = ((value - minValue) / range) * 100;
          return (
            <div key={idx} className="flex items-center gap-4">
              <span className="text-xs text-gray-600 w-10">
                {data[data.length - 7 + idx]}
              </span>
              <div className="flex-1 bg-gray-200 rounded-full h-6 overflow-hidden">
                <div
                  className="h-full rounded-full flex items-center justify-center text-white text-xs font-bold"
                  style={{
                    width: `${Math.max(Math.min(percentage, 100), 5)}%`,
                    background: color,
                  }}
                >
                  {percentage > 20 && `${value.toFixed(0)}${unit}`}
                </div>
              </div>
              <span className="text-sm font-semibold text-gray-900 w-16 text-right">
                {value.toFixed(unit === '%' ? 2 : 0)}{unit}
              </span>
            </div>
          );
        })}
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-3 gap-2 pt-4 border-t border-gray-200">
        <div>
          <p className="text-xs text-gray-600">Min</p>
          <p className="font-bold text-gray-900">{minValue.toFixed(unit === '%' ? 2 : 0)}{unit}</p>
        </div>
        <div>
          <p className="text-xs text-gray-600">Avg</p>
          <p className="font-bold text-gray-900">
            {(values.reduce((a, b) => a + b, 0) / values.length).toFixed(unit === '%' ? 2 : 0)}{unit}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-600">Max</p>
          <p className="font-bold text-gray-900">{maxValue.toFixed(unit === '%' ? 2 : 0)}{unit}</p>
        </div>
      </div>
    </div>
  );
};

interface EfficiencyMeterProps {
  label: string;
  score: number;
  subtitle: string;
  color: 'blue' | 'green' | 'purple';
}

const EfficiencyMeter: React.FC<EfficiencyMeterProps> = ({
  label,
  score,
  subtitle,
  color,
}) => {
  const colorMap = {
    blue: { bg: 'bg-blue-100', bar: 'bg-blue-500', text: 'text-blue-900' },
    green: { bg: 'bg-green-100', bar: 'bg-green-500', text: 'text-green-900' },
    purple: { bg: 'bg-purple-100', bar: 'bg-purple-500', text: 'text-purple-900' },
  };

  const { bg, bar, text } = colorMap[color];

  return (
    <div className={`rounded-lg ${bg} p-6`}>
      <p className={`font-semibold ${text} mb-2`}>{label}</p>
      <p className="text-3xl font-bold text-gray-900 mb-3">{score.toFixed(1)}</p>
      <div className="bg-gray-300 rounded-full h-3 mb-3 overflow-hidden">
        <div
          className={`${bar} h-3`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <p className={`text-sm ${text}`}>{subtitle}</p>
    </div>
  );
};

export default AdminAnalytics;
