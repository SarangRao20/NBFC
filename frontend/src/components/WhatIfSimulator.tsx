/**
 * WhatIfSimulator - Loan parameter variation simulator
 */

import React, { useState } from 'react';
import type { WhatIfResponse } from '../types/comparison';

interface WhatIfSimulatorProps {
  currentAmount: number;
  currentTenure: number;
  sessionId: string;
  onSimulate: (
    newAmount?: number,
    newTenure?: number
  ) => Promise<WhatIfResponse>;
  isLoading?: boolean;
  onClose?: () => void;
}

const WhatIfSimulator: React.FC<WhatIfSimulatorProps> = ({
  currentAmount,
  currentTenure,
  onSimulate,
  isLoading = false,
  onClose,
}) => {
  const [newAmount, setNewAmount] = useState(currentAmount);
  const [newTenure, setNewTenure] = useState(currentTenure);
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [simulating, setSimulating] = useState(false);

  const handleSimulate = async () => {
    try {
      setSimulating(true);
      setError(null);

      const response = await onSimulate(
        newAmount !== currentAmount ? newAmount : undefined,
        newTenure !== currentTenure ? newTenure : undefined
      );

      setResult(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Simulation failed';
      setError(message);
    } finally {
      setSimulating(false);
    }
  };

  const amountChange = newAmount - currentAmount;
  const tenureChange = newTenure - currentTenure;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">💡 What-If Simulator</h2>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700"
          >
            ✕
          </button>
        )}
      </div>

      {/* Parameter Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-gray-50 p-6 rounded-lg">
        {/* Loan Amount */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Loan Amount
          </label>
          <div className="space-y-2">
            <input
              type="range"
              min="100000"
              max="5000000"
              step="50000"
              value={newAmount}
              onChange={(e) => setNewAmount(Number(e.target.value))}
              disabled={isLoading || simulating}
              className="w-full"
            />
            <div className="flex justify-between items-center">
              <span className="text-lg font-bold text-gray-900">
                ₹{newAmount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </span>
              <span
                className={`text-sm font-semibold ${
                  amountChange > 0 ? 'text-red-600' : amountChange < 0 ? 'text-green-600' : 'text-gray-600'
                }`}
              >
                {amountChange > 0 ? '+' : ''}{amountChange.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        </div>

        {/* Tenure */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Tenure (Months)
          </label>
          <div className="space-y-2">
            <input
              type="range"
              min="6"
              max="120"
              step="6"
              value={newTenure}
              onChange={(e) => setNewTenure(Number(e.target.value))}
              disabled={isLoading || simulating}
              className="w-full"
            />
            <div className="flex justify-between items-center">
              <span className="text-lg font-bold text-gray-900">{newTenure} months</span>
              <span
                className={`text-sm font-semibold ${
                  tenureChange > 0 ? 'text-red-600' : tenureChange < 0 ? 'text-green-600' : 'text-gray-600'
                }`}
              >
                {tenureChange > 0 ? '+' : ''}{tenureChange} months
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleSimulate}
          disabled={
            simulating || isLoading || (newAmount === currentAmount && newTenure === currentTenure)
          }
          className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {simulating ? 'Simulating...' : 'Run Simulation'}
        </button>
        {onClose && (
          <button
            onClick={onClose}
            className="px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 p-4 rounded-lg flex items-start gap-3">
          <span className="text-red-600 text-xl">⚠️</span>
          <div>
            <p className="font-semibold text-red-900">Simulation Failed</p>
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <h3 className="text-lg font-bold text-gray-900">Simulation Results</h3>

          {/* Comparison Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-gray-300">
                  <th className="text-left py-3 px-4 font-semibold text-gray-700">Parameter</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700">Original</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700">Simulated</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-700">Change</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="py-3 px-4 text-gray-900 font-semibold">Loan Amount</td>
                  <td className="py-3 px-4 text-right text-gray-700">
                    ₹{(result.original.loan_amount || 0).toLocaleString('en-IN')}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-700">
                    ₹{(result.simulated.loan_amount || 0).toLocaleString('en-IN')}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="font-semibold text-gray-700">
                      {result.simulated.loan_amount ? (
                        result.simulated.loan_amount > result.original.loan_amount ? (
                          <span className="text-red-600">+₹{((result.simulated.loan_amount || 0) - (result.original.loan_amount || 0)).toLocaleString('en-IN')}</span>
                        ) : (
                          <span className="text-green-600">-₹{((result.original.loan_amount || 0) - (result.simulated.loan_amount || 0)).toLocaleString('en-IN')}</span>
                        )
                      ) : (
                        '-'
                      )}
                    </span>
                  </td>
                </tr>
                <tr className="border-b border-gray-200 hover:bg-gray-50">
                  <td className="py-3 px-4 text-gray-900 font-semibold">Tenure</td>
                  <td className="py-3 px-4 text-right text-gray-700">{result.original.tenure_months} months</td>
                  <td className="py-3 px-4 text-right text-gray-700">{result.simulated.tenure_months} months</td>
                  <td className="py-3 px-4 text-right">
                    <span className="font-semibold text-gray-700">
                      {result.simulated.tenure_months > result.original.tenure_months ? (
                        <span className="text-red-600">+{result.simulated.tenure_months - result.original.tenure_months} months</span>
                      ) : (
                        <span className="text-green-600">-{result.original.tenure_months - result.simulated.tenure_months} months</span>
                      )}
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-gray-50">
                  <td className="py-3 px-4 text-gray-900 font-semibold">EMI</td>
                  <td className="py-3 px-4 text-right text-gray-700">₹{(result.original.emi || 0).toLocaleString('en-IN')}</td>
                  <td className="py-3 px-4 text-right text-gray-700">₹{(result.simulated.emi || 0).toLocaleString('en-IN')}</td>
                  <td className="py-3 px-4 text-right">
                    <span className="font-semibold text-gray-700">
                      {result.differences.emi_change ? (
                        result.differences.emi_change > 0 ? (
                          <span className="text-red-600">+₹{result.differences.emi_change.toLocaleString('en-IN')}</span>
                        ) : (
                          <span className="text-green-600">-₹{Math.abs(result.differences.emi_change).toLocaleString('en-IN')}</span>
                        )
                      ) : (
                        '-'
                      )}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Summary */}
          {result.differences.interest_savings !== undefined && (
            <div className="bg-green-50 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Interest Savings</p>
              <p className="text-2xl font-bold text-green-600">
                ₹{Math.abs(result.differences.interest_savings || 0).toLocaleString('en-IN')}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default WhatIfSimulator;
