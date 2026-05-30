// frontend/src/pages/Attendance.jsx
// MS Softwares - Daily Attendance View (Single Date Filter)

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Calendar, Download, RefreshCw, Users, Clock } from 'lucide-react';

// Live Timer Component for ongoing sessions
function LiveTimer({ startTime }) {
  const [elapsed, setElapsed] = useState('');

  useEffect(() => {
    const updateTimer = () => {
      const start = new Date(startTime);
      const now = new Date();
      const diffMs = now - start;

      const hours = Math.floor(diffMs / (1000 * 60 * 60));
      const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diffMs % (1000 * 60)) / 1000);

      setElapsed(`${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <span className="font-mono text-blue-600 font-bold animate-pulse">
      {elapsed}
    </span>
  );
}

export default function Attendance() {
  const today = new Date().toISOString().split('T')[0];

  const [selectedDate, setSelectedDate] = useState(today);
  const [attendance, setAttendance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [stats, setStats] = useState({
    total: 0,
    present: 0,
    halfDay: 0,
    incomplete: 0,
    activeSessions: 0
  });

  useEffect(() => {
    fetchAttendance();
  }, [selectedDate]);

  // Auto-refresh every 30 seconds if viewing today's date
  useEffect(() => {
    if (selectedDate === today) {
      const interval = setInterval(() => {
        fetchAttendance();
      }, 30000); // Refresh every 30 seconds

      return () => clearInterval(interval);
    }
  }, [selectedDate, today]);

  const fetchAttendance = async () => {
    try {
      setLoading(true);

      // Fetch processed attendance for the selected date
      const response = await api.get(`/api/v1/attendance/processed`, {
        params: {
          start_date: selectedDate,
          end_date: selectedDate,
          limit: 1000
        }
      });

      if (response.data.status === 'success') {
        const records = response.data.data.records || [];
        setAttendance(records);

        // Calculate stats
        const present = records.filter(r => r.status === 'present' || r.status === 'present_ot').length;
        const halfDay = records.filter(r => r.status === 'half_day').length;
        const incomplete = records.filter(r => r.status === 'incomplete').length;

        // Count active sessions (has IN but no OUT on today's date)
        let activeSessions = 0;
        if (selectedDate === today) {
          records.forEach(record => {
            try {
              const sessions = record.sessions || [];
              sessions.forEach(session => {
                if (session.in && !session.out) {
                  activeSessions++;
                }
              });
            } catch (e) {
              // Ignore parsing errors
            }
          });
        }

        setStats({
          total: records.length,
          present,
          halfDay,
          incomplete,
          activeSessions
        });
      }
    } catch (error) {
      console.error('Error fetching attendance:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      const response = await api.get('/api/v1/export/today-attendance', {
        responseType: 'blob',
        params: { date: selectedDate }
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Attendance_${selectedDate}.xlsx`);
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
      lop:        'bg-red-200 text-red-900 border-red-300',
    };
    const labels = {
      present:    'Present',
      present_ot: 'Present (OT)',
      half_day:   'Half Day',
      incomplete: 'Incomplete',
      absent:     'Absent',
      lop:        'LOP',
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

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
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
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4">
        <div>
          <p className="text-sm text-gray-500 uppercase tracking-wide font-semibold mb-1">Daily Records</p>
          <p className="text-gray-600">View attendance by date (all employees)</p>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting || attendance.length === 0}
          className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Download className="w-4 h-4" />
          {exporting ? 'Exporting...' : 'Export to Excel'}
        </button>
      </div>

      {/* Date Filter & Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Date Picker */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            <Calendar className="inline w-4 h-4 mr-2" />
            Select Date
          </label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            max={today}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-600">{formatDate(selectedDate)}</p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-gray-600 mb-1">
              <Users className="w-4 h-4" />
              <p className="text-xs font-medium">Total</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-green-600 mb-1">
              <Clock className="w-4 h-4" />
              <p className="text-xs font-medium">Present</p>
            </div>
            <p className="text-2xl font-bold text-green-600">{stats.present}</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-yellow-600 mb-1">
              <Clock className="w-4 h-4" />
              <p className="text-xs font-medium">Half Day</p>
            </div>
            <p className="text-2xl font-bold text-yellow-600">{stats.halfDay}</p>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 text-orange-600 mb-1">
              <Clock className="w-4 h-4" />
              <p className="text-xs font-medium">Incomplete</p>
            </div>
            <p className="text-2xl font-bold text-orange-600">{stats.incomplete}</p>
          </div>

          {/* Active Sessions (only show for today) */}
          {selectedDate === today && (
            <div className="bg-white rounded-xl shadow-sm border border-blue-200 p-4">
              <div className="flex items-center gap-2 text-blue-600 mb-1">
                <Clock className="w-4 h-4 animate-pulse" />
                <p className="text-xs font-medium">Active Now</p>
              </div>
              <p className="text-2xl font-bold text-blue-600">{stats.activeSessions}</p>
            </div>
          )}
        </div>
      </div>

      {/* Attendance Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Attendance Records</h2>
            <div className="flex items-center gap-3 mt-1">
              <p className="text-sm text-gray-600">{formatDate(selectedDate)}</p>
              {selectedDate === today && (
                <span className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                  <Clock className="w-3 h-3 animate-pulse" />
                  Auto-refresh every 30s
                </span>
              )}
            </div>
          </div>
          <button
            onClick={fetchAttendance}
            className="flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh Now
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  S.No
                </th>
                <th className="px-4 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Employee Name
                </th>
                <th className="px-4 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  IN-1
                </th>
                <th className="px-4 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  OUT-1
                </th>
                <th className="px-4 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  IN-2
                </th>
                <th className="px-4 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  OUT-2
                </th>
                <th className="px-4 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Work Hours
                </th>
                <th className="px-4 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {attendance.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center text-gray-500">
                      <Users className="w-12 h-12 mb-3 text-gray-400" />
                      <p className="text-lg font-medium">No attendance records found</p>
                      <p className="text-sm mt-1">
                        No employees punched in/out on {formatDate(selectedDate)}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                attendance.map((record, idx) => {
                  // Parse punch sessions JSON
                  let sessions = [];
                  try {
                    sessions = record.sessions || [];
                  } catch (e) {
                    sessions = [];
                  }

                  // Get session 1 and session 2 data
                  const session1 = sessions[0] || {};
                  const session2 = sessions[1] || {};

                  const in1 = session1.in;
                  const out1 = session1.out;
                  const in2 = session2.in;
                  const out2 = session2.out;

                  const isToday = selectedDate === today;

                  // Helper function to render punch cell
                  const renderPunchCell = (time, type, sessionNum) => {
                    const hasTime = time && time !== null;
                    const isIn = type === 'in';
                    const isOngoing = isToday && hasTime && isIn &&
                                     ((sessionNum === 1 && !out1) || (sessionNum === 2 && !out2));

                    return (
                      <td className="px-4 py-4 text-sm">
                        {hasTime ? (
                          <div className="space-y-1">
                            <div className={`font-medium ${isIn ? 'text-green-700' : 'text-red-700'}`}>
                              {formatTime(time)}
                            </div>
                            {isOngoing && (
                              <div className="flex items-center gap-1 text-xs">
                                <Clock className="w-3 h-3 text-blue-600 animate-pulse" />
                                <LiveTimer startTime={time} />
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-400 text-xs">Not Used</span>
                        )}
                      </td>
                    );
                  };

                  return (
                    <tr key={idx} className="hover:bg-gray-50 transition-colors">
                      {/* S.No */}
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                        {idx + 1}
                      </td>

                      {/* Employee Name */}
                      <td className="px-4 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                            <span className="text-blue-700 font-semibold text-sm">
                              {record.user_name?.charAt(0).toUpperCase() || '?'}
                            </span>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">
                              {record.user_name || 'Unknown'}
                            </div>
                            <div className="text-xs text-gray-500">UID: {record.uid}</div>
                          </div>
                        </div>
                      </td>

                      {/* IN-1 */}
                      {renderPunchCell(in1, 'in', 1)}

                      {/* OUT-1 */}
                      {renderPunchCell(out1, 'out', 1)}

                      {/* IN-2 */}
                      {renderPunchCell(in2, 'in', 2)}

                      {/* OUT-2 */}
                      {renderPunchCell(out2, 'out', 2)}

                      {/* Work Hours */}
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-700">
                        {record.work_duration_hours ? `${record.work_duration_hours.toFixed(2)} hrs` : '-'}
                      </td>

                      {/* Status */}
                      <td className="px-4 py-4 whitespace-nowrap">
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

      {/* Footer Info */}
      {attendance.length > 0 && (
        <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
          <p className="text-sm text-blue-900">
            <span className="font-semibold">{attendance.length}</span> employee{attendance.length !== 1 ? 's' : ''} recorded on {formatDate(selectedDate)}
          </p>
        </div>
      )}
    </div>
  );
}
