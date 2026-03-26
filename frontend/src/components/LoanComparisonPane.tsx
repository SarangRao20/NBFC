/**
 * LoanComparisonPane - Main loan comparison interface
 * Integrates all comparison components and manages the flow
 */

import React, { useState, useEffect } from 'react';
import useComparisonAPI from '../hooks/useComparisonAPI';
import LoanComparisonResults from './LoanComparisonResults';
import WhatIfSimulator from './WhatIfSimulator';
import type { GetLoansRequest } from '../types/comparison';

interface LoanComparisonPaneProps {
  loanAmount: number;
  tenureMonths: number;
  creditScore: number;
  monthlySalary: number;
  age?: number;
  existingObligations?: number;
  onLoanSelected?: (lenderId: string, selectedData: any) => void;
  onComparingChanged?: (isComparing: boolean) => void;
}

type ViewMode = 'loading' | 'comparison' | 'what-if' | 'error';

const LoanComparisonPane: React.FC<LoanComparisonPaneProps> = ({
  loanAmount,
  tenureMonths,
  creditScore,
  monthlySalary,
  age = 35,
  existingObligations = 0,
  onLoanSelected,
  onComparingChanged,
}) => {
  const {
    loading,
    error,
    comparisonResult,
    runWhatIf,
    getLoans,
    selectLoan,
  } = useComparisonAPI();

  const [viewMode, setViewMode] = useState<ViewMode>('loading');
  const [sessionId, setSessionId] = useState<string>('');

  // Fetch loans on mount or when parameters change
  useEffect(() => {
    const fetchLoans = async () => {
      try {
        setViewMode('loading');
        onComparingChanged?.(true);

        const request: GetLoansRequest = {
          loan_amount: loanAmount,
          tenure_months: tenureMonths,
          credit_score: creditScore,
          monthly_salary: monthlySalary,
          age,
          existing_obligations: existingObligations,
        };

        await getLoans(request);
        const newSessionId = `session_${Date.now()}`;
        setSessionId(newSessionId);
        setViewMode('comparison');
      } catch (err) {
        setViewMode('error');
      } finally {
        onComparingChanged?.(false);
      }
    };

    fetchLoans();
  }, [loanAmount, tenureMonths, creditScore, monthlySalary, age, existingObligations]);

  const handleSelectLoan = async (lenderId: string) => {
    try {
      const response = await selectLoan({
        session_id: sessionId,
        selected_lender_id: lenderId,
      });

      if (response.success) {
        onLoanSelected?.(lenderId, {
          lenderName: response.selected_lender,
          interestRate: response.selected_interest_rate,
          emi: response.selected_emi,
          nextStep: response.next_step,
        });
      }
    } catch (err) {
      console.error('Failed to select loan:', err);
      throw err;
    }
  };

  const handleRunWhatIf = async (newAmount?: number, newTenure?: number) => {
    return runWhatIf({
      session_id: sessionId,
      new_loan_amount: newAmount,
      new_tenure_months: newTenure,
    });
  };

  // Loading State
  if (viewMode === 'loading') {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-700 font-semibold">Comparing loans from 5 lenders...</p>
          <p className="text-gray-500 text-sm mt-2">This takes just a moment</p>
        </div>
      </div>
    );
  }

  // Error State
  if (viewMode === 'error' || error) {
    return (
      <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-bold text-red-900 mb-2">Comparison Failed</h3>
        <p className="text-red-700 mb-4">{error || 'An unexpected error occurred'}</p>
        <button
          onClick={() => window.location.reload()}
          className="bg-red-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-red-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  // What-If View
  if (viewMode === 'what-if') {
    return (
      <WhatIfSimulator
        currentAmount={loanAmount}
        currentTenure={tenureMonths}
        sessionId={sessionId}
        onSimulate={handleRunWhatIf}
        isLoading={loading}
        onClose={() => setViewMode('comparison')}
      />
    );
  }

  // Comparison Results View
  if (comparisonResult) {
    return (
      <LoanComparisonResults
        result={comparisonResult}
        isLoading={loading}
        onSelectLoan={handleSelectLoan}
        onShowWhatIf={() => setViewMode('what-if')}
      />
    );
  }

  return null;
};

export default LoanComparisonPane;
