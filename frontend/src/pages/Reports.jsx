// frontend/src/pages/Reports.jsx
import React, { useState } from 'react';
import api from '../services/api';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { FileText, Download, TrendingUp } from 'lucide-react';

export default function Reports() {
  const [reportType, setReportType] = useState('attendance');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#6366f1', '#8b5cf6'];

  const generateStats = async () => {
    if (!startDate || !endDate) {
      alert('Please select date range');
      return;
    }

    try {
      setLoading(true);
      const response = await api.get(
        `/api/v1/attendance/stats?start_date=${startDate}&end_date=${endDate}`
      );
      if (response.data.status === 'success') {
        setStats(response.data.data);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching stats:', error);
      setLoading(false);
    }
  };

  const getChartData = () => {
    if (!stats) return [];
    
    return [
      { name: 'Present', value: stats.statistics.present, color: '#10b981' },
      { name: 'Late', value: stats.statistics.late, color: '#f59e0b' },
      { name: 'Early Leave', value: stats.statistics.early_leave, color: '#f97316' },
      { name: 'Incomplete', value: stats.statistics.incomplete, color: '#ef4444' },
      { name: 'Half Day', value: stats.statistics.half_day, color: '#6366f1' },
    ];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Reports & Analytics</h1>
          <p className="text-gray-600 mt-1">Visualize attendance and payroll data</p>
        </div>
        <button className="flex items-center space-x-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
          <Download className="w-5 h-5" />
          <span>Export Report</span>
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Report Type
            </label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option value="attendance">Attendance</option>
              <option value="payroll">Payroll</option>
              <option value="shift">Shift Analysis</option>
            </select>
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
              onClick={generateStats}
              disabled={loading}
              className="w-full bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Generate'}
            </button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm mb-1">Total Records</p>
                  <p className="text-3xl font-bold text-gray-800">{stats.statistics.total_records}</p>
                </div>
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <FileText className="w-6 h-6 text-blue-600" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm mb-1">Total Hours</p>
                  <p className="text-3xl font-bold text-green-600">{stats.statistics.total_work_hours}h</p>
                </div>
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm mb-1">Avg Hours/Day</p>
                  <p className="text-3xl font-bold text-indigo-600">{stats.statistics.average_work_hours}h</p>
                </div>
                <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <BarChart className="w-6 h-6 text-indigo-600" />
                </div>
              </div>
            </div>
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Pie Chart */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Attendance Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={getChartData()}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {getChartData().map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Bar Chart */}
            <div className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">Status Breakdown</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={getChartData()}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#6366f1">
                    {getChartData().map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Percentages */}
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Attendance Rates</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="border rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Present Rate</p>
                <div className="flex items-end space-x-2">
                  <p className="text-3xl font-bold text-green-600">{stats.percentages.present}%</p>
                  <p className="text-sm text-gray-500 mb-1">of total</p>
                </div>
              </div>
              <div className="border rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Late Rate</p>
                <div className="flex items-end space-x-2">
                  <p className="text-3xl font-bold text-yellow-600">{stats.percentages.late}%</p>
                  <p className="text-sm text-gray-500 mb-1">of total</p>
                </div>
              </div>
              <div className="border rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Incomplete Rate</p>
                <div className="flex items-end space-x-2">
                  <p className="text-3xl font-bold text-red-600">{stats.percentages.incomplete}%</p>
                  <p className="text-sm text-gray-500 mb-1">of total</p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* No Data State */}
      {!stats && !loading && (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg">Select date range and generate report to see analytics</p>
        </div>
      )}
    </div>
  );
}
