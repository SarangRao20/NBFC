/**
 * LenderManagement - Manage lenders and their offers
 */

import React, { useState, useEffect } from 'react';
import useAdminAPI from '../hooks/useAdminAPI';
import { LendersListResponse, LenderPerformanceData } from '../../types/admin';

interface LenderManagementProps {}

const LenderManagement: React.FC<LenderManagementProps> = () => {
  const { listLenders, loading, error } = useAdminAPI();
  const [lenders, setLenders] = useState<LendersListResponse | null>(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    const fetchLenders = async () => {
      try {
        const data = await listLenders();
        setLenders(data);
      } catch (err) {
        console.error('Failed to fetch lenders:', err);
      }
    };

    fetchLenders();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-700 font-semibold">Loading lenders...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <p className="text-red-900 font-semibold">Failed to load lenders</p>
        <p className="text-red-700 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">🏦 Lender Management</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
        >
          {showForm ? 'Cancel' : '+ Add New Lender'}
        </button>
      </div>

      {/* Lenders Table */}
      {lenders && (
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          <div className="p-6 bg-gradient-to-r from-blue-50 to-blue-100 border-b border-blue-200">
            <h3 className="text-lg font-bold text-gray-900">
              Active Lenders ({lenders.active_count} of {lenders.total_count})
            </h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b-2 border-gray-300 bg-gray-50">
                  <th className="text-left py-3 px-6 font-semibold text-gray-700">Lender Name</th>
                  <th className="text-right py-3 px-6 font-semibold text-gray-700">Selections</th>
                  <th className="text-right py-3 px-6 font-semibold text-gray-700">Selection Rate</th>
                  <th className="text-right py-3 px-6 font-semibold text-gray-700">Avg EMI</th>
                  <th className="text-right py-3 px-6 font-semibold text-gray-700">Avg Rate</th>
                  <th className="text-right py-3 px-6 font-semibold text-gray-700">Approval %</th>
                  <th className="text-center py-3 px-6 font-semibold text-gray-700">Market Share</th>
                  <th className="text-center py-3 px-6 font-semibold text-gray-700">Trend</th>
                  <th className="text-center py-3 px-6 font-semibold text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {lenders.lenders.map((lender: LenderPerformanceData) => (
                  <tr key={lender.lender_id} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="py-4 px-6">
                      <div>
                        <p className="font-semibold text-gray-900">{lender.lender_name}</p>
                        <p className="text-xs text-gray-600 capitalize">{lender.lender_id}</p>
                      </div>
                    </td>
                    <td className="text-right py-4 px-6 font-semibold text-gray-900">
                      {lender.selections}
                    </td>
                    <td className="text-right py-4 px-6 text-gray-900">
                      {lender.selection_rate.toFixed(2)}%
                    </td>
                    <td className="text-right py-4 px-6 font-semibold text-gray-900">
                      ₹{lender.avg_emi_offered.toLocaleString()}
                    </td>
                    <td className="text-right py-4 px-6 font-semibold text-gray-900">
                      {lender.avg_rate.toFixed(2)}%
                    </td>
                    <td className="text-right py-4 px-6 font-semibold text-green-600">
                      {(lender.avg_approval_prob * 100).toFixed(0)}%
                    </td>
                    <td className="text-center py-4 px-6">
                      <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-semibold">
                        {lender.market_share.toFixed(1)}%
                      </span>
                    </td>
                    <td className="text-center py-4 px-6">
                      <span
                        className={`text-lg ${
                          lender.trend === 'up'
                            ? 'text-green-600'
                            : lender.trend === 'down'
                            ? 'text-red-600'
                            : 'text-gray-600'
                        }`}
                      >
                        {lender.trend === 'up' && '📈'}
                        {lender.trend === 'down' && '📉'}
                        {lender.trend === 'stable' && '➡️'}
                      </span>
                    </td>
                    <td className="text-center py-4 px-6">
                      <button className="text-blue-600 hover:text-blue-900 font-semibold text-sm">
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default LenderManagement;
