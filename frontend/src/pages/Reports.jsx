// frontend/src/pages/Reports.jsx
import React, { useState, useEffect } from 'react';
import api from '../services/api';
import * as XLSX from 'xlsx';
import { 
  Download, 
  Users, 
  Calendar,
  Clock,
  TrendingUp,
  FileSpreadsheet,
  Filter,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

export default function Reports() {
  const [dateRange, setDateRange] = useState('current_month');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [allUsers, setAllUsers] = useState([]);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedDates, setExpandedDates] = useState({});

  useEffect(() => {
    fetchUsers();
    setDateRangeValues('current_month');
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await api.get('/api/v1/users?limit=500');
      if (response.data.status === 'success') {
        setAllUsers(response.data.data.users);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  const setDateRangeValues = (range) => {
    const today = new Date();
    let start, end;

    switch(range) {
      case 'current_week':
        const day = today.getDay();
        start = new Date(today);
        start.setDate(today.getDate() - day);
        end = new Date(today);
        break;
      case 'current_month':
        start = new Date(today.getFullYear(), today.getMonth(), 1);
        end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        break;
      case 'last_6_months':
        start = new Date(today.getFullYear(), today.getMonth() - 6, 1);
        end = new Date(today);
        break;
      case 'current_year':
        start = new Date(today.getFullYear(), 0, 1);
        end = new Date(today.getFullYear(), 11, 31);
        break;
      case 'custom':
        return;
      default:
        start = new Date(today.getFullYear(), today.getMonth(), 1);
        end = new Date(today);
    }

    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
  };

  const handleDateRangeChange = (range) => {
    setDateRange(range);
    setDateRangeValues(range);
  };

  const generateDetailedReport = async () => {
    if (!startDate || !endDate) return alert('Select date range');
    
    try {
      setLoading(true);
      
      // Fetch detailed attendance for all users
      const promises = allUsers.map(user => 
        api.get(`/api/v1/attendance/summary/${user.uid}?start_date=${startDate}&end_date=${endDate}&detailed=true`)
      );

      const responses = await Promise.all(promises);
      
      const detailedData = responses
        .filter(res => res.data.status === 'success')
        .map(res => res.data.data);

      // Organize data by date
      const dateWiseData = {};
      
      detailedData.forEach(userData => {
        if (userData.months) {
          userData.months.forEach(month => {
            month.days.forEach(day => {
              if (!dateWiseData[day.date]) {
                dateWiseData[day.date] = [];
              }
              
              const user = allUsers.find(u => u.uid === userData.uid);
              dateWiseData[day.date].push({
                uid: userData.uid,
                name: user?.name || 'Unknown',
                card_no: user?.card_no || '-',
                date: day.date,
                shift: day.shift,
                first_in: day.first_in,
                last_out: day.last_out,
                work_duration_hours: day.work_duration_hours,
                status: day.status,
                is_late: day.is_late,
                late_by_minutes: day.late_by_minutes,
                is_early_leave: day.is_early_leave,
                early_leave_by_minutes: day.early_leave_by_minutes,
                total_punches: day.total_punches,
                remarks: day.remarks
              });
            });
          });
        }
      });

      // Calculate statistics
      const totalDays = Object.keys(dateWiseData).length;
      const totalEmployees = allUsers.length;
      let totalPresent = 0;
      let totalLate = 0;
      let totalIncomplete = 0;
      let totalHours = 0;

      Object.values(dateWiseData).forEach(dayData => {
        dayData.forEach(record => {
          if (record.status === 'present') totalPresent++;
          if (record.status === 'late') totalLate++;
          if (record.status === 'incomplete') totalIncomplete++;
          totalHours += record.work_duration_hours || 0;
        });
      });

      setReportData({
        dateWiseData: dateWiseData,
        statistics: {
          totalDays,
          totalEmployees,
          totalRecords: totalPresent + totalLate + totalIncomplete,
          totalPresent,
          totalLate,
          totalIncomplete,
          totalHours: totalHours.toFixed(2),
          averageHoursPerDay: totalDays > 0 ? (totalHours / totalDays).toFixed(2) : 0
        },
        allUsersData: detailedData
      });

      setLoading(false);
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Failed to generate report');
      setLoading(false);
    }
  };

  const toggleDate = (date) => {
    setExpandedDates(prev => ({
      ...prev,
      [date]: !prev[date]
    }));
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '-';
    return new Date(timestamp).toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getStatusBadge = (status) => {
    const config = {
      'present': { bg: 'bg-green-100', text: 'text-green-700', label: 'Present' },
      'late': { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Late' },
      'incomplete': { bg: 'bg-red-100', text: 'text-red-700', label: 'Incomplete' },
      'half_day': { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Half Day' },
      'early_leave': { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Early Leave' },
      'absent': { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Absent' }
    };
    const cfg = config[status] || config['absent'];
    return <span className={`${cfg.bg} ${cfg.text} px-2 py-1 rounded-lg text-xs font-bold`}>{cfg.label}</span>;
  };

  const exportDetailedReport = () => {
    if (!reportData) return;

    const wb = XLSX.utils.book_new();

    // Sheet 1: Report Summary
    const summaryData = [
      ['ENTERPRISE ATTENDANCE REPORT'],
      ['Report Generated:', new Date().toLocaleString()],
      ['Period:', `${startDate} to ${endDate}`],
      [''],
      ['SUMMARY STATISTICS'],
      ['Total Days:', reportData.statistics.totalDays],
      ['Total Employees:', reportData.statistics.totalEmployees],
      ['Total Attendance Records:', reportData.statistics.totalRecords],
      ['Total Present:', reportData.statistics.totalPresent],
      ['Total Late:', reportData.statistics.totalLate],
      ['Total Incomplete:', reportData.statistics.totalIncomplete],
      ['Total Work Hours:', reportData.statistics.totalHours + ' hours'],
      ['Average Hours/Day:', reportData.statistics.averageHoursPerDay + ' hours'],
    ];
    const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
    summarySheet['!cols'] = [{ wch: 30 }, { wch: 30 }];
    XLSX.utils.book_append_sheet(wb, summarySheet, 'Report Summary');

    // Sheet 2: Complete Day-wise Attendance
    const dayWiseHeader = [
      'Date', 'Day of Week', 'Employee UID', 'Employee Name', 'Card No', 
      'Shift', 'Check In', 'Check Out', 'Work Hours', 'Status', 
      'Late?', 'Late By (mins)', 'Early Leave?', 'Early By (mins)', 
      'Total Punches', 'Remarks'
    ];
    const dayWiseData = [dayWiseHeader];

    const sortedDates = Object.keys(reportData.dateWiseData).sort();
    
    sortedDates.forEach(date => {
      const records = reportData.dateWiseData[date];
      records.forEach(record => {
        dayWiseData.push([
          date,
          new Date(date).toLocaleDateString('en-US', { weekday: 'long' }),
          record.uid,
          record.name,
          record.card_no,
          record.shift || '-',
          formatTime(record.first_in),
          formatTime(record.last_out),
          record.work_duration_hours ? record.work_duration_hours.toFixed(2) : '0.00',
          (record.status || 'absent').toUpperCase(),
          record.is_late ? 'YES' : 'NO',
          record.late_by_minutes || 0,
          record.is_early_leave ? 'YES' : 'NO',
          record.early_leave_by_minutes || 0,
          record.total_punches || 0,
          record.remarks || '-'
        ]);
      });
    });

    const dayWiseSheet = XLSX.utils.aoa_to_sheet(dayWiseData);
    dayWiseSheet['!cols'] = [
      { wch: 12 }, { wch: 15 }, { wch: 12 }, { wch: 25 }, { wch: 12 },
      { wch: 8 }, { wch: 15 }, { wch: 15 }, { wch: 12 }, { wch: 12 },
      { wch: 8 }, { wch: 15 }, { wch: 12 }, { wch: 15 }, { wch: 12 }, { wch: 35 }
    ];
    XLSX.utils.book_append_sheet(wb, dayWiseSheet, 'Complete Attendance');

    // Sheet 3: Employee-wise Summary
    const empSummaryHeader = ['Employee UID', 'Employee Name', 'Total Days', 'Present', 'Late', 'Incomplete', 'Total Hours', 'Avg Hours/Day'];
    const empSummaryData = [empSummaryHeader];

    reportData.allUsersData.forEach(userData => {
      empSummaryData.push([
        userData.uid,
        allUsers.find(u => u.uid === userData.uid)?.name || 'Unknown',
        userData.summary?.total_days || 0,
        userData.summary?.present || 0,
        userData.summary?.late || 0,
        userData.summary?.incomplete || 0,
        userData.summary?.total_hours_worked || 0,
        userData.summary?.average_hours_per_day || 0
      ]);
    });

    const empSummarySheet = XLSX.utils.aoa_to_sheet(empSummaryData);
    empSummarySheet['!cols'] = [
      { wch: 15 }, { wch: 25 }, { wch: 12 }, { wch: 10 }, 
      { wch: 10 }, { wch: 12 }, { wch: 12 }, { wch: 15 }
    ];
    XLSX.utils.book_append_sheet(wb, empSummarySheet, 'Employee Summary');

    // Sheet 4: Date-wise Summary
    const dateSummaryHeader = ['Date', 'Day', 'Total Present', 'Total Late', 'Total Incomplete', 'Total Hours'];
    const dateSummaryData = [dateSummaryHeader];

    sortedDates.forEach(date => {
      const records = reportData.dateWiseData[date];
      const present = records.filter(r => r.status === 'present').length;
      const late = records.filter(r => r.status === 'late').length;
      const incomplete = records.filter(r => r.status === 'incomplete').length;
      const hours = records.reduce((sum, r) => sum + (r.work_duration_hours || 0), 0);

      dateSummaryData.push([
        date,
        new Date(date).toLocaleDateString('en-US', { weekday: 'long' }),
        present,
        late,
        incomplete,
        hours.toFixed(2)
      ]);
    });

    const dateSummarySheet = XLSX.utils.aoa_to_sheet(dateSummaryData);
    dateSummarySheet['!cols'] = [
      { wch: 12 }, { wch: 15 }, { wch: 15 }, { wch: 12 }, { wch: 15 }, { wch: 12 }
    ];
    XLSX.utils.book_append_sheet(wb, dateSummarySheet, 'Date-wise Summary');

    // Save file
    XLSX.writeFile(wb, `Enterprise_Attendance_Report_${startDate}_to_${endDate}.xlsx`);
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="bg-gradient-to-br from-indigo-900 to-purple-900 rounded-[2.5rem] p-10 text-white relative overflow-hidden shadow-2xl">
        <div className="relative z-10">
          <h1 className="text-4xl font-black italic tracking-tighter">ENTERPRISE REPORTS</h1>
          <p className="text-indigo-200 mt-2 font-medium">Comprehensive attendance analytics for payroll processing</p>
        </div>
        <FileSpreadsheet className="absolute -right-4 -bottom-4 text-white opacity-5 w-48 h-48" />
      </div>

      {/* Filters */}
      <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-8 -mt-10 mx-6 relative z-20">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase ml-1">Quick Select</label>
            <select 
              value={dateRange} 
              onChange={(e) => handleDateRangeChange(e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 border-0 rounded-2xl focus:ring-2 focus:ring-indigo-500 font-medium"
            >
              <option value="current_week">Current Week</option>
              <option value="current_month">Current Month</option>
              <option value="last_6_months">Last 6 Months</option>
              <option value="current_year">Current Year</option>
              <option value="custom">Custom Range</option>
            </select>
          </div>
          
          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase ml-1">From Date</label>
            <input 
              type="date" 
              value={startDate} 
              onChange={(e) => setStartDate(e.target.value)} 
              className="w-full px-4 py-3 bg-gray-50 border-0 rounded-2xl focus:ring-2 focus:ring-indigo-500"
              disabled={dateRange !== 'custom'}
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase ml-1">To Date</label>
            <input 
              type="date" 
              value={endDate} 
              onChange={(e) => setEndDate(e.target.value)} 
              className="w-full px-4 py-3 bg-gray-50 border-0 rounded-2xl focus:ring-2 focus:ring-indigo-500"
              disabled={dateRange !== 'custom'}
            />
          </div>
          
          <div className="flex items-end">
            <button 
              onClick={generateDetailedReport} 
              disabled={loading}
              className="w-full bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 transition-all disabled:opacity-50 py-3 flex items-center justify-center space-x-2"
            >
              <Filter className="w-5 h-5" />
              <span>{loading ? 'Generating...' : 'Generate Report'}</span>
            </button>
          </div>
          
          {reportData && (
            <div className="flex items-end">
              <button 
                onClick={exportDetailedReport}
                className="w-full bg-green-600 text-white rounded-2xl font-bold hover:bg-green-700 transition-all py-3 flex items-center justify-center space-x-2"
              >
                <Download className="w-5 h-5" />
                <span>Export Excel</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
      {reportData && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: Calendar, label: 'Total Days', value: reportData.statistics.totalDays, color: 'text-blue-600', bg: 'bg-blue-50' },
              { icon: Users, label: 'Total Employees', value: reportData.statistics.totalEmployees, color: 'text-purple-600', bg: 'bg-purple-50' },
              { icon: TrendingUp, label: 'Present Records', value: reportData.statistics.totalPresent, color: 'text-green-600', bg: 'bg-green-50' },
              { icon: Clock, label: 'Total Hours', value: reportData.statistics.totalHours + 'h', color: 'text-indigo-600', bg: 'bg-indigo-50' }
            ].map((stat, i) => (
              <div key={i} className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-3 ${stat.bg} rounded-xl`}>
                    <stat.icon className={`w-6 h-6 ${stat.color}`} />
                  </div>
                </div>
                <p className="text-xs font-black text-gray-400 uppercase tracking-widest">{stat.label}</p>
                <p className={`text-3xl font-black mt-2 ${stat.color}`}>{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Day-wise Detailed View */}
          <div className="bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm">
            <div className="px-8 py-6 border-b border-gray-50 bg-gradient-to-r from-gray-50 to-white">
              <h3 className="text-xl font-black text-gray-800">Daily Attendance Records</h3>
              <p className="text-sm text-gray-500 mt-1">Complete day-by-day attendance with employee details</p>
            </div>

            <div className="divide-y divide-gray-100 max-h-[800px] overflow-y-auto">
              {Object.keys(reportData.dateWiseData).sort().reverse().map((date, idx) => {
                const dayRecords = reportData.dateWiseData[date];
                const presentCount = dayRecords.filter(r => r.status === 'present').length;
                const lateCount = dayRecords.filter(r => r.status === 'late').length;
                const incompleteCount = dayRecords.filter(r => r.status === 'incomplete').length;

                return (
                  <div key={idx} className="border-b border-gray-100">
                    {/* Date Header */}
                    <button
                      onClick={() => toggleDate(date)}
                      className="w-full px-8 py-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
                          <Calendar className="w-6 h-6 text-indigo-600" />
                        </div>
                        <div className="text-left">
                          <h4 className="font-black text-gray-900">{formatDate(date)}</h4>
                          <p className="text-sm text-gray-500 font-medium">
                            {dayRecords.length} employees • {dayRecords.reduce((sum, r) => sum + (r.work_duration_hours || 0), 0).toFixed(2)}h total
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right text-sm space-x-3">
                          <span className="text-green-600 font-bold">{presentCount} Present</span>
                          {lateCount > 0 && <span className="text-yellow-600 font-bold">{lateCount} Late</span>}
                          {incompleteCount > 0 && <span className="text-red-600 font-bold">{incompleteCount} Incomplete</span>}
                        </div>
                        {expandedDates[date] ? 
                          <ChevronUp className="w-5 h-5 text-gray-400" /> : 
                          <ChevronDown className="w-5 h-5 text-gray-400" />
                        }
                      </div>
                    </button>

                    {/* Employee Records */}
                    {expandedDates[date] && (
                      <div className="overflow-x-auto bg-gray-50">
                        <table className="w-full">
                          <thead className="bg-gray-100 text-[10px] font-black text-gray-400 uppercase tracking-widest">
                            <tr>
                              <th className="px-6 py-4 text-left">UID</th>
                              <th className="px-6 py-4 text-left">Employee Name</th>
                              <th className="px-6 py-4 text-left">Card No</th>
                              <th className="px-6 py-4 text-center">Shift</th>
                              <th className="px-6 py-4 text-left">Check In</th>
                              <th className="px-6 py-4 text-left">Check Out</th>
                              <th className="px-6 py-4 text-center">Hours</th>
                              <th className="px-6 py-4 text-center">Status</th>
                              <th className="px-6 py-4 text-center">Late</th>
                              <th className="px-6 py-4 text-left">Remarks</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-100 bg-white">
                            {dayRecords.map((record, recordIdx) => (
                              <tr key={recordIdx} className="hover:bg-gray-50 transition-colors">
                                <td className="px-6 py-4 font-bold text-gray-700">{record.uid}</td>
                                <td className="px-6 py-4 font-medium text-gray-900">{record.name}</td>
                                <td className="px-6 py-4 text-gray-600">{record.card_no}</td>
                                <td className="px-6 py-4 text-center">
                                  <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs font-bold">
                                    {record.shift || '-'}
                                  </span>
                                </td>
                                <td className="px-6 py-4 font-medium text-gray-700">{formatTime(record.first_in)}</td>
                                <td className="px-6 py-4 font-medium text-gray-700">{formatTime(record.last_out)}</td>
                                <td className="px-6 py-4 text-center">
                                  <span className="font-black text-indigo-600">
                                    {record.work_duration_hours ? record.work_duration_hours.toFixed(2) + 'h' : '-'}
                                  </span>
                                </td>
                                <td className="px-6 py-4 text-center">{getStatusBadge(record.status)}</td>
                                <td className="px-6 py-4 text-center">
                                  {record.is_late ? (
                                    <span className="text-yellow-600 font-bold text-sm">+{record.late_by_minutes}m</span>
                                  ) : (
                                    <span className="text-gray-400">-</span>
                                  )}
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-500">{record.remarks || '-'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}

      {/* Empty State */}
      {!reportData && !loading && (
        <div className="bg-white rounded-3xl shadow-sm p-20 text-center border border-gray-100">
          <FileSpreadsheet className="w-24 h-24 text-gray-300 mx-auto mb-6" />
          <h3 className="text-2xl font-bold text-gray-700 mb-2">Generate Enterprise Report</h3>
          <p className="text-gray-500 text-lg max-w-md mx-auto">
            Select a date range and generate comprehensive attendance reports for all employees with complete day-wise details
          </p>
        </div>
      )}
    </div>
  );
}