/**
 * ReportsPanel - Generate and view reports
 */

import React, { useState } from 'react';
import useAdminAPI from '../hooks/useAdminAPI';

interface ReportsPanelProps {}

const ReportsPanel: React.FC<ReportsPanelProps> = () => {
  const { generateReport, loading, error } = useAdminAPI();
  const [reportType, setReportType] = useState('performance');
  const [dateRange, setDateRange] = useState({ from: '', to: '' });
  const [generatedReport, setGeneratedReport] = useState<any>(null);

  const reportTypes = [
    { id: 'performance', name: '📊 Performance Report', description: 'System and agent performance metrics' },
    { id: 'conversion', name: '📈 Conversion Report', description: 'User conversion and funnel analysis' },
    { id: 'lender', name: '🏦 Lender Report', description: 'Lender performance and market share' },
    { id: 'fraud', name: '🛡️ Fraud Report', description: 'Fraud detection and prevention metrics' },
    { id: 'kyc', name: '🆔 KYC Report', description: 'KYC processing and verification stats' },
  ];

  const handleGenerateReport = async () => {
    if (!dateRange.from || !dateRange.to) {
      alert('Please select date range');
      return;
    }

    try {
      const report = await generateReport({
        report_type: reportType,
        start_date: dateRange.from,
        end_date: dateRange.to,
      });
      setGeneratedReport(report);
    } catch (err) {
      console.error('Failed to generate report:', err);
    }
  };

  return (
    <div className="space-y-8">
      <h2 className="text-2xl font-bold text-gray-900">📋 Reports & Analytics</h2>

      {/* Report Generation */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-6">Generate New Report</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Report Type Selection */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              Report Type
            </label>
            <div className="space-y-2">
              {reportTypes.map((type) => (
                <label key={type.id} className="flex items-center p-3 border rounded-lg cursor-pointer hover:bg-blue-50 transition-colors">
                  <input
                    type="radio"
                    name="reportType"
                    value={type.id}
                    checked={reportType === type.id}
                    onChange={(e) => setReportType(e.target.value)}
                    className="w-4 h-4 text-blue-600"
                  />
                  <div className="ml-3">
                    <p className="font-semibold text-gray-900">{type.name}</p>
                    <p className="text-xs text-gray-600">{type.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Date Range */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                From Date
              </label>
              <input
                type="date"
                value={dateRange.from}
                onChange={(e) => setDateRange({ ...dateRange, from: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                To Date
              </label>
              <input
                type="date"
                value={dateRange.to}
                onChange={(e) => setDateRange({ ...dateRange, to: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent"
              />
            </div>
            <button
              onClick={handleGenerateReport}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-2 rounded-lg font-semibold transition-colors"
            >
              {loading ? 'Generating...' : 'Generate Report'}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-900">
            Failed to generate report: {error}
          </div>
        )}
      </div>

      {/* Generated Report Display */}
      {generatedReport && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-bold text-gray-900">Report: {generatedReport.title}</h3>
            <div className="flex gap-3">
              <button className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-semibold">
                📥 Download PDF
              </button>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold">
                📧 Email Report
              </button>
            </div>
          </div>

          <div className="space-y-6">
            {generatedReport.sections.map((section: any, idx: number) => (
              <div key={idx} className="border-b border-gray-200 pb-6">
                <h4 className="text-md font-bold text-gray-900 mb-4">{section.title}</h4>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-gray-700 text-sm whitespace-pre-wrap">{section.content}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-xs text-gray-600">
              Generated at {new Date(generatedReport.generated_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}

      {/* Predefined Reports */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-6">Recent Reports</h3>
        <div className="space-y-3">
          {[
            { name: 'Weekly Performance Report', date: '2024-01-15', size: '2.4 MB' },
            { name: 'Monthly Conversion Analysis', date: '2024-01-10', size: '1.8 MB' },
            { name: 'Lender Performance Metrics', date: '2024-01-05', size: '3.1 MB' },
          ].map((report, idx) => (
            <div key={idx} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
              <div>
                <p className="font-semibold text-gray-900">{report.name}</p>
                <p className="text-xs text-gray-600">{report.date}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">{report.size}</span>
                <button className="text-blue-600 hover:text-blue-900">
                  ⬇️ Download
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ReportsPanel;
