/**
 * LoanComparisonResults - Display loan comparison results and recommendations
 */

import React, { useState } from 'react';
import type { GetLoansResponse, LoanOffer } from '../types/comparison';
import LoanCard from './LoanCard';
import LoanComparisonTable from './LoanComparisonTable';

interface LoanComparisonResultsProps {
  result: GetLoansResponse;
  onSelectLoan: (lender_id: string) => Promise<void>;
  isLoading?: boolean;
  onShowWhatIf?: () => void;
}

type ViewMode = 'cards' | 'table';

const LoanComparisonResults: React.FC<LoanComparisonResultsProps> = ({
  result,
  onSelectLoan,
  onShowWhatIf,
}) => {
  const [selectedLender, setSelectedLender] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('cards');

  const handleSelectLoan = async (lender_id: string) => {
    try {
      setSelectedLender(lender_id);
      setSubmitting(true);
      setSubmitError(null);
      await onSelectLoan(lender_id);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to select loan';
      setSubmitError(message);
      setSelectedLender(null);
    } finally {
      setSubmitting(false);
    }
  };

  if (result.status === 'no_eligible_offers') {
    return (
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-6 rounded">
        <h3 className="text-lg font-bold text-yellow-900 mb-3">No Eligible Offers</h3>
        <p className="text-yellow-800 mb-4">
          Unfortunately, you don't meet the eligibility criteria for any lenders at this time.
        </p>

        {result.smart_suggestions.length > 0 && (
          <div>
            <h4 className="font-semibold text-yellow-900 mb-2">Suggestions to improve eligibility:</h4>
            <ul className="list-disc list-inside space-y-1">
              {result.smart_suggestions.map((suggestion: string, idx: number) => (
                <li key={idx} className="text-yellow-800 text-sm">
                  {suggestion}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 p-6 rounded-lg">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Loan Comparison Results</h2>
            <p className="text-gray-700 mb-3">{result.recommendation_reason}</p>
          </div>
          {/* View Toggle */}
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('cards')}
              className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
                viewMode === 'cards'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              📋 Cards
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
                viewMode === 'table'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              📊 Table
            </button>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(result.applied_weights).map(([key, value]: [string, any]) => (
            <span key={key} className="bg-white px-3 py-1 rounded text-sm text-gray-700">
              {key.replace(/_/g, ' ')}: {(value as number * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      </div>

      {/* Table View */}
      {viewMode === 'table' && result.eligible_offers.length > 0 && (
        <div>
          <LoanComparisonTable
            loans={result.eligible_offers}
            selectedLenderId={selectedLender || undefined}
            onSelect={handleSelectLoan}
            isLoading={submitting}
          />
        </div>
      )}

      {/* Card View */}
      {viewMode === 'cards' && (
        <>
          {/* Best Offer */}
          {result.best_offer && (
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                <span>🏆</span> Our Recommendation
              </h3>
              <LoanCard
                loan={result.best_offer}
                isSelected={selectedLender === result.best_offer.lender_id}
                onSelect={handleSelectLoan}
                isBest={true}
                isLoading={submitting}
              />
            </div>
          )}

          {/* Eligible Offers */}
          {result.eligible_offers.length > 1 && (
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-3">Other Eligible Options</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {result.eligible_offers.map((loan: LoanOffer) => {
                  if (result.best_offer && loan.lender_id === result.best_offer.lender_id) {
                    return null; // Already shown in recommendation
                  }
                  return (
                    <LoanCard
                      key={loan.lender_id}
                      loan={loan}
                      isSelected={selectedLender === loan.lender_id}
                      onSelect={handleSelectLoan}
                      isLoading={submitting}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* Alternatives Summary */}
          {result.alternatives.length > 0 && (
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">📊 Top Alternatives</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {result.alternatives.map((alt: any) => (
                  <div key={alt.lender_id} className="flex justify-between items-center bg-white p-3 rounded">
                    <div>
                      <p className="font-semibold text-gray-900">{alt.lender_name}</p>
                      <p className="text-sm text-gray-600">{alt.interest_rate.toFixed(2)}% • ₹{alt.emi.toLocaleString('en-IN')}</p>
                    </div>
                    <span className="text-lg">{alt.rank_badge}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Error Message */}
      {submitError && (
        <div className="bg-red-50 border border-red-200 p-4 rounded-lg flex items-start gap-3">
          <span className="text-red-600 text-xl">⚠️</span>
          <div>
            <p className="font-semibold text-red-900">Selection Error</p>
            <p className="text-red-700 text-sm">{submitError}</p>
          </div>
        </div>
      )}

      {/* Selection Status */}
      {submitting && (
        <div className="bg-blue-50 p-4 rounded-lg flex items-center gap-3">
          <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full"></div>
          <p className="text-blue-900 font-medium">Processing your selection...</p>
        </div>
      )}

      {/* What-If Button */}
      {onShowWhatIf && (
        <div className="flex justify-center">
          <button
            onClick={onShowWhatIf}
            className="bg-white border-2 border-gray-300 text-gray-700 px-6 py-2 rounded-lg font-semibold hover:border-gray-400 hover:bg-gray-50 transition-colors"
          >
            💡 Try What-If Simulation
          </button>
        </div>
      )}
    </div>
  );
};

export default LoanComparisonResults;
