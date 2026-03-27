/**
 * Admin API type definitions - TypeScript models for admin dashboard
 */

// KPI Metrics
export interface KPIMetrics {
  total_loans_compared: number;
  total_unique_users: number;
  conversions: number;
  conversion_rate: number;
  avg_emi: number;
  avg_interest_rate: number;
  avg_approval_probability: number;
  total_cost_savings: number;
  processed_at: string;
}

// Conversion Funnel
export interface ConversionFunnelData {
  total_views: number;
  total_comparisons: number;
  total_selections: number;
  view_to_compare: number;
  compare_to_select: number;
  overall_conversion: number;
}

// Admin Overview Response
export interface AdminStatsOverviewResponse {
  kpis: KPIMetrics;
  funnel: ConversionFunnelData;
  period_days: number;
  timestamp: string;
}

// Lender Performance
export interface LenderPerformanceData {
  lender_id: string;
  lender_name: string;
  selections: number;
  selection_rate: number;
  avg_emi_offered: number;
  avg_rate: number;
  avg_approval_prob: number;
  market_share: number;
  trend: 'up' | 'down' | 'stable';
}

// Lenders List Response
export interface LendersListResponse {
  lenders: LenderPerformanceData[];
  total_count: number;
  active_count: number;
  timestamp: string;
}

// Lender Info Request/Response
export interface LenderInfoRequest {
  name: string;
  type: string;
  min_loan_amount: number;
  max_loan_amount: number;
  min_tenure: number;
  max_tenure: number;
  interest_rate_min: number;
  interest_rate_max: number;
  processing_fee: number;
  approval_probability: number;
  is_active: boolean;
}

export interface LenderInfoResponse extends LenderInfoRequest {
  id: string;
  created_at: string;
  updated_at: string;
}

// Trends Data
export interface TrendData {
  dates: string[];
  loans_compared: number[];
  conversions: number[];
  avg_emi: number[];
  avg_rate: number[];
  avg_approval: number[];
  cost_savings: number[];
}

// Admin Trends Response
export interface AdminTrendsResponse {
  trends: TrendData;
  period_days: number;
  summary: {
    total_loans: number;
    total_conversions: number;
    avg_daily_loans: number;
    avg_daily_conversions: number;
    peak_day_loans: number;
    peak_day_loans_date: string;
  };
  timestamp: string;
}

// Efficiency Score
export interface EfficiencyScore {
  lender_id: string;
  lender_name: string;
  efficiency_score: number;
  emi_score: number;
  rate_score: number;
  approval_score: number;
}

// Performance Metrics Response
export interface PerformanceMetricsResponse {
  period_days: number;
  kpis: KPIMetrics;
  lender_performance: LenderPerformanceData[];
  efficiency_scores: EfficiencyScore[];
  top_performers: string[];
  timestamp: string;
}

// Report Generation
export interface ReportRequest {
  report_type: 'daily' | 'weekly' | 'monthly';
  export_format: 'json' | 'csv' | 'pdf';
  email_to?: string;
}

export interface ReportResponse {
  report_id: string;
  report_type: string;
  period: string;
  url: string;
  created_at: string;
  expires_at: string;
}

// User Profile Stats
export interface UserProfileStats {
  avg_loan_amount: number;
  avg_tenure: number;
  avg_salary: number;
  avg_credit_score: number;
  avg_obligations: number;
  avg_age: number;
}

// Admin Health Response
export interface AdminHealthResponse {
  status: string;
  timestamp: string;
  version: string;
  authenticated: boolean;
}

// Conversion Funnel Details
export interface ConversionFunnelMetrics {
  total_views: number;
  total_comparisons: number;
  total_selections: number;
  view_to_compare_rate: number;
  compare_to_select_rate: number;
  overall_conversion_rate: number;
  details: {
    view_to_compare_count: number;
    dropped_at_compare: number;
    compare_to_select_count: number;
    dropped_at_select: number;
  };
}

// Loan Analytics Response
export interface LoanAnalyticsResponse {
  trends: TrendData;
  user_profile_stats: UserProfileStats;
  period_days: number;
}

// System Info
export interface SystemInfoResponse {
  status: string;
  version: string;
  marketplace_version: string;
  features: string[];
  total_lenders: number;
  active_lenders: number;
  timestamp: string;
}

// Admin Component State
export interface AdminDashboardState {
  loading: boolean;
  error: string | null;
  overview: AdminStatsOverviewResponse | null;
  lenders: LendersListResponse | null;
  performance: PerformanceMetricsResponse | null;
  trends: AdminTrendsResponse | null;
  selectedPeriodDays: number;
}
