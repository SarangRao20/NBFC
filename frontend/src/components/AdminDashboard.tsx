/**
 * AdminDashboard - Main admin control panel with navigation and layout
 */

import React, { useState, useEffect } from 'react';
import useAdminAPI from '../../hooks/useAdminAPI';
import AdminAnalytics from './AdminAnalytics';
import LenderManagement from './LenderManagement';
import PerformanceMetrics from './PerformanceMetrics';
import ReportsPanel from './ReportsPanel';

type AdminView = 'dashboard' | 'analytics' | 'lenders' | 'performance' | 'reports' | 'settings';

interface AdminDashboardProps {
  userName?: string;
  userRole?: 'admin' | 'analyst' | 'viewer';
  onLogout?: () => void;
}

const AdminDashboard: React.FC<AdminDashboardProps> = ({
  userName = 'Admin User',
  userRole = 'admin',
  onLogout,
}) => {
  const [activeView, setActiveView] = useState<AdminView>('dashboard');
  const [selectedPeriodDays, setSelectedPeriodDays] = useState(30);
  const { healthCheck, error: apiError, clearError } = useAdminAPI();

  // Check admin API health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await healthCheck();
      } catch (err) {
        console.error('Admin API health check failed:', err);
      }
    };

    checkHealth();
  }, []);

  const navigationItems: { id: AdminView; label: string; icon: string; requires: string[] }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊', requires: ['admin', 'analyst', 'viewer'] },
    { id: 'analytics', label: 'Analytics', icon: '📈', requires: ['admin', 'analyst', 'viewer'] },
    { id: 'lenders', label: 'Lenders', icon: '🏦', requires: ['admin'] },
    { id: 'performance', label: 'Performance', icon: '⭐', requires: ['admin', 'analyst'] },
    { id: 'reports', label: 'Reports', icon: '📄', requires: ['admin', 'analyst'] },
    { id: 'settings', label: 'Settings', icon: '⚙️', requires: ['admin'] },
  ];

  const canAccessView = (itemId: AdminView) => {
    const item = navigationItems.find((i) => i.id === itemId);
    return item?.requires.includes(userRole) || false;
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
        <div className="flex items-center justify-between px-8 py-4">
          <div>
            <h1 className="text-3xl font-bold">🎛️ Admin Dashboard</h1>
            <p className="text-blue-100 text-sm mt-1">Loan Marketplace Control Center</p>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="font-semibold">{userName}</p>
              <p className="text-sm text-blue-100 capitalize">{userRole}</p>
            </div>
            <button
              onClick={onLogout}
              className="bg-blue-700 hover:bg-blue-900 px-6 py-2 rounded-lg font-semibold transition-colors"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Period Selector */}
        <div className="px-8 py-3 bg-blue-700 flex items-center gap-4">
          <label className="font-semibold">Period:</label>
          <select
            value={selectedPeriodDays}
            onChange={(e) => setSelectedPeriodDays(Number(e.target.value))}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg border border-blue-500 focus:outline-none"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={60}>Last 60 days</option>
            <option value={90}>Last 90 days</option>
            <option value={180}>Last 6 months</option>
            <option value={365}>Last year</option>
          </select>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex min-h-[calc(100vh-200px)]">
        {/* Sidebar Navigation */}
        <nav className="w-64 bg-white shadow-lg">
          <div className="p-4 space-y-2">
            {navigationItems.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  if (canAccessView(item.id)) {
                    setActiveView(item.id);
                  }
                }}
                disabled={!canAccessView(item.id)}
                className={`w-full text-left px-4 py-3 rounded-lg font-semibold transition-all ${
                  activeView === item.id
                    ? 'bg-blue-600 text-white'
                    : canAccessView(item.id)
                    ? 'text-gray-700 hover:bg-gray-100'
                    : 'text-gray-400 cursor-not-allowed'
                }`}
              >
                <span className="mr-3">{item.icon}</span>
                {item.label}
                {!canAccessView(item.id) && <span className="ml-auto text-xs">🔒</span>}
              </button>
            ))}
          </div>

          {/* Sidebar Footer */}
          <div className="absolute bottom-8 left-0 w-64 px-4">
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <p className="text-sm text-gray-700 font-semibold mb-2">💡 Tip:</p>
              <p className="text-xs text-gray-600">
                Use the period selector at the top to filter all analytics by date range.
              </p>
            </div>
          </div>
        </nav>

        {/* Content Area */}
        <main className="flex-1 overflow-auto">
          <div className="p-8">
            {/* Error Alert */}
            {apiError && (
              <div className="mb-6 bg-red-50 border-l-4 border-red-400 p-4 rounded-lg flex items-start gap-3">
                <span className="text-red-600 text-2xl">⚠️</span>
                <div className="flex-1">
                  <p className="font-bold text-red-900">API Error</p>
                  <p className="text-red-700 text-sm">{apiError}</p>
                </div>
                <button
                  onClick={clearError}
                  className="text-red-600 hover:text-red-900 font-bold"
                >
                  ✕
                </button>
              </div>
            )}

            {/* View Components */}
            {activeView === 'dashboard' && <DashboardView periodDays={selectedPeriodDays} />}
            {activeView === 'analytics' && <AdminAnalytics periodDays={selectedPeriodDays} />}
            {activeView === 'lenders' && canAccessView('lenders') && (
              <LenderManagement />
            )}
            {activeView === 'performance' && canAccessView('performance') && (
              <PerformanceMetrics periodDays={selectedPeriodDays} />
            )}
            {activeView === 'reports' && canAccessView('reports') && (
              <ReportsPanel />
            )}
            {activeView === 'settings' && canAccessView('settings') && (
              <SettingsView />
            )}

            {/* Restricted Access */}
            {!canAccessView(activeView) && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
                <p className="text-yellow-800 font-semibold text-lg">🔒 Access Restricted</p>
                <p className="text-yellow-700 mt-2">
                  Your {userRole} role doesn't have access to this section.
                </p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

// ============================================================================
// Dashboard View Component
// ============================================================================

interface DashboardViewProps {
  periodDays: number;
}

const DashboardView: React.FC<DashboardViewProps> = ({ periodDays }) => {
  const { getStatsOverview, loading, error } = useAdminAPI();
  const [overview, setOverview] = useState<any>(null);

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        const data = await getStatsOverview(periodDays);
        setOverview(data);
      } catch (err) {
        console.error('Failed to fetch overview:', err);
      }
    };

    fetchOverview();
  }, [periodDays]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-700 font-semibold">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <p className="text-red-900 font-semibold">Failed to load dashboard</p>
        <p className="text-red-700 text-sm">{error}</p>
      </div>
    );
  }

  if (!overview) {
    return <div>No data available</div>;
  }

  const { kpis, funnel } = overview;

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-gray-900">Dashboard Overview</h2>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          label="Total Loans Compared"
          value={kpis.total_loans_compared.toLocaleString()}
          icon="📊"
          color="blue"
        />
        <KPICard
          label="Conversions"
          value={kpis.conversions.toLocaleString()}
          icon="✓"
          color="green"
          subtitle={`${kpis.conversion_rate.toFixed(1)}% rate`}
        />
        <KPICard
          label="Avg EMI Offered"
          value={`₹${kpis.avg_emi.toLocaleString()}`}
          icon="💰"
          color="purple"
        />
        <KPICard
          label="Total Cost Savings"
          value={`₹${(kpis.total_cost_savings / 1000000).toFixed(1)}M`}
          icon="💎"
          color="yellow"
        />
      </div>

      {/* Conversion Funnel */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-xl font-bold text-gray-900 mb-6">Conversion Funnel</h3>
        <FunnelChart funnel={funnel} />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <p className="text-gray-600 text-sm mb-2">Unique Users</p>
          <p className="text-3xl font-bold text-gray-900">
            {kpis.total_unique_users.toLocaleString()}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-lg p-6">
          <p className="text-gray-600 text-sm mb-2">Avg Approval Probability</p>
          <p className="text-3xl font-bold text-gray-900">
            {(kpis.avg_approval_probability * 100).toFixed(1)}%
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-lg p-6">
          <p className="text-gray-600 text-sm mb-2">Avg Interest Rate</p>
          <p className="text-3xl font-bold text-gray-900">
            {kpis.avg_interest_rate.toFixed(2)}%
          </p>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// KPI Card Component
// ============================================================================

interface KPICardProps {
  label: string;
  value: string;
  icon: string;
  color: 'blue' | 'green' | 'purple' | 'yellow';
  subtitle?: string;
}

const KPICard: React.FC<KPICardProps> = ({ label, value, icon, color, subtitle }) => {
  const colorMap = {
    blue: 'bg-blue-50 border-blue-200 text-blue-900',
    green: 'bg-green-50 border-green-200 text-green-900',
    purple: 'bg-purple-50 border-purple-200 text-purple-900',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-900',
  };

  return (
    <div className={`rounded-lg border-2 p-6 ${colorMap[color]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold opacity-75">{label}</p>
          <p className="text-2xl font-bold mt-2">{value}</p>
          {subtitle && <p className="text-xs opacity-75 mt-1">{subtitle}</p>}
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
};

// ============================================================================
// Funnel Chart Component
// ============================================================================

interface FunnelChartProps {
  funnel: any;
}

const FunnelChart: React.FC<FunnelChartProps> = ({ funnel }) => {
  const stages = [
    {
      label: 'View Loan Offers',
      value: funnel.total_views,
      color: 'bg-blue-500',
    },
    {
      label: 'Compare Loans',
      value: funnel.total_comparisons,
      percentage: funnel.view_to_compare,
      color: 'bg-blue-600',
    },
    {
      label: 'Select & Proceed',
      value: funnel.total_selections,
      percentage: funnel.compare_to_select,
      color: 'bg-blue-700',
    },
  ];

  const maxValue = Math.max(...stages.map((s) => s.value));

  return (
    <div className="space-y-6">
      {stages.map((stage, index) => {
        const percentage = (stage.value / maxValue) * 100;
        return (
          <div key={stage.label}>
            <div className="flex justify-between items-center mb-2">
              <span className="font-semibold text-gray-800">{stage.label}</span>
              <div className="text-right">
                <span className="font-bold text-lg text-gray-900">{stage.value.toLocaleString()}</span>
                {stage.percentage && (
                  <span className="text-sm text-gray-600 ml-2">({stage.percentage.toFixed(1)}%)</span>
                )}
              </div>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-8">
              <div
                className={`${stage.color} h-8 rounded-full flex items-center justify-center text-white font-semibold text-sm`}
                style={{ width: `${percentage}%` }}
              >
                {percentage > 10 && `${percentage.toFixed(0)}%`}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ============================================================================
// Settings View Component
// ============================================================================

const SettingsView: React.FC = () => {
  const { getSystemInfo, loading } = useAdminAPI();
  const [systemInfo, setSystemInfo] = React.useState<any>(null);

  React.useEffect(() => {
    const fetchInfo = async () => {
      try {
        const info = await getSystemInfo();
        setSystemInfo(info);
      } catch (err) {
        console.error('Failed to fetch system info:', err);
      }
    };

    fetchInfo();
  }, []);

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-gray-900">System Settings</h2>

      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4">System Information</h3>
        {loading ? (
          <p>Loading...</p>
        ) : systemInfo ? (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-gray-600 text-sm">Version</p>
              <p className="text-gray-900 font-semibold">{systemInfo.version}</p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Status</p>
              <p className="text-green-600 font-semibold">✓ {systemInfo.status}</p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Total Lenders</p>
              <p className="text-gray-900 font-semibold">{systemInfo.total_lenders}</p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Active Lenders</p>
              <p className="text-gray-900 font-semibold">{systemInfo.active_lenders}</p>
            </div>
            <div className="col-span-2">
              <p className="text-gray-600 text-sm mb-2">Features</p>
              <div className="flex flex-wrap gap-2">
                {systemInfo.features.map((feature: string) => (
                  <span
                    key={feature}
                    className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-xs font-semibold"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default AdminDashboard;
