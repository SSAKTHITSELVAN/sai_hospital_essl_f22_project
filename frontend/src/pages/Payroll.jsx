// frontend/src/pages/Payroll.jsx
import React, { useState } from 'react';
import api from '../services/api';
import * as XLSX from 'xlsx';
import { 
  DollarSign, 
  Download, 
  User, 
  Calendar, 
  Clock, 
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet
} from 'lucide-react';

export default function Payroll() {
  const [uid, setUid] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [report, setReport] = useState(null);
  const [detailedData, setDetailedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedMonths, setExpandedMonths] = useState({});

  const generateReport = async () => {
    if (!uid || !startDate || !endDate) return alert('Fill all fields');
    try {
      setLoading(true);
      
      // Get summary report
      const summaryRes = await api.get(
        `/api/v1/payroll/detailed-report/${uid}?start_date=${startDate}&end_date=${endDate}`
      );
      
      // Get detailed day-wise data
      const detailedRes = await api.get(
        `/api/v1/attendance/summary/${uid}?start_date=${startDate}&end_date=${endDate}&detailed=true`
      );
      
      if (summaryRes.data.status === 'success') {
        setReport(summaryRes.data.data);
      }
      
      if (detailedRes.data.status === 'success') {
        setDetailedData(detailedRes.data.data);
      }
      
      setLoading(false);
    } catch (e) {
      console.error('Error loading data:', e);
      setLoading(false);
      alert('Error loading data');
    }
  };

  const toggleMonth = (monthKey) => {
    setExpandedMonths(prev => ({
      ...prev,
      [monthKey]: !prev[monthKey]
    }));
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      'present': { bg: 'bg-green-100', text: 'text-green-700', label: 'Present' },
      'late': { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Late' },
      'incomplete': { bg: 'bg-red-100', text: 'text-red-700', label: 'Incomplete' },
      'half_day': { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Half Day' },
      'early_leave': { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Early Leave' },
      'absent': { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Absent' },
      'lop': { bg: 'bg-red-200', text: 'text-red-900', label: 'LOP' }
    };
    
    const config = statusConfig[status] || statusConfig['absent'];
    return (
      <span className={`${config.bg} ${config.text} px-2 py-1 rounded-lg text-xs font-bold`}>
        {config.label}
      </span>
    );
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
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const exportDetailedExcel = () => {
    if (!detailedData || !report) return;

    const wb = XLSX.utils.book_new();

    // Sheet 1: Employee Summary
    const summaryData = [
      ['EMPLOYEE PAYROLL REPORT'],
      [''],
      ['Employee Information'],
      ['Name:', report.user.name],
      ['Employee UID:', report.user.uid],
      ['Card Number:', report.user.card_no || 'N/A'],
      ['Report Period:', `${startDate} to ${endDate}`],
      ['Total Calendar Days:', report.period.total_days],
      [''],
      ['ATTENDANCE SUMMARY'],
      ['Metric', 'Value'],
      ['Total Days Worked', report.summary.total_worked_days],
      ['Present Days', report.summary.present_days],
      ['Late Days', report.summary.late_days],
      ['Early Leave Days', report.summary.early_leave_days],
      ['Incomplete Days', report.summary.incomplete_days],
      ['Half Days', report.summary.half_days],
      ['Total Leaves', report.summary.leaves],
      ['Total Hours Worked', report.summary.total_hours_worked + ' hours'],
      ['Overtime Hours', report.summary.overtime_hours + ' hours'],
      ['Average Hours Per Day', report.summary.average_hours_per_day + ' hours'],
      ['Attendance Rate', report.summary.attendance_rate + '%']
    ];
    const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
    summarySheet['!cols'] = [{ wch: 25 }, { wch: 30 }];
    XLSX.utils.book_append_sheet(wb, summarySheet, 'Employee Summary');

    // Sheet 2: Complete Day-wise Attendance (Month-wise organized with summaries)
    const completeDayWiseData = [
      ['COMPLETE ATTENDANCE RECORD - DAY WISE WITH MONTHLY SUMMARIES'],
      ['Employee:', report.user.name, '', 'UID:', report.user.uid, '', 'Period:', `${startDate} to ${endDate}`],
      ['']
    ];

    // Add data for each month with monthly summary
    if (detailedData.months) {
      detailedData.months.forEach((month, monthIndex) => {
        // Month header with summary
        completeDayWiseData.push([]);
        completeDayWiseData.push([
          `MONTH: ${month.month}`,
          '',
          '',
          `Total Days: ${month.month_summary.total_days}`,
          '',
          `Present: ${month.month_summary.present}`,
          '',
          `Late: ${month.month_summary.late}`,
          '',
          `Incomplete: ${month.month_summary.incomplete}`,
          '',
          `Total Hours: ${month.month_summary.total_hours_worked}h`
        ]);
        completeDayWiseData.push([]);
        
        // Column headers for this month
        completeDayWiseData.push([
          'Date', 
          'Day of Week', 
          'Shift', 
          'Check In Time', 
          'Check Out Time', 
          'Work Hours', 
          'Status', 
          'Late?', 
          'Late By (mins)', 
          'Early Leave?', 
          'Early By (mins)', 
          'Total Punches', 
          'Remarks'
        ]);

        // Add each day's data
        month.days.forEach(day => {
          completeDayWiseData.push([
            day.date,
            new Date(day.date).toLocaleDateString('en-US', { weekday: 'long' }),
            day.shift || '-',
            formatTime(day.first_in),
            formatTime(day.last_out),
            day.work_duration_hours ? day.work_duration_hours.toFixed(2) : '0.00',
            (day.status || 'N/A').toUpperCase(),
            day.is_late ? 'YES' : 'NO',
            day.late_by_minutes || 0,
            day.is_early_leave ? 'YES' : 'NO',
            day.early_leave_by_minutes || 0,
            day.total_punches || 0,
            day.remarks || '-'
          ]);
        });

        // Month footer summary
        const monthTotalHours = month.days.reduce((sum, day) => sum + (day.work_duration_hours || 0), 0);
        completeDayWiseData.push([]);
        completeDayWiseData.push([
          `${month.month} SUMMARY:`,
          '',
          `Days Worked: ${month.month_summary.total_days}`,
          '',
          `Total Hours: ${monthTotalHours.toFixed(2)}h`,
          '',
          `Avg Hours/Day: ${month.days.length > 0 ? (monthTotalHours / month.days.length).toFixed(2) : 0}h`,
          '',
          `Present: ${month.month_summary.present}`,
          '',
          `Late: ${month.month_summary.late}`,
          '',
          `Incomplete: ${month.month_summary.incomplete}`
        ]);
      });
    }

    const completeDaySheet = XLSX.utils.aoa_to_sheet(completeDayWiseData);
    completeDaySheet['!cols'] = [
      { wch: 12 }, // Date
      { wch: 15 }, // Day
      { wch: 8 },  // Shift
      { wch: 15 }, // Check In
      { wch: 15 }, // Check Out
      { wch: 12 }, // Work Hours
      { wch: 12 }, // Status
      { wch: 8 },  // Late?
      { wch: 15 }, // Late By
      { wch: 12 }, // Early Leave?
      { wch: 15 }, // Early By
      { wch: 12 }, // Punches
      { wch: 35 }  // Remarks
    ];
    XLSX.utils.book_append_sheet(wb, completeDaySheet, 'Complete Day-wise Record');

    // Sheet 3: Monthly Summary with Details
    const monthlyDetailData = [
      ['MONTHLY BREAKDOWN SUMMARY'],
      [''],
      ['Month', 'Days Worked', 'Present Days', 'Late Days', 'Early Leave', 'Incomplete Days', 'Half Days', 'Leaves', 'Total Hours', 'Overtime Hours', 'Avg Hours/Day']
    ];
    
    report.monthly_breakdown.forEach(month => {
      monthlyDetailData.push([
        month.month,
        month.total_days_worked,
        month.present_days,
        month.late_days,
        month.early_leave_days,
        month.incomplete_days,
        month.half_days,
        month.leaves,
        month.total_hours,
        month.overtime_hours,
        month.average_hours_per_day
      ]);
    });
    
    const monthlyDetailSheet = XLSX.utils.aoa_to_sheet(monthlyDetailData);
    monthlyDetailSheet['!cols'] = [
      { wch: 15 }, { wch: 12 }, { wch: 12 }, { wch: 10 }, 
      { wch: 12 }, { wch: 15 }, { wch: 10 }, { wch: 10 },
      { wch: 12 }, { wch: 15 }, { wch: 15 }
    ];
    XLSX.utils.book_append_sheet(wb, monthlyDetailSheet, 'Monthly Summary');

    // Sheet 4: Month-wise Day Details (Separate view)
    if (detailedData.months) {
      detailedData.months.forEach(month => {
        const monthSheetData = [
          [month.month.toUpperCase() + ' - DAILY ATTENDANCE'],
          ['Employee:', report.user.name, '', 'UID:', report.user.uid],
          [''],
          ['Month Summary:'],
          ['Total Days:', month.month_summary.total_days, '', 'Total Hours:', month.month_summary.total_hours_worked + 'h'],
          ['Present:', month.month_summary.present, '', 'Late:', month.month_summary.late, '', 'Incomplete:', month.month_summary.incomplete],
          [''],
          ['Date', 'Day', 'Shift', 'Check In', 'Check Out', 'Work Hours', 'Status', 'Late By (mins)', 'Early Leave By (mins)', 'Remarks']
        ];

        month.days.forEach(day => {
          monthSheetData.push([
            day.date,
            new Date(day.date).toLocaleDateString('en-US', { weekday: 'long' }),
            day.shift || '-',
            formatTime(day.first_in),
            formatTime(day.last_out),
            day.work_duration_hours ? day.work_duration_hours.toFixed(2) + 'h' : '-',
            (day.status || 'N/A').toUpperCase(),
            day.late_by_minutes || 0,
            day.early_leave_by_minutes || 0,
            day.remarks || '-'
          ]);
        });

        const monthSheet = XLSX.utils.aoa_to_sheet(monthSheetData);
        monthSheet['!cols'] = [
          { wch: 12 }, { wch: 12 }, { wch: 8 }, { wch: 15 }, 
          { wch: 15 }, { wch: 12 }, { wch: 12 }, { wch: 15 }, 
          { wch: 18 }, { wch: 35 }
        ];
        
        // Clean month name for sheet name (Excel has 31 char limit)
        const sheetName = month.month.substring(0, 31);
        XLSX.utils.book_append_sheet(wb, monthSheet, sheetName);
      });
    }

    // Sheet 5: Shift-wise Analysis
    const shiftAnalysisData = [
      ['SHIFT-WISE ANALYSIS'],
      [''],
      ['Shift', 'Days Worked', 'Present Days', 'Late Days', 'Total Hours', 'Average Hours/Day', 'Attendance Rate']
    ];
    
    Object.entries(report.shift_analysis).forEach(([shift, data]) => {
      shiftAnalysisData.push([
        `Shift ${shift}`,
        data.total_days_worked,
        data.present_days,
        data.late_days,
        data.total_hours,
        data.average_hours_per_day,
        data.attendance_rate + '%'
      ]);
    });
    
    const shiftSheet = XLSX.utils.aoa_to_sheet(shiftAnalysisData);
    shiftSheet['!cols'] = [
      { wch: 10 }, { wch: 15 }, { wch: 15 }, { wch: 12 }, 
      { wch: 15 }, { wch: 18 }, { wch: 18 }
    ];
    XLSX.utils.book_append_sheet(wb, shiftSheet, 'Shift Analysis');

    // Save file
    const fileName = `Payroll_${report.user.name.replace(/\s+/g, '_')}_${startDate}_to_${endDate}.xlsx`;
    XLSX.writeFile(wb, fileName);
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto pb-20">
      {/* Header */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-[2.5rem] p-10 text-white relative overflow-hidden shadow-2xl">
        <div className="relative z-10">
          <h1 className="text-4xl font-black italic tracking-tighter">PAYROLL ENGINE</h1>
          <p className="text-slate-400 mt-2 font-medium">Comprehensive attendance & salary processing</p>
        </div>
        <DollarSign className="absolute -right-4 -bottom-4 text-white opacity-5 w-48 h-48" />
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-white p-6 rounded-3xl border border-gray-100 shadow-sm -mt-10 mx-6 relative z-20">
        <div>
          <label className="block text-xs font-bold text-gray-500 mb-2 ml-1">EMPLOYEE UID</label>
          <input 
            type="number" 
            placeholder="Enter User ID" 
            value={uid} 
            onChange={(e) => setUid(e.target.value)} 
            className="w-full px-5 py-3 bg-gray-50 rounded-2xl border-0 focus:ring-2 focus:ring-indigo-500 font-medium" 
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 mb-2 ml-1">FROM DATE</label>
          <input 
            type="date" 
            value={startDate} 
            onChange={(e) => setStartDate(e.target.value)} 
            className="w-full px-5 py-3 bg-gray-50 rounded-2xl border-0 focus:ring-2 focus:ring-indigo-500" 
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 mb-2 ml-1">TO DATE</label>
          <input 
            type="date" 
            value={endDate} 
            onChange={(e) => setEndDate(e.target.value)} 
            className="w-full px-5 py-3 bg-gray-50 rounded-2xl border-0 focus:ring-2 focus:ring-indigo-500" 
          />
        </div>
        <div className="flex items-end">
          <button 
            onClick={generateReport} 
            disabled={loading} 
            className="w-full bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 transition-all disabled:opacity-50 py-3"
          >
            {loading ? 'Loading...' : 'Generate Report'}
          </button>
        </div>
      </div>

      {report && detailedData && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-5 duration-500">
          {/* Employee Info & Export */}
          <div className="flex items-center justify-between bg-white p-8 rounded-3xl border border-gray-100 shadow-sm">
            <div className="flex items-center space-x-6">
              <div className="w-16 h-16 bg-indigo-600 rounded-2xl flex items-center justify-center text-white text-2xl font-bold">
                {report.user.name.charAt(0)}
              </div>
              <div>
                <h3 className="text-2xl font-black text-gray-900">{report.user.name}</h3>
                <p className="text-gray-500 font-medium">
                  UID: {report.user.uid} • Period: {startDate} to {endDate}
                </p>
              </div>
            </div>
            <button 
              onClick={exportDetailedExcel} 
              className="flex items-center space-x-2 px-6 py-4 bg-green-600 text-white rounded-2xl hover:bg-green-700 transition-all shadow-lg"
            >
              <FileSpreadsheet className="w-5 h-5" />
              <span className="font-bold">Export Detailed Excel</span>
            </button>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {[
              { label: 'Total Hours', val: report.summary.total_hours_worked + 'h', col: 'text-indigo-600' },
              { label: 'Present Days', val: report.summary.present_days, col: 'text-green-600' },
              { label: 'Late Days', val: report.summary.late_days, col: 'text-yellow-600' },
              { label: 'Incomplete', val: report.summary.incomplete_days, col: 'text-red-500' },
              { label: 'Attendance Rate', val: report.summary.attendance_rate + '%', col: 'text-gray-900' }
            ].map((item, i) => (
              <div key={i} className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
                <p className="text-xs font-black text-gray-400 uppercase tracking-widest">{item.label}</p>
                <p className={`text-3xl font-black mt-2 ${item.col}`}>{item.val}</p>
              </div>
            ))}
          </div>

          {/* Day-wise Detailed View */}
          <div className="bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm">
            <div className="px-8 py-6 border-b border-gray-50 flex justify-between items-center">
              <h3 className="text-lg font-black text-gray-800">Day-wise Attendance Details</h3>
              {report.summary.incomplete_days > 0 && (
                <div className="flex items-center space-x-2 text-red-500 text-xs font-bold bg-red-50 px-3 py-1 rounded-full">
                  <AlertTriangle size={14}/>
                  <span>{report.summary.incomplete_days} Issues Found</span>
                </div>
              )}
            </div>

            {/* Month-wise Expandable Sections */}
            <div className="divide-y divide-gray-100">
              {detailedData.months?.map((month, monthIdx) => (
                <div key={monthIdx} className="border-b border-gray-100">
                  {/* Month Header */}
                  <button
                    onClick={() => toggleMonth(month.month)}
                    className="w-full px-8 py-5 flex items-center justify-between hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
                        <Calendar className="w-5 h-5 text-indigo-600" />
                      </div>
                      <div className="text-left">
                        <h4 className="font-black text-gray-900">{month.month}</h4>
                        <p className="text-sm text-gray-500 font-medium">
                          {month.month_summary.total_days} days • {month.month_summary.total_hours_worked}h worked
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right text-sm">
                        <span className="text-green-600 font-bold">{month.month_summary.present} Present</span>
                        {month.month_summary.late > 0 && (
                          <span className="text-yellow-600 font-bold ml-3">{month.month_summary.late} Late</span>
                        )}
                        {month.month_summary.incomplete > 0 && (
                          <span className="text-red-600 font-bold ml-3">{month.month_summary.incomplete} Incomplete</span>
                        )}
                      </div>
                      {expandedMonths[month.month] ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                  </button>

                  {/* Day-wise Details */}
                  {expandedMonths[month.month] && (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50/80 text-[10px] font-black text-gray-400 uppercase tracking-widest">
                          <tr>
                            <th className="px-8 py-4 text-left">Date</th>
                            <th className="px-4 py-4 text-left">Shift</th>
                            <th className="px-4 py-4 text-left">Check In</th>
                            <th className="px-4 py-4 text-left">Check Out</th>
                            <th className="px-4 py-4 text-center">Work Hours</th>
                            <th className="px-4 py-4 text-center">Status</th>
                            <th className="px-4 py-4 text-center">Late</th>
                            <th className="px-4 py-4 text-left">Remarks</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                          {month.days.map((day, dayIdx) => (
                            <tr key={dayIdx} className="hover:bg-gray-50/50 transition-colors">
                              <td className="px-8 py-4">
                                <div>
                                  <div className="font-bold text-gray-900">{formatDate(day.date)}</div>
                                  <div className="text-xs text-gray-500">{day.date}</div>
                                </div>
                              </td>
                              <td className="px-4 py-4">
                                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-lg text-xs font-bold">
                                  {day.shift || '-'}
                                </span>
                              </td>
                              <td className="px-4 py-4 font-medium text-gray-700">
                                {formatTime(day.first_in)}
                              </td>
                              <td className="px-4 py-4 font-medium text-gray-700">
                                {formatTime(day.last_out)}
                              </td>
                              <td className="px-4 py-4 text-center">
                                <span className="font-black text-indigo-600">
                                  {day.work_duration_hours ? day.work_duration_hours.toFixed(2) + 'h' : '-'}
                                </span>
                              </td>
                              <td className="px-4 py-4 text-center">
                                {getStatusBadge(day.status)}
                              </td>
                              <td className="px-4 py-4 text-center">
                                {day.is_late ? (
                                  <span className="text-yellow-600 font-bold text-sm">
                                    +{day.late_by_minutes}m
                                  </span>
                                ) : (
                                  <span className="text-gray-400">-</span>
                                )}
                              </td>
                              <td className="px-4 py-4 text-sm text-gray-500">
                                {day.remarks || '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Shift Analysis */}
          <div className="bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm">
            <div className="px-8 py-6 border-b border-gray-50">
              <h3 className="text-lg font-black text-gray-800">Shift-wise Analysis</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-8">
              {Object.entries(report.shift_analysis).map(([shift, data]) => (
                <div key={shift} className="border border-gray-200 rounded-2xl p-6 hover:border-indigo-300 transition-colors">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-black text-gray-900 text-xl">Shift {shift}</h4>
                    <Clock className="w-5 h-5 text-gray-400" />
                  </div>
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Days Worked:</span>
                      <span className="font-bold text-gray-900">{data.total_days_worked}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Total Hours:</span>
                      <span className="font-bold text-indigo-600">{data.total_hours}h</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Late Days:</span>
                      <span className="font-bold text-yellow-600">{data.late_days}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Rate:</span>
                      <span className="font-bold text-green-600">{data.attendance_rate}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!report && !loading && (
        <div className="bg-white rounded-3xl shadow-sm p-16 text-center border border-gray-100">
          <DollarSign className="w-20 h-20 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 text-lg font-medium">Enter employee details and date range to generate payroll report</p>
        </div>
      )}
    </div>
  );
}