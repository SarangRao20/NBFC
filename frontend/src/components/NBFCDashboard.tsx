/**
 * NBFC Dashboard - Lender control panel for managing loan applications and products
 * Redesigned to match user dashboard style with clean, professional UI
 */

import React, { useState, useEffect } from 'react';
import useNBFCAPI from '../hooks/useNBFCAPI';
import type { NBFCView, NBFCDashboardProps, LoanApplication, LoanProduct, NBFCStats } from '../types';
import {
  LayoutDashboard,
  ClipboardList,
  Wallet,
  TrendingUp,
  LogOut,
  ChevronDown,
  Calendar,
  Lock,
  FileText,
  User,
  CheckCircle2,
  Clock,
  XCircle,
  Landmark,
  TrendingDown,
  AlertTriangle,
  Lightbulb
} from 'lucide-react';
import clsx from 'clsx';

export type { NBFCView, NBFCDashboardProps, LoanApplication, LoanProduct, NBFCStats };

// ============================================================================
// Metric Card Component (matching DashboardPane style)
// ============================================================================

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: string;
  trendUp?: boolean;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, icon, trend, trendUp }) => (
  <div className="bg-white rounded-lg border border-slate-200 p-4 hover:border-slate-300 transition-colors">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</p>
        <p className="text-xl font-bold text-slate-800 mt-1">{value}</p>
        {trend && (
          <p className={clsx("text-xs mt-1 flex items-center gap-1", trendUp ? "text-emerald-600" : "text-slate-500")}>
            {trendUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {trend}
          </p>
        )}
      </div>
      <div className="w-9 h-9 bg-slate-100 rounded-lg flex items-center justify-center text-slate-600">
        {icon}
      </div>
    </div>
  </div>
);

// ============================================================================
// Status Badge Component
// ============================================================================

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles: Record<string, string> = {
    pending: 'bg-amber-50 text-amber-700 border-amber-200',
    under_review: 'bg-blue-50 text-blue-700 border-blue-200',
    approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    rejected: 'bg-red-50 text-red-700 border-red-200',
    disbursed: 'bg-slate-100 text-slate-700 border-slate-200',
    active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    closed: 'bg-slate-100 text-slate-600 border-slate-200',
  };

  const labels: Record<string, string> = {
    pending: 'Pending',
    under_review: 'Under Review',
    approved: 'Approved',
    rejected: 'Rejected',
    disbursed: 'Disbursed',
    active: 'Active',
    closed: 'Closed',
  };

  return (
    <span className={clsx("px-2.5 py-1 rounded-full text-xs font-semibold border", styles[status] || 'bg-slate-100 text-slate-600 border-slate-200')}>
      {labels[status] || status}
    </span>
  );
};

// ============================================================================
// Overview View Component
// ============================================================================

interface ViewProps {
  nbfcId: string;
  periodDays: number;
}

