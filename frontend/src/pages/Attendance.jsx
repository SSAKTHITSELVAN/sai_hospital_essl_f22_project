// frontend/src/pages/Attendance.jsx
import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Calendar, Download, RefreshCw } from 'lucide-react';

export default function Attendance() {
  const [attendance, setAttendance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    fetchAttendance();
  }, [startDate, endDate]);

  const fetchAttendance = async () => {
    try {
      setLoading(true);
      const response = await api.get(
        `/api/v1/attendance/processed?start_date=${startDate}&end_date=${endDate}&limit=100`
      );
      if (response.data.status === 'success') {
        setAttendance(response.data.data.records);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching attendance:', error);
      setLoading(false);
    }
  };

  const processAttendance = async () => {
    try {
      const response = await api.post('/api/v1/attendance/process');
      if (response.data.status === 'success') {
        alert('Attendance processed successfully!');
        fetchAttendance();
      }
    } catch (error) {
      console.error('Error processing attendance:', error);
      alert('Failed to process attendance');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Attendance Records</h1>
          <p className="text-gray-600 mt-1">View and manage attendance</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={processAttendance}
            className="flex items-center space-x-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
          >
            <RefreshCw className="w-5 h-5" />
            <span>Process</span>
          </button>
          <button className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
            <Download className="w-5 h-5" />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
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
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            />
          </div>
        </div>
      </div>

      {/* Attendance Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Date</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Employee</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Shift</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">In Time</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Out Time</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Hours</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Status</th>
              </tr>
            </thead>
            <tbody>
              {attendance.map((record) => (
                <tr key={record.id} className="border-b hover:bg-gray-50">
                  <td className="py-4 px-6 text-sm text-gray-600">
                    {new Date(record.date).toLocaleDateString()}
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-semibold text-sm">
                        {record.user_name.charAt(0)}
                      </div>
                      <span className="font-medium">{record.user_name}</span>
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <span className="px-2 py-1 bg-gray-100 rounded text-sm font-medium">
                      {record.shift}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-sm">
                    {record.first_in ? (
                      <div>
                        <div className="font-medium">
                          {new Date(record.first_in).toLocaleTimeString()}
                        </div>
                        {record.is_late && (
                          <div className="text-xs text-red-600">
                            Late by {record.late_by_minutes} min
                          </div>
                        )}
                      </div>
                    ) : '-'}
                  </td>
                  <td className="py-4 px-6 text-sm">
                    {record.last_out ? (
                      <div>
                        <div className="font-medium">
                          {new Date(record.last_out).toLocaleTimeString()}
                        </div>
                        {record.is_early_leave && (
                          <div className="text-xs text-orange-600">
                            Early by {record.early_leave_by_minutes} min
                          </div>
                        )}
                      </div>
                    ) : '-'}
                  </td>
                  <td className="py-4 px-6 font-semibold text-sm">
                    {record.work_duration_hours ? record.work_duration_hours.toFixed(2) + 'h' : '-'}
                  </td>
                  <td className="py-4 px-6">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      record.status === 'present' ? 'bg-green-100 text-green-700' :
                      record.status === 'late' ? 'bg-yellow-100 text-yellow-700' :
                      record.status === 'early_leave' ? 'bg-orange-100 text-orange-700' :
                      record.status === 'incomplete' ? 'bg-red-100 text-red-700' :
                      record.status === 'half_day' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {record.status.replace('_', ' ')}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

