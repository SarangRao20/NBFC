/**
 * LoanComparisonTable - Sortable table view of all loan offers
 * Allows users to compare loans side-by-side with sorting capabilities
 */

import React, { useState } from 'react';
import type { LoanOffer } from '../types/comparison';

interface LoanComparisonTableProps {
  loans: LoanOffer[];
  selectedLenderId?: string;
  onSelect: (lender_id: string) => void;
  isLoading?: boolean;
}

type SortKey = 'interest_rate' | 'emi' | 'total_cost' | 'approval_percentage' | 'composite_score';
type SortOrder = 'asc' | 'desc';

const LoanComparisonTable: React.FC<LoanComparisonTableProps> = ({
  loans,
  selectedLenderId,
  onSelect,
  isLoading = false,
}) => {
  const [sortKey, setSortKey] = useState<SortKey>('composite_score');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  // Handle sort
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('desc');
    }
  };

  // Sort loans
  const sortedLoans = [...loans].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];

    let comparison = 0;
    if (typeof aVal === 'number' && typeof bVal === 'number') {
      comparison = aVal - bVal;
    } else {
      comparison = String(aVal).localeCompare(String(bVal));
    }

    return sortOrder === 'asc' ? comparison : -comparison;
  });

  // Sort indicator
  const SortIndicator: React.FC<{ column: SortKey }> = ({ column }) => {
    if (sortKey !== column) return null;
    return <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>;
  };

  // Header button style
  const headerButtonClass =
    'px-2 py-1 text-left text-xs font-semibold text-gray-700 hover:bg-gray-100 cursor-pointer transition-colors rounded';
  const headerCellClass = 'px-4 py-3 text-left border-b border-gray-200';

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full">
        {/* Header */}
        <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
          <tr>
            <th className={headerCellClass}>
              <div className="text-xs font-semibold text-gray-700">Lender</div>
            </th>
            <th className={headerCellClass}>
              <button
                className={headerButtonClass}
                onClick={() => handleSort('interest_rate')}
              >
                Interest Rate <SortIndicator column="interest_rate" />
              </button>
            </th>
            <th className={headerCellClass}>
              <button
                className={headerButtonClass}
                onClick={() => handleSort('emi')}
              >
                Monthly EMI <SortIndicator column="emi" />
              </button>
            </th>
            <th className={headerCellClass}>
              <button
                className={headerButtonClass}
                onClick={() => handleSort('total_cost')}
              >
                Total Cost <SortIndicator column="total_cost" />
              </button>
            </th>
            <th className={headerCellClass}>
              <button
                className={headerButtonClass}
                onClick={() => handleSort('approval_percentage')}
              >
                Approval % <SortIndicator column="approval_percentage" />
              </button>
            </th>
            <th className={headerCellClass}>
              <button
                className={headerButtonClass}
                onClick={() => handleSort('composite_score')}
              >
                Score <SortIndicator column="composite_score" />
              </button>
            </th>
            <th className={headerCellClass}>
              <div className="text-xs font-semibold text-gray-700">Action</div>
            </th>
          </tr>
        </thead>

        {/* Body */}
        <tbody className="divide-y divide-gray-200">
          {sortedLoans.length === 0 ? (
            <tr>
              <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                No loans to display
              </td>
            </tr>
          ) : (
            sortedLoans.map((loan) => (
              <tr
                key={loan.lender_id}
                className={`
                  transition-colors
                  ${
                    selectedLenderId === loan.lender_id
                      ? 'bg-blue-50 border-l-4 border-l-blue-500'
                      : 'hover:bg-gray-50'
                  }
                  ${isLoading ? 'opacity-60' : ''}
                `}
              >
                {/* Lender Name */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div>
                      <div className="font-semibold text-gray-900">{loan.lender_name}</div>
                      <div className="text-xs text-gray-500 capitalize">{loan.lender_type}</div>
                    </div>
                    {loan.rank_badge && (
                      <span className="text-lg" title="Rank">
                        {loan.rank_badge}
                      </span>
                    )}
                  </div>
                </td>

                {/* Interest Rate */}
                <td className="px-4 py-3">
                  <span className="font-semibold text-gray-900">
                    {loan.interest_rate.toFixed(2)}%
                  </span>
                </td>

                {/* EMI */}
                <td className="px-4 py-3">
                  <span className="font-semibold text-blue-600">
                    ₹{loan.emi.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </td>

                {/* Total Cost */}
                <td className="px-4 py-3">
                  <span className="text-gray-900">
                    ₹{loan.total_cost.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </td>

                {/* Approval % */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-green-600">
                      {loan.approval_percentage.toFixed(0)}%
                    </span>
                    <div className="w-16 h-2 bg-gray-200 rounded-full">
                      <div
                        className="h-2 bg-gradient-to-r from-green-400 to-green-600 rounded-full"
                        style={{ width: `${Math.min(loan.approval_percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                </td>

                {/* Score */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900">
                      {loan.composite_score.toFixed(1)}/100
                    </span>
                    <div className="w-16 h-2 bg-gray-200 rounded-full">
                      <div
                        className="h-2 bg-gradient-to-r from-blue-400 to-blue-600 rounded-full"
                        style={{ width: `${Math.min(loan.composite_score, 100)}%` }}
                      />
                    </div>
                  </div>
                </td>

                {/* Select Button */}
                <td className="px-4 py-3">
                  <button
                    onClick={() => onSelect(loan.lender_id)}
                    disabled={isLoading}
                    className={`
                      px-3 py-1 rounded font-semibold text-sm transition-all
                      ${
                        selectedLenderId === loan.lender_id
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }
                      ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                    `}
                  >
                    {selectedLenderId === loan.lender_id ? '✓ Selected' : 'Select'}
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default LoanComparisonTable;
