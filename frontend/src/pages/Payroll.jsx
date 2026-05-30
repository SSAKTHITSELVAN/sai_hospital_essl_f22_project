// frontend/src/pages/Payroll.jsx
// MS Softwares - Payroll Report with Date Range

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Calendar, Download, RefreshCw, Users, DollarSign } from 'lucide-react';

export default function Payroll() {
  const today = new Date().toISOString().split('T')[0];
  const firstDayOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0];

  const [startDate, setStartDate] = useState(firstDayOfMonth);
  const [endDate, setEndDate] = useState(today);
  const [payrollData, setPayrollData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchPayrollData();
  }, [startDate, endDate]);

  const fetchPayrollData = async () => {
    try {
      setLoading(true);

      // Fetch all users
      const usersRes = await api.get('/api/v1/users?limit=1000');
      if (usersRes.data.status !== 'success') return;

      const users = usersRes.data.data.users || [];

      // Fetch attendance for each user
      const payrollPromises = users.map(async (user) => {
        try {
          const attRes = await api.get('/api/v1/attendance/processed', {
            params: {
              uid: user.uid,
              start_date: startDate,
              end_date: endDate,
              limit: 1000
            }
          });

          if (attRes.data.status === 'success') {
            const records = attRes.data.data.records || [];

            // Calculate statistics
            const daysPresent = records.filter(r => r.status === 'present' || r.status === 'present_ot').length;
            const daysHalfDay = records.filter(r => r.status === 'half_day').length;
            const daysIncomplete = records.filter(r => r.status === 'incomplete').length;
            const totalHours = records.reduce((sum, r) => sum + (r.work_duration_hours || 0), 0);
            const regularDays = records.filter(r => r.shift === 'Regular').length;
            const breakShiftDays = records.filter(r => r.shift === 'Break Shift').length;

            return {
              uid: user.uid,
              name: user.name,
              daysPresent,
              daysHalfDay,
              daysIncomplete,
              totalHours,
              regularDays,
              breakShiftDays
            };
          }
        } catch (err) {
          console.error(`Error fetching attendance for ${user.name}:`, err);
        }

        return null;
      });

      const results = await Promise.all(payrollPromises);
      setPayrollData(results.filter(r => r !== null));
    } catch (error) {
      console.error('Error fetching payroll data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      const response = await api.get('/api/v1/export/payroll-report', {
        params: {
          start_date: startDate,
          end_date: endDate
        },
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Payroll_${startDate}_to_${endDate}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export payroll report');
    } finally {
      setExporting(false);
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getTotalStats = () => {
    return {
      totalEmployees: payrollData.length,
      totalPresent: payrollData.reduce((sum, p) => sum + p.daysPresent, 0),
      totalHalfDay: payrollData.reduce((sum, p) => sum + p.daysHalfDay, 0),
      totalHours: payrollData.reduce((sum, p) => sum + p.totalHours, 0)
    };
  };

  const stats = getTotalStats();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4">
        <div>
          <p className="text-sm text-gray-500 uppercase tracking-wide font-semibold mb-1">Payroll Summary</p>
          <p className="text-gray-600">Employee payroll summary (all employees)</p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting || payrollData.length === 0 || loading}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Download className="w-4 h-4" />
          {exporting ? 'Exporting...' : 'Export to Excel'}
        </button>
      </div>

      {/* Date Range Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          <Calendar className="inline w-5 h-5 mr-2" />
          Select Period
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              max={endDate}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
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
              min={startDate}
              max={today}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={fetchPayrollData}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>
        </div>
        <p className="text-sm text-gray-600 mt-3">
          Showing data from <span className="font-semibold">{formatDate(startDate)}</span> to <span className="font-semibold">{formatDate(endDate)}</span>
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-600 mb-1">
            <Users className="w-4 h-4" />
            <p className="text-xs font-medium">Total Employees</p>
          </div>
          <p className="text-2xl font-bold text-gray-900">{stats.totalEmployees}</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-green-600 mb-1">
            <DollarSign className="w-4 h-4" />
            <p className="text-xs font-medium">Total Present Days</p>
          </div>
          <p className="text-2xl font-bold text-green-600">{stats.totalPresent}</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-yellow-600 mb-1">
            <DollarSign className="w-4 h-4" />
            <p className="text-xs font-medium">Total Half Days</p>
          </div>
          <p className="text-2xl font-bold text-yellow-600">{stats.totalHalfDay}</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-blue-600 mb-1">
            <DollarSign className="w-4 h-4" />
            <p className="text-xs font-medium">Total Work Hours</p>
          </div>
          <p className="text-2xl font-bold text-blue-600">{stats.totalHours.toFixed(2)}</p>
        </div>
      </div>

      {/* Payroll Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Employee Payroll Summary</h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    S.No
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Employee Name
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Days Present
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Half Days
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Incomplete
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Total Hours
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Regular Days
                  </th>
                  <th className="px-6 py-4 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Break Shift Days
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {payrollData.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center justify-center text-gray-500">
                        <Users className="w-12 h-12 mb-3 text-gray-400" />
                        <p className="text-lg font-medium">No payroll data found</p>
                        <p className="text-sm mt-1">Select a date range and click Refresh</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  payrollData.map((employee, idx) => (
                    <tr key={employee.uid} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                        {idx + 1}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                            <span className="text-blue-700 font-semibold text-sm">
                              {employee.name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">{employee.name}</div>
                            <div className="text-xs text-gray-500">UID: {employee.uid}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                          {employee.daysPresent}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                          {employee.daysHalfDay}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm font-medium">
                          {employee.daysIncomplete}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-semibold text-gray-900">
                        {employee.totalHours.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-700">
                        {employee.regularDays}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-700">
                        {employee.breakShiftDays}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
