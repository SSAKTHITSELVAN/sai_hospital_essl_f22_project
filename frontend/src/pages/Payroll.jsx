// frontend/src/pages/Payroll.jsx
import React, { useState } from 'react';
import api from '../services/api';
import { DollarSign, Download, Search, Calendar } from 'lucide-react';

export default function Payroll() {
  const [uid, setUid] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const generateReport = async () => {
    if (!uid || !startDate || !endDate) {
      alert('Please fill all fields');
      return;
    }

    try {
      setLoading(true);
      const response = await api.get(
        `/api/v1/payroll/detailed-report/${uid}?start_date=${startDate}&end_date=${endDate}`
      );
      if (response.data.status === 'success') {
        setReport(response.data.data);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Failed to generate report');
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Payroll Reports</h1>
          <p className="text-gray-600 mt-1">Generate detailed payroll reports</p>
        </div>
      </div>

      {/* Report Generator */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Generate Report</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Employee UID
            </label>
            <input
              type="number"
              value={uid}
              onChange={(e) => setUid(e.target.value)}
              placeholder="Enter UID"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={generateReport}
              disabled={loading}
              className="w-full bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Generate'}
            </button>
          </div>
        </div>
      </div>

      {/* Report Display */}
      {report && (
        <div className="space-y-6">
          {/* Employee Info */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-gray-800">{report.user.name}</h3>
                <p className="text-gray-600">UID: {report.user.uid}</p>
              </div>
              <button className="flex items-center space-x-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
                <Download className="w-5 h-5" />
                <span>Export PDF</span>
              </button>
            </div>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <p className="text-gray-500 text-sm mb-1">Days Worked</p>
              <p className="text-3xl font-bold text-gray-800">{report.summary.total_worked_days}</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6">
              <p className="text-gray-500 text-sm mb-1">Total Hours</p>
              <p className="text-3xl font-bold text-green-600">{report.summary.total_hours_worked}h</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6">
              <p className="text-gray-500 text-sm mb-1">Overtime</p>
              <p className="text-3xl font-bold text-orange-600">{report.summary.overtime_hours}h</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6">
              <p className="text-gray-500 text-sm mb-1">Leaves</p>
              <p className="text-3xl font-bold text-red-600">{report.summary.leaves}</p>
            </div>
          </div>

          {/* Monthly Breakdown */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Monthly Breakdown</h3>
            {report.monthly_breakdown.map((month, index) => (
              <div key={index} className="border rounded-lg p-4 mb-4">
                <h4 className="font-semibold text-gray-800 mb-3">{month.month}</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Days Worked</p>
                    <p className="text-lg font-semibold">{month.total_days_worked}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Total Hours</p>
                    <p className="text-lg font-semibold">{month.total_hours}h</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Overtime</p>
                    <p className="text-lg font-semibold text-orange-600">{month.overtime_hours}h</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Leaves</p>
                    <p className="text-lg font-semibold text-red-600">{month.leaves}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Shift Analysis */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Shift Analysis</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(report.shift_analysis).map(([shift, data]) => (
                <div key={shift} className="border rounded-lg p-4">
                  <h4 className="font-semibold text-gray-800 mb-2">Shift {shift}</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Days:</span>
                      <span className="font-semibold">{data.total_days_worked}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Hours:</span>
                      <span className="font-semibold">{data.total_hours}h</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Late:</span>
                      <span className="font-semibold text-yellow-600">{data.late_days}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Attendance:</span>
                      <span className="font-semibold text-green-600">{data.attendance_rate}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}