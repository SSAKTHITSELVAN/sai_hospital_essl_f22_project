

// frontend/src/pages/Attendance.jsx
import React, { useState, useEffect } from 'react';
import api from '../services/api';
import * as XLSX from 'xlsx';
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

  const exportToExcel = () => {
    if (attendance.length === 0) return alert("No data to export");
    const data = attendance.map(record => ({
      'Date': new Date(record.date).toLocaleDateString(),
      'Employee': record.user_name,
      'Shift': record.shift,
      'In Time': record.first_in ? new Date(record.first_in).toLocaleTimeString() : '-',
      'Out Time': record.last_out ? new Date(record.last_out).toLocaleTimeString() : '-',
      'Work Hours': record.work_duration_hours ? record.work_duration_hours.toFixed(2) : '0.00',
      'Status': record.status.toUpperCase()
    }));

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Attendance Records");
    XLSX.writeFile(wb, `Attendance_${startDate}_to_${endDate}.xlsx`);
  };

  const processAttendance = async () => {
    try {
      const response = await api.post('/api/v1/attendance/process');
      if (response.data.status === 'success') {
        alert('Attendance processed successfully!');
        fetchAttendance();
      }
    } catch (error) {
      alert('Failed to process attendance');
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div></div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Attendance Records</h1>
          <p className="text-gray-600 mt-1">View and manage attendance</p>
        </div>
        <div className="flex items-center space-x-3">
          <button onClick={processAttendance} className="flex items-center space-x-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
            <RefreshCw className="w-5 h-5" />
            <span>Process</span>
          </button>
          <button onClick={exportToExcel} className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
            <Download className="w-5 h-5" />
            <span>Export Excel</span>
          </button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-full px-4 py-2 border rounded-lg" />
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left py-4 px-6">Date</th>
              <th className="text-left py-4 px-6">Employee</th>
              <th className="text-left py-4 px-6">In Time</th>
              <th className="text-left py-4 px-6">Out Time</th>
              <th className="text-left py-4 px-6">Status</th>
            </tr>
          </thead>
          <tbody>
            {attendance.map((record) => (
              <tr key={record.id} className="border-b hover:bg-gray-50">
                <td className="py-4 px-6">{new Date(record.date).toLocaleDateString()}</td>
                <td className="py-4 px-6 font-medium">{record.user_name}</td>
                <td className="py-4 px-6">{record.first_in ? new Date(record.first_in).toLocaleTimeString() : '-'}</td>
                <td className="py-4 px-6">{record.last_out ? new Date(record.last_out).toLocaleTimeString() : '-'}</td>
                <td className="py-4 px-6">
                   <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-100">{record.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}