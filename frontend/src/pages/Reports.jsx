// frontend/src/pages/Reports.jsx
import React, { useState } from 'react';
import api from '../services/api';
import { Download, Users, Clock, FileSpreadsheet, Filter, ChevronDown, ChevronUp } from 'lucide-react';

const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December'
];

const STATUS_CFG = {
  'Present':    { bg:'bg-green-100',  text:'text-green-800'  },
  'Half Day':   { bg:'bg-yellow-100', text:'text-yellow-800' },
  'Incomplete': { bg:'bg-red-100',    text:'text-red-800'    },
  'Absent':     { bg:'bg-gray-100',   text:'text-gray-600'   },
  'LOP':        { bg:'bg-red-200',    text:'text-red-900'    },
};

function StatusBadge({ status }) {
  const key = Object.keys(STATUS_CFG).find(k => status.startsWith(k)) || 'Absent';
  const cfg = STATUS_CFG[key];
  return (
    <span className={`${cfg.bg} ${cfg.text} px-2 py-0.5 rounded-lg text-xs font-bold whitespace-nowrap`}>
      {status}
    </span>
  );
}

export default function Reports() {
  const today = new Date();
  const [year,     setYear]     = useState(today.getFullYear());
  const [month,    setMonth]    = useState(today.getMonth() + 1);
  const [report,   setReport]   = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [expanded, setExpanded] = useState({});

  const toggle = uid => setExpanded(p => ({ ...p, [uid]: !p[uid] }));

  const generate = async () => {
    try {
      setLoading(true);
      const res = await api.get(
        `/api/v1/payroll/monthly-report-all?year=${year}&month=${month}`
      );
      if (res.data.status === 'success') {
        setReport(res.data.data);
        setExpanded({});
      } else {
        alert(res.data.message || 'Failed');
      }
    } catch (e) {
      console.error(e);
      alert('Error generating report');
    } finally {
      setLoading(false);
    }
  };

  const download = async (fmt) => {
    try {
      const res = await api.get(
        `/api/v1/payroll/monthly-report-all?year=${year}&month=${month}&export=${fmt}`,
        { responseType: 'blob' }
      );
      const mime = fmt === 'excel'
        ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        : 'text/csv';
      const ext = fmt === 'excel' ? 'xlsx' : 'csv';
      const url = window.URL.createObjectURL(new Blob([res.data], { type: mime }));
      const a   = document.createElement('a');
      a.href     = url;
      a.download = `All_Employees_${MONTHS[month-1]}_${year}.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert(`${fmt.toUpperCase()} export failed`);
    }
  };

  const stats = report ? {
    employees:   report.total_employees,
    totalHours:  report.employees.reduce((s,e) => s + e.summary.total_hours, 0).toFixed(2),
    present:     report.employees.reduce((s,e) => s + e.summary.present, 0),
    totalDays:   report.employees.reduce((s,e) => s + e.summary.total_days, 0),
  } : null;

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">

      {/* header */}
      <div className="bg-gradient-to-br from-indigo-900 to-purple-900 rounded-[2rem] p-10 text-white relative overflow-hidden shadow-2xl">
        <h1 className="text-4xl font-black italic tracking-tighter relative z-10">ENTERPRISE REPORTS</h1>
        <p className="text-indigo-200 mt-1 relative z-10 font-medium">
          All-employee monthly attendance — flexible break-shift format
        </p>
        <FileSpreadsheet className="absolute -right-4 -bottom-4 text-white opacity-5 w-48 h-48" />
      </div>

      {/* filters */}
      <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-8 -mt-8 mx-4 relative z-20">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <label className="text-xs font-black text-gray-400 uppercase ml-1">Month</label>
            <select value={month} onChange={e => setMonth(Number(e.target.value))}
              className="mt-1 w-full px-4 py-3 bg-gray-50 border-0 rounded-2xl focus:ring-2 focus:ring-indigo-500 font-medium">
              {MONTHS.map((m,i) => <option key={i+1} value={i+1}>{m}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-black text-gray-400 uppercase ml-1">Year</label>
            <input type="number" value={year} onChange={e => setYear(Number(e.target.value))}
              className="mt-1 w-full px-4 py-3 bg-gray-50 border-0 rounded-2xl focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div className="flex items-end">
            <button onClick={generate} disabled={loading}
              className="w-full bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 disabled:opacity-50 py-3 flex items-center justify-center gap-2">
              <Filter className="w-4 h-4" />
              {loading ? 'Generating…' : 'Generate Report'}
            </button>
          </div>
          {report && (
            <div className="flex items-end gap-2">
              <button onClick={() => download('csv')}
                className="flex-1 bg-gray-100 text-gray-700 rounded-2xl font-bold hover:bg-gray-200 py-3 flex items-center justify-center gap-2">
                <Download className="w-4 h-4" /> CSV
              </button>
              <button onClick={() => download('excel')}
                className="flex-1 bg-green-600 text-white rounded-2xl font-bold hover:bg-green-700 py-3 flex items-center justify-center gap-2 shadow-lg">
                <FileSpreadsheet className="w-4 h-4" /> Excel
              </button>
            </div>
          )}
        </div>
      </div>

      {/* stat cards */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { icon:Users,  label:'Employees',    val:stats.employees,   col:'text-purple-600', bg:'bg-purple-50' },
            { icon:Clock,  label:'Total Days',   val:stats.totalDays,   col:'text-blue-600',   bg:'bg-blue-50'   },
            { icon:Clock,  label:'Total Hours',  val:stats.totalHours+'h', col:'text-indigo-600', bg:'bg-indigo-50' },
            { icon:Users,  label:'Present Records', val:stats.present,  col:'text-green-600',  bg:'bg-green-50'  },
          ].map((s,i) => (
            <div key={i} className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
              <div className={`p-3 ${s.bg} rounded-xl w-fit mb-3`}>
                <s.icon className={`w-6 h-6 ${s.col}`} />
              </div>
              <p className="text-xs font-black text-gray-400 uppercase tracking-widest">{s.label}</p>
              <p className={`text-3xl font-black mt-1 ${s.col}`}>{s.val}</p>
            </div>
          ))}
        </div>
      )}

      {/* per-employee accordion */}
      {report && (
        <div className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="px-8 py-6 border-b bg-gray-50">
            <h3 className="text-xl font-black text-gray-800">
              {report.period.month_name} {report.period.year} — Employee Attendance
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              Excel export creates one sheet per employee. Click an employee to preview their data.
            </p>
          </div>

          <div className="divide-y divide-gray-100">
            {report.employees.map((emp, ei) => {
              const isOpen = expanded[emp.employee.uid];
              const s      = emp.summary;

              return (
                <div key={ei}>
                  {/* accordion header */}
                  <button onClick={() => toggle(emp.employee.uid)}
                    className="w-full px-8 py-5 flex items-center justify-between hover:bg-gray-50 transition-colors">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center text-indigo-700 font-black text-sm">
                        {emp.employee.name.charAt(0)}
                      </div>
                      <div className="text-left">
                        <h4 className="font-black text-gray-900">{emp.employee.name}</h4>
                        <p className="text-xs text-gray-500">
                          UID {emp.employee.uid} &nbsp;•&nbsp;
                          {s.total_days} days &nbsp;•&nbsp; {s.total_hours}h worked
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="hidden md:flex gap-3 text-sm">
                        <span className="text-green-600 font-bold">{s.present} Present</span>
                        {s.half_day  > 0 && <span className="text-yellow-600 font-bold">{s.half_day} Half</span>}
                        {s.incomplete > 0 && <span className="text-red-500 font-bold">{s.incomplete} Inc.</span>}
                        {s.overtime_hours > 0 && <span className="text-blue-600 font-bold">+{s.overtime_hours}h OT</span>}
                      </div>
                      {isOpen
                        ? <ChevronUp   className="w-5 h-5 text-gray-400" />
                        : <ChevronDown className="w-5 h-5 text-gray-400" />}
                    </div>
                  </button>

                  {/* day rows */}
                  {isOpen && (
                    <div className="overflow-x-auto bg-gray-50">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-100 text-[10px] font-black text-gray-400 uppercase tracking-widest">
                          <tr>
                            <th className="px-4 py-3 text-left">Sno</th>
                            <th className="px-4 py-3 text-left">ID</th>
                            <th className="px-4 py-3 text-center">Date</th>
                            <th className="px-4 py-3 text-center">In-1</th>
                            <th className="px-4 py-3 text-center">Out-1</th>
                            <th className="px-4 py-3 text-center">In-2</th>
                            <th className="px-4 py-3 text-center">Out-2</th>
                            <th className="px-4 py-3 text-center">Shift</th>
                            <th className="px-4 py-3 text-center">Total Hrs</th>
                            <th className="px-4 py-3 text-center">Status</th>
                            <th className="px-4 py-3 text-left">Remarks</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 bg-white">
                          {emp.rows.map((row, ri) => (
                            <tr key={ri} className={`hover:bg-gray-50 ${row.shift === 'Break Shift' ? 'bg-blue-50/20' : ''}`}>
                              <td className="px-4 py-3 text-gray-400">{row.sno}</td>
                              <td className="px-4 py-3 font-mono text-indigo-600 font-bold">{row.id}</td>
                              <td className="px-4 py-3 text-center font-bold text-gray-800 whitespace-nowrap">{row.date}</td>
                              <td className="px-4 py-3 text-center text-green-700 font-semibold whitespace-nowrap">{row.in1}</td>
                              <td className="px-4 py-3 text-center text-red-600 font-semibold whitespace-nowrap">{row.out1}</td>
                              <td className="px-4 py-3 text-center font-semibold whitespace-nowrap">
                                {row.in2 !== '-' ? <span className="text-green-700">{row.in2}</span> : <span className="text-gray-300">—</span>}
                              </td>
                              <td className="px-4 py-3 text-center font-semibold whitespace-nowrap">
                                {row.out2 !== '-' ? <span className="text-red-600">{row.out2}</span> : <span className="text-gray-300">—</span>}
                              </td>
                              <td className="px-4 py-3 text-center">
                                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                                  row.shift === 'Break Shift' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                                }`}>
                                  {row.shift}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-center font-black text-indigo-700">
                                {row.total_duration_hours > 0 ? `${row.total_duration_hours.toFixed(2)}h` : '—'}
                              </td>
                              <td className="px-4 py-3 text-center"><StatusBadge status={row.status} /></td>
                              <td className="px-4 py-3 text-gray-500 text-xs max-w-[200px] truncate" title={row.remarks}>
                                {row.remarks || '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {emp.rows.length === 0 && (
                        <p className="text-center py-8 text-gray-400 text-sm">No records this month.</p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!report && !loading && (
        <div className="bg-white rounded-3xl shadow-sm p-20 text-center border border-gray-100">
          <FileSpreadsheet className="w-20 h-20 text-gray-300 mx-auto mb-4" />
          <h3 className="text-2xl font-bold text-gray-700 mb-2">Select Month & Generate</h3>
          <p className="text-gray-400 max-w-sm mx-auto">
            Produces a complete monthly report for all active employees.
            Excel export has one sheet per employee.
          </p>
        </div>
      )}
    </div>
  );
}