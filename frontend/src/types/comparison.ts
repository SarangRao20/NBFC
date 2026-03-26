/**
 * Comparison API Types
 * Matches backend api/schemas/comparison.py models
 */

export interface LoanOffer {
  lender_id: string;
  lender_name: string;
  lender_type: string;
  interest_rate: number;
  emi: number;
  total_cost: number;
  approval_probability: number;
  approval_percentage: number;
  composite_score: number;
  rank_badge: string;
  recommendation_rank: number;
}

export interface GetLoansResponse {
  status: 'success' | 'no_eligible_offers';
  eligible_count: number;
  ineligible_count: number;
  eligible_offers: LoanOffer[];
  best_offer: LoanOffer | null;
  alternatives: LoanOffer[];
  recommendation_reason: string;
  smart_suggestions: string[];
  applied_weights: {
    emi_factor: number;
    approval_factor: number;
    cost_factor: number;
  };
}

export interface SelectLoanRequest {
  session_id?: string;
  selected_lender_id: string;
}

export interface SelectLoanResponse {
  success: boolean;
  message: string;
  selected_lender: string;
  selected_interest_rate: number;
  selected_emi: number;
  next_step: string;
}

export interface GetLoansRequest {
  loan_amount: number;
  tenure_months: number;
  credit_score: number;
  monthly_salary: number;
  age?: number;
  existing_obligations?: number;
}

export interface WhatIfRequest {
  session_id: string;
  new_loan_amount?: number;
  new_tenure_months?: number;
}

export interface WhatIfResponse {
  original: Record<string, any>;
  simulated: Record<string, any>;
  differences: Record<string, any>;
}

export interface LendersInfo {
  count: number;
  lenders: Record<
    string,
    {
      name: string;
      type: string;
      jurisdiction: string;
      base_rate: number;
      min_loan_amount: number;
      max_loan_amount: number;
      approval_probability: number;
    }
  >;
}

export interface ComparisonState {
  loading: boolean;
  error: string | null;
  response: GetLoansResponse | null;
  selectedLender: string | null;
}