const OverviewView: React.FC<ViewProps> = ({ nbfcId, periodDays }) => {
  const { getStatsOverview, loading, error } = useNBFCAPI(nbfcId);
  const [stats, setStats] = useState<NBFCStats | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getStatsOverview(periodDays);
        setStats(data);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
      }
    };
    fetchStats();
  }, [periodDays, nbfcId]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="text-center">
          <div className="animate-spin h-8 w-8 border-2 border-slate-300 border-t-slate-600 rounded-full mx-auto mb-3"></div>
          <p className="text-slate-600 text-sm font-medium">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-900 font-semibold text-sm">Failed to load dashboard</p>
        <p className="text-red-700 text-xs mt-1">{error}</p>
      </div>
    );
  }

  const demoStats: NBFCStats = stats || {
    total_applications: 156,
    pending_review: 23,
    approved_count: 89,
    rejected_count: 44,
    disbursed_count: 67,
    total_disbursed_amount: 42500000,
    total_outstanding: 31800000,
    total_emis_collected: 5200000,
    avg_loan_amount: 635000,
    avg_interest_rate: 14.5,
    conversion_rate: 75.4,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-800">Dashboard Overview</h2>
        <span className="text-xs text-slate-500">Last updated: Just now</span>
      </div>

      {/* Primary Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Total Applications"
          value={demoStats.total_applications.toLocaleString()}
          icon={<ClipboardList size={18} />}
          trend={`${demoStats.pending_review} pending`}
        />
        <MetricCard
          label="Approved Loans"
          value={demoStats.approved_count.toLocaleString()}
          icon={<CheckCircle2 size={18} />}
          trend={`${demoStats.conversion_rate.toFixed(1)}% conversion`}
          trendUp
        />
        <MetricCard
          label="Total Disbursed"
          value={`₹${(demoStats.total_disbursed_amount / 10000000).toFixed(1)}Cr`}
          icon={<Wallet size={18} />}
        />
        <MetricCard
          label="Outstanding"
          value={`₹${(demoStats.total_outstanding / 10000000).toFixed(1)}Cr`}
          icon={<TrendingUp size={18} />}
        />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <p className="text-xs text-slate-500 mb-1">Rejected</p>
          <p className="text-lg font-bold text-red-600">{demoStats.rejected_count}</p>
          <p className="text-xs text-slate-400 mt-1">
            {((demoStats.rejected_count / demoStats.total_applications) * 100).toFixed(1)}% rate
          </p>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <p className="text-xs text-slate-500 mb-1">Avg Loan Amount</p>
          <p className="text-lg font-bold text-slate-800">₹{(demoStats.avg_loan_amount / 100000).toFixed(1)}L</p>
          <p className="text-xs text-slate-400 mt-1">@ {demoStats.avg_interest_rate}%</p>
        </div>
        <div className="bg-white rounded-lg border border-slate-200 p-4">
          <p className="text-xs text-slate-500 mb-1">EMI Collected</p>
          <p className="text-lg font-bold text-emerald-600">₹{(demoStats.total_emis_collected / 100000).toFixed(1)}L</p>
          <p className="text-xs text-slate-400 mt-1">This period</p>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-lg border border-slate-200">
        <div className="px-4 py-3 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-800">Recent Activity</h3>
        </div>
        <div className="divide-y divide-slate-100">
          {[
            { action: 'New application received', customer: 'Rahul Sharma', amount: '₹8,50,000', time: '2 min ago', type: 'new' },
            { action: 'Loan approved', customer: 'Priya Patel', amount: '₹12,00,000', time: '15 min ago', type: 'approved' },
            { action: 'EMI received', customer: 'Amit Kumar', amount: '₹25,500', time: '1 hour ago', type: 'payment' },
            { action: 'Document verified', customer: 'Sneha Gupta', amount: '₹5,00,000', time: '2 hours ago', type: 'verified' },
          ].map((item, idx) => (
            <div key={idx} className="px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <div className="flex items-center gap-3">
                <div className={clsx(
                  "w-2 h-2 rounded-full",
                  item.type === 'new' ? 'bg-blue-500' :
                  item.type === 'approved' ? 'bg-emerald-500' :
                  item.type === 'payment' ? 'bg-slate-400' : 'bg-slate-400'
                )} />
                <div>
                  <p className="text-sm font-medium text-slate-800">{item.action}</p>
                  <p className="text-xs text-slate-500">{item.customer} • {item.amount}</p>
                </div>
              </div>
              <span className="text-xs text-slate-400">{item.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Applications View Component
// ============================================================================

const ApplicationsView: React.FC<ViewProps> = ({ nbfcId, periodDays }) => {
  const { getApplications, updateApplicationStatus, loading, error } = useNBFCAPI(nbfcId);
  const [applications, setApplications] = useState<LoanApplication[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    const fetchApplications = async () => {
      try {
        const data = await getApplications(periodDays);
        setApplications(data);
      } catch (err) {
        console.error('Failed to fetch applications:', err);
      }
    };
    fetchApplications();
  }, [periodDays, nbfcId]);

  const demoApplications: LoanApplication[] = applications.length > 0 ? applications : [
    { id: 'APP-001', customer_name: 'Rahul Sharma', customer_phone: '98765XXXXX', amount_requested: 850000, tenure_months: 36, purpose: 'Home Renovation', credit_score: 745, monthly_income: 75000, status: 'pending', applied_date: '2024-01-15', risk_score: 35, documents_verified: true },
    { id: 'APP-002', customer_name: 'Priya Patel', customer_phone: '98765XXXXX', amount_requested: 1200000, tenure_months: 48, purpose: 'Business Expansion', credit_score: 720, monthly_income: 95000, status: 'under_review', applied_date: '2024-01-14', risk_score: 42, documents_verified: true },
    { id: 'APP-003', customer_name: 'Amit Kumar', customer_phone: '98765XXXXX', amount_requested: 500000, tenure_months: 24, purpose: 'Medical Emergency', credit_score: 680, monthly_income: 55000, status: 'approved', applied_date: '2024-01-13', risk_score: 55, documents_verified: true },
    { id: 'APP-004', customer_name: 'Sneha Gupta', customer_phone: '98765XXXXX', amount_requested: 750000, tenure_months: 36, purpose: 'Education', credit_score: 780, monthly_income: 80000, status: 'disbursed', applied_date: '2024-01-10', risk_score: 28, documents_verified: true },
    { id: 'APP-005', customer_name: 'Vikram Singh', customer_phone: '98765XXXXX', amount_requested: 2000000, tenure_months: 60, purpose: 'Property Purchase', credit_score: 620, monthly_income: 45000, status: 'rejected', applied_date: '2024-01-12', risk_score: 78, documents_verified: false },
  ];

  const filteredApps = filterStatus === 'all'
    ? demoApplications
    : demoApplications.filter(a => a.status === filterStatus);

  const handleApprove = async (appId: string) => {
    try {
      await updateApplicationStatus(appId, 'approved');
      setApplications(apps => apps.map(a => a.id === appId ? { ...a, status: 'approved' } : a));
    } catch (err) {
      console.error('Failed to approve:', err);
    }
  };

  const handleReject = async (appId: string) => {
    try {
      await updateApplicationStatus(appId, 'rejected');
      setApplications(apps => apps.map(a => a.id === appId ? { ...a, status: 'rejected' } : a));
    } catch (err) {
      console.error('Failed to reject:', err);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-800">Loan Applications</h2>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="text-sm px-3 py-1.5 bg-white border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-slate-200"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="under_review">Under Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="disbursed">Disbursed</option>
        </select>
      </div>

      {loading && <p className="text-slate-500 text-sm">Loading applications...</p>}
      {error && <p className="text-red-600 text-sm">{error}</p>}

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">ID</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Customer</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Amount</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Purpose</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Score</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-700">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredApps.map((app) => (
              <tr key={app.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 font-medium text-slate-900">{app.id}</td>
                <td className="px-4 py-3">
                  <div>
                    <p className="font-medium text-slate-800">{app.customer_name}</p>
                    <p className="text-xs text-slate-500">{app.customer_phone}</p>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <p className="font-medium text-slate-800">₹{app.amount_requested.toLocaleString()}</p>
                  <p className="text-xs text-slate-500">{app.tenure_months} months</p>
                </td>
                <td className="px-4 py-3 text-slate-600">{app.purpose}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={clsx(
                      "text-xs font-semibold",
                      app.credit_score >= 750 ? 'text-emerald-600' : app.credit_score >= 650 ? 'text-amber-600' : 'text-red-600'
                    )}>
                      {app.credit_score}
                    </span>
                    <span className="text-xs text-slate-400">|</span>
                    <span className={clsx(
                      "text-xs",
                      app.risk_score && app.risk_score < 40 ? 'text-emerald-600' : app.risk_score && app.risk_score < 60 ? 'text-amber-600' : 'text-red-600'
                    )}>
                      R{app.risk_score}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={app.status} />
                </td>
                <td className="px-4 py-3">
                  {(app.status === 'pending' || app.status === 'under_review') && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(app.id)}
                        className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded text-xs font-medium hover:bg-emerald-200 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReject(app.id)}
                        className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium hover:bg-red-200 transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  )}
                  {app.status === 'approved' && (
                    <button className="px-2 py-1 bg-slate-100 text-slate-700 rounded text-xs font-medium hover:bg-slate-200 transition-colors">
                      Disburse
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================================
// Products View Component
// ============================================================================

const ProductsView: React.FC<{ nbfcId: string }> = () => {
  const [products, setProducts] = useState<LoanProduct[]>([
    { id: 'PROD-001', name: 'Personal Loan - Standard', type: 'personal', min_amount: 50000, max_amount: 2000000, min_tenure: 12, max_tenure: 60, interest_rate_min: 12, interest_rate_max: 18, processing_fee_percent: 2, prepayment_charges: 4, is_active: true, created_at: '2023-06-01' },
    { id: 'PROD-002', name: 'Business Loan - SME', type: 'business', min_amount: 200000, max_amount: 10000000, min_tenure: 24, max_tenure: 84, interest_rate_min: 14, interest_rate_max: 20, processing_fee_percent: 2.5, prepayment_charges: 3, is_active: true, created_at: '2023-07-15' },
    { id: 'PROD-003', name: 'Education Loan', type: 'education', min_amount: 100000, max_amount: 5000000, min_tenure: 12, max_tenure: 120, interest_rate_min: 10, interest_rate_max: 14, processing_fee_percent: 1, prepayment_charges: 0, is_active: true, created_at: '2023-08-01' },
    { id: 'PROD-004', name: 'Home Improvement', type: 'home', min_amount: 300000, max_amount: 5000000, min_tenure: 24, max_tenure: 180, interest_rate_min: 11, interest_rate_max: 16, processing_fee_percent: 1.5, prepayment_charges: 2, is_active: false, created_at: '2023-09-01' },
  ]);

  const toggleProductStatus = (prodId: string) => {
    setProducts(products.map(p => p.id === prodId ? { ...p, is_active: !p.is_active } : p));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-800">Loan Products</h2>
        <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 text-white rounded-md text-sm font-medium hover:bg-slate-700 transition-colors">
          <ClipboardList size={16} />
          Add Product
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {products.map((product) => (
          <div key={product.id} className="bg-white rounded-lg border border-slate-200 p-4 hover:border-slate-300 transition-colors">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-slate-800">{product.name}</h3>
                <span className="inline-block mt-1 px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded capitalize">
                  {product.type} Loan
                </span>
              </div>
              <StatusBadge status={product.is_active ? 'active' : 'closed'} />
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
              <div>
                <p className="text-xs text-slate-500">Loan Amount</p>
                <p className="font-medium text-slate-800">
                  ₹{(product.min_amount / 100000).toFixed(0)}L - ₹{(product.max_amount / 100000).toFixed(0)}L
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Tenure</p>
                <p className="font-medium text-slate-800">{product.min_tenure} - {product.max_tenure} mo</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Interest Rate</p>
                <p className="font-medium text-slate-800">{product.interest_rate_min}% - {product.interest_rate_max}%</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Processing Fee</p>
                <p className="font-medium text-slate-800">{product.processing_fee_percent}%</p>
              </div>
            </div>

            <div className="flex gap-2">
              <button className="flex-1 px-3 py-1.5 bg-slate-100 text-slate-700 rounded text-sm font-medium hover:bg-slate-200 transition-colors">
                Edit
              </button>
              <button
                onClick={() => toggleProductStatus(product.id)}
                className={clsx(
                  "flex-1 px-3 py-1.5 rounded text-sm font-medium transition-colors",
                  product.is_active
                    ? 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                    : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                )}
              >
                {product.is_active ? 'Deactivate' : 'Activate'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// Performance View Component
// ============================================================================

const PerformanceView: React.FC<ViewProps> = () => {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-slate-800">Performance Analytics</h2>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard label="App Volume" value="↑ 12%" icon={<TrendingUp size={18} />} trend="vs last period" trendUp />
        <MetricCard label="Approval Rate" value="57.1%" icon={<CheckCircle2 size={18} />} trend="Industry: 52%" trendUp />
        <MetricCard label="Processing Time" value="2.3 days" icon={<Clock size={18} />} trend="↓ 0.5 days" trendUp />
        <MetricCard label="Customer Rating" value="4.6/5" icon={<User size={18} />} trend="128 reviews" />
      </div>

      <div className="bg-white rounded-lg border border-slate-200">
        <div className="px-4 py-3 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-800">Conversion Funnel</h3>
        </div>
        <div className="p-4 space-y-3">
          {[
            { label: 'Applications Received', value: 156, percentage: 100 },
            { label: 'Documents Verified', value: 134, percentage: 86 },
            { label: 'Credit Approved', value: 89, percentage: 57 },
            { label: 'Disbursed', value: 67, percentage: 43 },
          ].map((stage) => (
            <div key={stage.label}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-sm font-medium text-slate-700">{stage.label}</span>
                <div className="text-right">
                  <span className="text-sm font-bold text-slate-800">{stage.value}</span>
                  <span className="text-xs text-slate-500 ml-2">({stage.percentage}%)</span>
                </div>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-2">
                <div
                  className="bg-slate-600 h-2 rounded-full transition-all"
                  style={{ width: `${stage.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200">
        <div className="px-4 py-3 border-b border-slate-100">
          <h3 className="text-sm font-bold text-slate-800">Monthly Trends</h3>
        </div>
        <div className="divide-y divide-slate-100">
          {[
            { month: 'January 2024', applications: 45, approved: 28, disbursed: 22, amount: '₹1.4Cr' },
            { month: 'December 2023', applications: 52, approved: 35, disbursed: 30, amount: '₹1.9Cr' },
            { month: 'November 2023', applications: 38, approved: 22, disbursed: 18, amount: '₹1.1Cr' },
            { month: 'October 2023', applications: 41, approved: 25, disbursed: 20, amount: '₹1.3Cr' },
          ].map((month) => (
            <div key={month.month} className="px-4 py-3 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <span className="text-sm font-medium text-slate-700 w-28">{month.month}</span>
              <div className="flex gap-6 flex-1 justify-center">
                <div className="text-center">
                  <p className="text-xs text-slate-500">Apps</p>
                  <p className="text-sm font-bold text-slate-800">{month.applications}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500">Approved</p>
                  <p className="text-sm font-bold text-emerald-600">{month.approved}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-500">Disbursed</p>
                  <p className="text-sm font-bold text-slate-800">{month.disbursed}</p>
                </div>
              </div>
              <span className="text-sm font-bold text-slate-800 w-20 text-right">{month.amount}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Main NBFC Dashboard Component
// ============================================================================

const NBFCDashboard: React.FC<NBFCDashboardProps> = ({
  nbfcId = 'nbfc-001',
  nbfcName = 'BAJAJ FINSERVE',
  userRole = 'manager',
  onLogout,
}) => {
  const [activeView, setActiveView] = useState<NBFCView>('overview');
  const [selectedPeriodDays, setSelectedPeriodDays] = useState(30);
  const { healthCheck, error: apiError, clearError } = useNBFCAPI(nbfcId);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await healthCheck();
      } catch (err) {
        console.error('NBFC API health check failed:', err);
      }
    };
    checkHealth();
  }, []);

  const navigationItems = [
    { id: 'overview' as NBFCView, label: 'Overview', icon: LayoutDashboard, requires: ['manager', 'underwriter', 'viewer'] },
    { id: 'applications' as NBFCView, label: 'Applications', icon: FileText, requires: ['manager', 'underwriter', 'viewer'] },
    { id: 'products' as NBFCView, label: 'Products', icon: Wallet, requires: ['manager'] },
    { id: 'performance' as NBFCView, label: 'Performance', icon: TrendingUp, requires: ['manager', 'underwriter'] },
  ];

  const canAccessView = (itemId: NBFCView) => {
    const item = navigationItems.find((i) => i.id === itemId);
    return item?.requires.includes(userRole) || false;
  };

  return (
    <div className="w-full h-screen flex overflow-hidden font-sans bg-slate-50 text-slate-900">
      {/* Sidebar - Matching DashboardPane style */}
      <div className="w-72 border-r border-slate-200 bg-slate-50 flex flex-col h-screen z-10 overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center text-white">
              <Landmark size={20} />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-800 leading-tight">{nbfcName}</h1>
              <p className="text-xs text-slate-500">Partner Dashboard</p>
            </div>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 min-h-0 overflow-y-auto scrollbar-hide p-4">
          {/* Period Selector */}
          <div className="mb-4">
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 block">Period</label>
            <div className="relative">
              <Calendar size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <select
                value={selectedPeriodDays}
                onChange={(e) => setSelectedPeriodDays(Number(e.target.value))}
                className="w-full pl-8 pr-8 py-2 bg-white border border-slate-200 rounded-md text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-200 appearance-none"
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
                <option value={60}>Last 60 days</option>
                <option value={90}>Last 90 days</option>
                <option value={180}>Last 6 months</option>
                <option value={365}>Last year</option>
              </select>
              <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
          </div>

          {/* Navigation */}
          <nav className="space-y-1">
            {navigationItems.map((item) => {
              const Icon = item.icon;
              const hasAccess = canAccessView(item.id);
              const isActive = activeView === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => hasAccess && setActiveView(item.id)}
                  disabled={!hasAccess}
                  className={clsx(
                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                    isActive
                      ? 'bg-slate-800 text-white'
                      : hasAccess
                        ? 'text-slate-700 hover:bg-slate-100'
                        : 'text-slate-400 cursor-not-allowed'
                  )}
                >
                  <Icon size={18} className={isActive ? 'text-white' : hasAccess ? 'text-slate-500' : 'text-slate-400'} />
                  <span>{item.label}</span>
                  {!hasAccess && <Lock size={14} className="ml-auto" />}
                </button>
              );
            })}
          </nav>

          {/* Tip Box */}
          <div className="mt-6 p-3 bg-slate-100 rounded-lg border border-slate-200">
            <div className="flex items-start gap-2">
              <Lightbulb size={14} className="text-slate-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-slate-600 leading-relaxed">
                Review pending applications daily to improve conversion rates.
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-slate-200 rounded-full flex items-center justify-center">
                <User size={14} className="text-slate-600" />
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-700 capitalize">{userRole}</p>
                <p className="text-[10px] text-slate-500">ID: {nbfcId}</p>
              </div>
            </div>
          </div>
          <button
            onClick={onLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md text-sm font-medium transition-colors"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        <main className="p-6 max-w-6xl">
          {/* Error Alert */}
          {apiError && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle size={18} className="text-red-500 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold text-red-900 text-sm">API Error</p>
                <p className="text-red-700 text-xs mt-1">{apiError}</p>
              </div>
              <button
                onClick={clearError}
                className="text-red-500 hover:text-red-700"
              >
                <XCircle size={18} />
              </button>
            </div>
          )}

          {/* View Components */}
          {activeView === 'overview' && <OverviewView nbfcId={nbfcId} periodDays={selectedPeriodDays} />}
          {activeView === 'applications' && <ApplicationsView nbfcId={nbfcId} periodDays={selectedPeriodDays} />}
          {activeView === 'products' && canAccessView('products') && <ProductsView nbfcId={nbfcId} />}
          {activeView === 'performance' && canAccessView('performance') && <PerformanceView nbfcId={nbfcId} periodDays={selectedPeriodDays} />}

          {/* Restricted Access */}
          {!canAccessView(activeView) && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-6 text-center">
              <Lock size={24} className="mx-auto mb-2 text-amber-500" />
              <p className="text-amber-800 font-semibold text-sm">Access Restricted</p>
              <p className="text-amber-700 text-xs mt-1">
                Your {userRole} role doesn't have access to this section.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default NBFCDashboard;

