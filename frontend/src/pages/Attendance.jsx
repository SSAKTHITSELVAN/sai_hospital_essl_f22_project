// frontend/src/pages/Attendance.jsx
// Fix: removed hardcoded limit=100 — replaced with proper pagination.
//      With 20+ employees over a month, the old code silently truncated
//      data with no indication anything was missing.

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import * as XLSX from 'xlsx';
import { Download, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';

const PAGE_SIZE = 100;

const STATUS_CLASS = {
  present:    'bg-green-100 text-green-700',
  present_ot: 'bg-teal-100 text-teal-700',
  half_day:   'bg-yellow-100 text-yellow-700',
  incomplete: 'bg-red-100 text-red-700',
  absent:     'bg-gray-200 text-gray-600',
  lop:        'bg-red-200 text-red-900',
};

const STATUS_LABEL = {
  present:    'Present',
  present_ot: 'Present + OT',
  half_day:   'Half Day',
  incomplete: 'Incomplete',
  absent:     'Absent',
  lop:        'LOP',
};

export default function Attendance() {
  const today   = new Date().toISOString().split('T')[0];
  const [attendance, setAttendance] = useState([]);
  const [total, setTotal]           = useState(0);
  const [page, setPage]             = useState(0);       // 0-indexed
  const [loading, setLoading]       = useState(true);
  const [startDate, setStartDate]   = useState(today);
  const [endDate, setEndDate]       = useState(today);

  // Reset to page 0 when date range changes
  useEffect(() => {
    setPage(0);
  }, [startDate, endDate]);

  useEffect(() => {
    fetchAttendance();
  }, [startDate, endDate, page]);

  const fetchAttendance = async () => {
    try {
      setLoading(true);
      const skip = page * PAGE_SIZE;
      const res  = await api.get(
        `/api/v1/attendance/processed` +
        `?start_date=${startDate}&end_date=${endDate}` +
        `&skip=${skip}&limit=${PAGE_SIZE}`
      );
      if (res.data.status === 'success') {
        setAttendance(res.data.data.records);
        setTotal(res.data.data.pagination.total);
      }
    } catch (error) {
      console.error('Error fetching attendance:', error);
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const exportToExcel = () => {
    if (attendance.length === 0) return alert('No data to export');
    const data = attendance.map(r => ({
      'Date':        new Date(r.date).toLocaleDateString('en-IN'),
      'Employee':    r.user_name,
      'Shift':       r.shift || 'Regular',
      'In Time':     r.first_in  ? new Date(r.first_in).toLocaleTimeString('en-IN')  : '-',
      'Out Time':    r.last_out  ? new Date(r.last_out).toLocaleTimeString('en-IN')  : '-',
      'Work Hours':  r.work_duration_hours ? r.work_duration_hours.toFixed(2) : '0.00',
      'OT Hours':    r.overtime_hours      ? r.overtime_hours.toFixed(2)      : '0.00',
      'Status':      STATUS_LABEL[r.status] || r.status?.toUpperCase() || '-',
      'Remarks':     r.remarks || '',
    }));
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Attendance');
    XLSX.writeFile(wb, `Attendance_${startDate}_to_${endDate}.xlsx`);
  };

  const processAttendance = async () => {
    try {
      const res = await api.post('/api/v1/attendance/process');
      if (res.data.status === 'success') {
        alert('Attendance processed successfully!');
        fetchAttendance();
      }
    } catch {
      alert('Failed to process attendance');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Attendance Records</h1>
          <p className="text-gray-500 text-sm mt-1">
            {total > 0 ? `${total} records found` : 'No records for this range'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={processAttendance}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
            <RefreshCw className="w-4 h-4" />
            Process
          </button>
          <button onClick={exportToExcel}
            className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
            <Download className="w-4 h-4" />
            Export Excel
          </button>
        </div>
      </div>

      {/* Date Filters */}
      <div className="bg-white rounded-xl shadow-sm p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">FROM</label>
            <input type="date" value={startDate}
              onChange={e => setStartDate(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 mb-1">TO</label>
            <input type="date" value={endDate}
              onChange={e => setEndDate(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left py-4 px-6 font-semibold text-gray-600">Date</th>
                    <th className="text-left py-4 px-6 font-semibold text-gray-600">Employee</th>
                    <th className="text-left py-4 px-6 font-semibold text-gray-600">Shift</th>
                    <th className="text-left py-4 px-6 font-semibold text-gray-600">In Time</th>
                    <th className="text-left py-4 px-6 font-semibold text-gray-600">Out Time</th>
                    <th className="text-left py-4 px-6 font-semibold text-gray-600">Hours</th>
                    <th className="text-left py-4 px-6 font-semibold text-gray-600">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {attendance.map(record => (
                    <tr key={record.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-6 font-medium">
                        {new Date(record.date).toLocaleDateString('en-IN')}
                      </td>
                      <td className="py-3 px-6 font-medium">{record.user_name}</td>
                      <td className="py-3 px-6 text-gray-500">{record.shift || 'Regular'}</td>
                      <td className="py-3 px-6 text-gray-600">
                        {record.first_in
                          ? new Date(record.first_in).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
                          : '—'}
                      </td>
                      <td className="py-3 px-6 text-gray-600">
                        {record.last_out
                          ? new Date(record.last_out).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
                          : '—'}
                      </td>
                      <td className="py-3 px-6 font-semibold text-indigo-700">
                        {record.work_duration_hours ? `${record.work_duration_hours.toFixed(2)}h` : '—'}
                      </td>
                      <td className="py-3 px-6">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${STATUS_CLASS[record.status] || 'bg-gray-100 text-gray-700'}`}>
                          {STATUS_LABEL[record.status] || record.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {attendance.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-gray-400">
                        No attendance records for the selected date range.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-6 py-4 border-t">
                <p className="text-sm text-gray-500">
                  Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total} records
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="p-2 rounded-lg border hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-sm font-medium px-3">
                    {page + 1} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                    className="p-2 rounded-lg border hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed">
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}