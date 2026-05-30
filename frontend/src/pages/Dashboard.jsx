// frontend/src/pages/Dashboard.jsx
// Enterprise-grade Dashboard with Dual Device Support

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Users, Clock, CheckCircle, AlertCircle, Calendar, Download } from 'lucide-react';
import DeviceStatus from '../components/DeviceStatus';

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalUsers:      0,
    todayPresent:    0,
    todayHalfDay:    0,
    todayIncomplete: 0,
  });
  const [loading, setLoading] = useState(true);
  const [todayAttendance, setTodayAttendance] = useState([]);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    fetchDashboardData();
    // Refresh every 2 minutes
    const interval = setInterval(fetchDashboardData, 120000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      // Fetch total users
      const usersRes = await api.get('/api/v1/users?limit=1');
      const totalUsers = usersRes.data.data.pagination?.total || 0;

      // Fetch today's attendance
      const attendanceRes = await api.get('/api/v1/attendance/today');
      if (attendanceRes.data.status === 'success') {
        const records = attendanceRes.data.data.records || [];
        setTodayAttendance(records);

        // Calculate stats
        const present    = records.filter(r =>
          r.status === 'present' || r.status === 'present_ot'
        ).length;
        const halfDay    = records.filter(r => r.status === 'half_day').length;
        const incomplete = records.filter(r => r.status === 'incomplete').length;

        setStats({ totalUsers, todayPresent: present, todayHalfDay: halfDay, todayIncomplete: incomplete });
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      const response = await api.get('/api/v1/export/today-attendance', {
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Attendance_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export attendance');
    } finally {
      setExporting(false);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      present:    'bg-green-100 text-green-800 border-green-200',
      present_ot: 'bg-blue-100 text-blue-800 border-blue-200',
      half_day:   'bg-yellow-100 text-yellow-800 border-yellow-200',
      incomplete: 'bg-orange-100 text-orange-800 border-orange-200',
      absent:     'bg-red-100 text-red-800 border-red-200',
    };
    const labels = {
      present:    'Present',
      present_ot: 'Present (OT)',
      half_day:   'Half Day',
      incomplete: 'Incomplete',
      absent:     'Absent',
    };
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${badges[status] || badges.incomplete}`}>
        {labels[status] || 'Unknown'}
      </span>
    );
  };

  const formatTime = (datetime) => {
    if (!datetime) return '-';
    const date = new Date(datetime);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">MS Softwares - Real-time attendance overview</p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting || todayAttendance.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Download className="w-4 h-4" />
          {exporting ? 'Exporting...' : 'Export to Excel'}
        </button>
      </div>

      {/* Device Status */}
      <DeviceStatus />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Users */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Employees</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">{stats.totalUsers}</p>
            </div>
            <div className="bg-blue-100 p-3 rounded-lg">
              <Users className="w-8 h-8 text-blue-600" />
            </div>
          </div>
        </div>

        {/* Present Today */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Present Today</p>
              <p className="text-3xl font-bold text-green-600 mt-2">{stats.todayPresent}</p>
            </div>
            <div className="bg-green-100 p-3 rounded-lg">
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
          </div>
        </div>

        {/* Half Day */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Half Day</p>
              <p className="text-3xl font-bold text-yellow-600 mt-2">{stats.todayHalfDay}</p>
            </div>
            <div className="bg-yellow-100 p-3 rounded-lg">
              <Clock className="w-8 h-8 text-yellow-600" />
            </div>
          </div>
        </div>

        {/* Incomplete */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Incomplete</p>
              <p className="text-3xl font-bold text-orange-600 mt-2">{stats.todayIncomplete}</p>
            </div>
            <div className="bg-orange-100 p-3 rounded-lg">
              <AlertCircle className="w-8 h-8 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Today's Attendance Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Today's Attendance</h2>
          <p className="text-sm text-gray-600 mt-1">{new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                  Employee Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                  Punch Sessions
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                  Work Hours
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                  Shift Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {todayAttendance.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                    No attendance records for today
                  </td>
                </tr>
              ) : (
                todayAttendance.map((record, idx) => {
                  // Parse punch sessions
                  let sessions = [];
                  try {
                    sessions = record.punch_sessions ? JSON.parse(record.punch_sessions) : [];
                  } catch (e) {
                    sessions = [];
                  }

                  return (
                    <tr key={idx} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-medium text-gray-900">{record.user_name || 'Unknown'}</div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-700">
                        {sessions.length === 0 ? (
                          <span className="text-gray-400">-</span>
                        ) : (
                          <div className="space-y-1">
                            {sessions.map((session, sidx) => (
                              <div key={sidx} className="flex items-center gap-2">
                                {sessions.length > 1 && (
                                  <span className="text-xs font-medium text-gray-500">{sidx + 1}:</span>
                                )}
                                <span className="text-green-700">IN: {formatTime(session.in)}</span>
                                <span className="text-gray-400">→</span>
                                <span className="text-red-700">OUT: {formatTime(session.out)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                        {record.work_duration_hours ? `${record.work_duration_hours.toFixed(2)} hrs` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                        {record.shift || 'Regular'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(record.status)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
