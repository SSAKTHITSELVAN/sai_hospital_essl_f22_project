// frontend/src/pages/Dashboard.jsx
// Fix: "Late Today" stat removed — backend has no 'late' status.
//       Replaced with "Half Day" which is a real AttendanceStatus value.
//       Status values from backend: present, present_ot, half_day, incomplete, absent, lop

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Users, Clock, CheckCircle, AlertCircle, Calendar } from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalUsers:      0,
    todayPresent:    0,
    todayHalfDay:    0,
    todayIncomplete: 0,
  });
  const [loading, setLoading]             = useState(true);
  const [todayAttendance, setTodayAttendance] = useState([]);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      const usersRes = await api.get('/api/v1/users?limit=1');
      const totalUsers = usersRes.data.data.pagination.total;

      const attendanceRes = await api.get('/api/v1/attendance/today');
      if (attendanceRes.data.status === 'success') {
        const records = attendanceRes.data.data.records || [];
        setTodayAttendance(records);

        // Backend statuses: present, present_ot, half_day, incomplete, absent, lop
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

  const statusBadgeClass = (status) => {
    switch (status) {
      case 'present':    return 'bg-green-100 text-green-700';
      case 'present_ot': return 'bg-teal-100 text-teal-700';
      case 'half_day':   return 'bg-yellow-100 text-yellow-700';
      case 'incomplete': return 'bg-red-100 text-red-700';
      case 'lop':        return 'bg-red-200 text-red-900';
      default:           return 'bg-gray-100 text-gray-700';
    }
  };

  const statusLabel = (status) => {
    const map = {
      present:    'Present',
      present_ot: 'Present + OT',
      half_day:   'Half Day',
      incomplete: 'Incomplete',
      absent:     'Absent',
      lop:        'LOP',
    };
    return map[status] || status;
  };

  const statCards = [
    {
      title:     'Total Employees',
      value:     stats.totalUsers,
      icon:      Users,
      textColor: 'text-blue-600',
      bgColor:   'bg-blue-50',
    },
    {
      title:     'Present Today',
      value:     stats.todayPresent,
      icon:      CheckCircle,
      textColor: 'text-green-600',
      bgColor:   'bg-green-50',
    },
    {
      title:     'Half Day',
      value:     stats.todayHalfDay,
      icon:      Clock,
      textColor: 'text-yellow-600',
      bgColor:   'bg-yellow-50',
    },
    {
      title:     'Incomplete',
      value:     stats.todayIncomplete,
      icon:      AlertCircle,
      textColor: 'text-red-600',
      bgColor:   'bg-red-50',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-2xl p-8 text-white">
        <h1 className="text-3xl font-bold mb-2">Welcome Back, Admin!</h1>
        <p className="text-indigo-100">
          {new Date().toLocaleDateString('en-IN', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
          })}
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className="bg-white rounded-xl shadow-sm p-6 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm font-medium mb-1">{stat.title}</p>
                  <p className="text-3xl font-bold text-gray-800">{stat.value}</p>
                </div>
                <div className={`${stat.bgColor} p-3 rounded-lg`}>
                  <Icon className={`w-6 h-6 ${stat.textColor}`} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Today's Attendance Table */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">Today's Attendance</h2>
          <Calendar className="w-5 h-5 text-gray-400" />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Employee</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Shift</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">First In</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Last Out</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Hours</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Status</th>
              </tr>
            </thead>
            <tbody>
              {todayAttendance.slice(0, 15).map((record, i) => (
                <tr key={i} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-semibold text-sm">
                        {(record.name || '?').charAt(0).toUpperCase()}
                      </div>
                      <span className="font-medium">{record.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-1 bg-gray-100 rounded text-sm font-medium">
                      {record.shift || 'Regular'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600">
                    {record.first_in
                      ? new Date(record.first_in).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
                      : '—'}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-600">
                    {record.last_out
                      ? new Date(record.last_out).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
                      : '—'}
                  </td>
                  <td className="py-3 px-4 text-sm font-semibold">
                    {record.work_duration_hours ? record.work_duration_hours.toFixed(2) : '—'}h
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusBadgeClass(record.status)}`}>
                      {statusLabel(record.status)}
                    </span>
                  </td>
                </tr>
              ))}
              {todayAttendance.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-gray-400">
                    No attendance records for today yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}