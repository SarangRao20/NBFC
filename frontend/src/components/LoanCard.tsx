/**
 * LoanCard - Individual loan offer display component
 */

import React from 'react';
import type { LoanOffer } from '../types/comparison';

interface LoanCardProps {
  loan: LoanOffer;
  isSelected: boolean;
  onSelect: (lender_id: string) => void;
  isBest?: boolean;
  isLoading?: boolean;
}

const LoanCard: React.FC<LoanCardProps> = ({
  loan,
  isSelected,
  onSelect,
  isBest = false,
  isLoading = false,
}) => {
  const handleSelect = () => {
    if (!isLoading) {
      onSelect(loan.lender_id);
    }
  };

  return (
    <div
      className={`
        relative rounded-lg border-2 transition-all duration-200 p-4
        ${
          isSelected
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-200 bg-white hover:border-gray-300'
        }
        ${isBest ? 'ring-2 ring-green-400' : ''}
        ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
      onClick={handleSelect}
    >
      {/* Badge */}
      <div className="absolute -top-3 -right-3 flex gap-2">
        <span className="text-2xl">{loan.rank_badge}</span>
        {isBest && (
          <span className="bg-green-500 text-white px-2 py-1 rounded-full text-xs font-bold">
            BEST
          </span>
        )}
      </div>

      {/* Header */}
      <div className="mb-4 pr-8">
        <h3 className="text-lg font-bold text-gray-900">{loan.lender_name}</h3>
        <p className="text-sm text-gray-500 capitalize">{loan.lender_type}</p>
      </div>

      {/* Main Metrics */}
      <div className="grid grid-cols-3 gap-4 mb-4 pb-4 border-b border-gray-200">
        <div>
          <p className="text-xs text-gray-600 mb-1">Interest Rate</p>
          <p className="text-2xl font-bold text-gray-900">{loan.interest_rate.toFixed(2)}%</p>
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-1">Monthly EMI</p>
          <p className="text-2xl font-bold text-blue-600">
            ₹{loan.emi.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-600 mb-1">Approval %</p>
          <p className="text-2xl font-bold text-green-600">{loan.approval_percentage.toFixed(0)}%</p>
        </div>
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gray-50 p-2 rounded">
          <p className="text-xs text-gray-600">Total Cost</p>
          <p className="font-semibold text-gray-900">
            ₹{loan.total_cost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        </div>
        <div className="bg-gray-50 p-2 rounded">
          <p className="text-xs text-gray-600">Score</p>
          <p className="font-semibold text-gray-900">{loan.composite_score.toFixed(1)}/100</p>
        </div>
      </div>

      {/* Score Bar */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-1">
          <span className="text-xs font-semibold text-gray-700">Recommendation Score</span>
          <span className="text-xs text-gray-600">{loan.composite_score.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full"
            style={{ width: `${Math.min(loan.composite_score, 100)}%` }}
          />
        </div>
      </div>

      {/* Selection Radio */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <input
          type="radio"
          id={`loan-${loan.lender_id}`}
          name="loan-selection"
          value={loan.lender_id}
          checked={isSelected}
          onChange={handleSelect}
          disabled={isLoading}
          className="w-4 h-4 text-blue-600"
        />
        <label htmlFor={`loan-${loan.lender_id}`} className="text-sm font-medium text-gray-700">
          Select this loan
        </label>
      </div>
    </div>
  );
};

export default LoanCard;
