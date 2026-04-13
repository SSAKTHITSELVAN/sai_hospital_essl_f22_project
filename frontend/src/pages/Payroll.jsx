// frontend/src/pages/Payroll.jsx
import React, { useState } from 'react';
import api from '../services/api';
import { DollarSign, Download, FileSpreadsheet, AlertTriangle } from 'lucide-react';

/* ── constants ──────────────────────────────────────────────── */
const MONTHS = [
  'January','February','March','April','May','June',
  'July','August','September','October','November','December'
];

const STATUS_CFG = {
  'Present':    { bg: 'bg-green-100',  text: 'text-green-800'  },
  'Half Day':   { bg: 'bg-yellow-100', text: 'text-yellow-800' },
  'Incomplete': { bg: 'bg-red-100',    text: 'text-red-800'    },
  'Absent':     { bg: 'bg-gray-100',   text: 'text-gray-600'   },
  'LOP':        { bg: 'bg-red-200',    text: 'text-red-900'    },
};

function StatusBadge({ status }) {
  // e.g. "Present + 1.50h OT" — key off first word
  const key = Object.keys(STATUS_CFG).find(k => status.startsWith(k)) || 'Absent';
  const cfg = STATUS_CFG[key];
  return (
    <span className={`${cfg.bg} ${cfg.text} px-2 py-0.5 rounded-lg text-xs font-bold whitespace-nowrap`}>
      {status}
    </span>
  );
}

/* ── component ──────────────────────────────────────────────── */
export default function Payroll() {
  const today = new Date();
  const [uid,     setUid]     = useState('');
  const [year,    setYear]    = useState(today.getFullYear());
  const [month,   setMonth]   = useState(today.getMonth() + 1);
  const [report,  setReport]  = useState(null);
  const [loading, setLoading] = useState(false);

  /* ── fetch JSON report ─────────────────────────────────────── */
  const generate = async () => {
    if (!uid) return alert('Enter Employee UID');
    try {
      setLoading(true);
      const res = await api.get(
        `/api/v1/payroll/monthly-report/${uid}?year=${year}&month=${month}`
      );
      if (res.data.status === 'success') {
        setReport(res.data.data);
      } else {
        alert(res.data.message || 'Not found');
      }
    } catch (e) {
      console.error(e);
      alert('Error loading report');
    } finally {
      setLoading(false);
    }
  };

  /* ── download helpers ──────────────────────────────────────── */
  const download = async (fmt) => {
    if (!uid) return;
    try {
      const res = await api.get(
        `/api/v1/payroll/monthly-report/${uid}?year=${year}&month=${month}&export=${fmt}`,
        { responseType: 'blob' }
      );
      const mime = fmt === 'excel'
        ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        : 'text/csv';
      const ext  = fmt === 'excel' ? 'xlsx' : 'csv';
      const url  = window.URL.createObjectURL(new Blob([res.data], { type: mime }));
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `Attendance_${report?.employee?.name?.replace(/\s+/g,'_') || uid}_${MONTHS[month-1]}_${year}.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert(`${fmt.toUpperCase()} export failed`);
    }
  };

  const s = report?.summary;

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto pb-20">

      {/* header */}
      <div className="bg-gradient-to-br from-slate-900 to-slate-700 rounded-[2rem] p-10 text-white relative overflow-hidden shadow-2xl">
        <h1 className="text-4xl font-black italic tracking-tighter relative z-10">PAYROLL ENGINE</h1>
        <p className="text-slate-400 mt-1 relative z-10 font-medium">
          Monthly attendance report — flexible 24-hour cycle with break-shift support
        </p>
        <DollarSign className="absolute -right-4 -bottom-4 text-white opacity-5 w-48 h-48" />
      </div>

      {/* filter bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-white p-6 rounded-3xl border border-gray-100 shadow-sm -mt-8 mx-4 relative z-20">
        <div>
          <label className="block text-xs font-bold text-gray-500 mb-2">EMPLOYEE UID</label>
          <input type="number" placeholder="e.g. 3"
            value={uid} onChange={e => setUid(e.target.value)}
            className="w-full px-4 py-3 bg-gray-50 rounded-2xl border-0 focus:ring-2 focus:ring-indigo-500 font-medium"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 mb-2">MONTH</label>
          <select value={month} onChange={e => setMonth(Number(e.target.value))}
            className="w-full px-4 py-3 bg-gray-50 rounded-2xl border-0 focus:ring-2 focus:ring-indigo-500">
            {MONTHS.map((m,i) => <option key={i+1} value={i+1}>{m}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 mb-2">YEAR</label>
          <input type="number" value={year} onChange={e => setYear(Number(e.target.value))}
            className="w-full px-4 py-3 bg-gray-50 rounded-2xl border-0 focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div className="flex items-end">
          <button onClick={generate} disabled={loading}
            className="w-full bg-indigo-600 text-white rounded-2xl font-bold hover:bg-indigo-700 disabled:opacity-50 py-3">
            {loading ? 'Loading…' : 'Generate'}
          </button>
        </div>
      </div>

      {report && (
        <div className="space-y-6">

          {/* employee card + export buttons */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between bg-white p-8 rounded-3xl border border-gray-100 shadow-sm gap-4">
            <div className="flex items-center gap-5">
              <div className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center text-white text-2xl font-black">
                {report.employee.name.charAt(0)}
              </div>
              <div>
                <h3 className="text-2xl font-black text-gray-900">{report.employee.name}</h3>
                <p className="text-gray-500">UID: {report.employee.uid} &nbsp;•&nbsp; {report.period.month_name} {report.period.year}</p>
              </div>
            </div>
            <div className="flex gap-3">
              <button onClick={() => download('csv')}
                className="flex items-center gap-2 px-5 py-3 bg-gray-100 text-gray-700 rounded-2xl hover:bg-gray-200 font-bold transition-all">
                <Download className="w-4 h-4" /> CSV
              </button>
              <button onClick={() => download('excel')}
                className="flex items-center gap-2 px-5 py-3 bg-green-600 text-white rounded-2xl hover:bg-green-700 font-bold shadow-lg transition-all">
                <FileSpreadsheet className="w-4 h-4" /> Excel
              </button>
            </div>
          </div>

          {/* summary cards */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {[
              { label:'Present',    val: s.present,                col:'text-green-700'  },
              { label:'Half Day',   val: s.half_day,               col:'text-yellow-600' },
              { label:'Incomplete', val: s.incomplete,             col:'text-red-500'    },
              { label:'Total Hrs',  val:`${s.total_hours}h`,       col:'text-indigo-600' },
              { label:'OT Hrs',     val:`${s.overtime_hours}h`,    col:'text-blue-600'   },
            ].map((c,i) => (
              <div key={i} className="bg-white p-5 rounded-3xl border border-gray-100 shadow-sm">
                <p className="text-xs font-black text-gray-400 uppercase tracking-widest">{c.label}</p>
                <p className={`text-3xl font-black mt-2 ${c.col}`}>{c.val}</p>
              </div>
            ))}
          </div>

          {/* attendance table */}
          <div className="bg-white rounded-3xl border border-gray-100 overflow-hidden shadow-sm">
            <div className="px-8 py-5 border-b flex items-center justify-between">
              <h3 className="text-lg font-black text-gray-800">Day-wise Attendance</h3>
              {s.incomplete > 0 && (
                <span className="flex items-center gap-1 text-red-500 text-xs font-bold bg-red-50 px-3 py-1 rounded-full">
                  <AlertTriangle size={12}/>{s.incomplete} incomplete
                </span>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-[11px] font-black text-gray-400 uppercase tracking-widest">
                  <tr>
                    <th className="px-4 py-4 text-left">Sno</th>
                    <th className="px-4 py-4 text-left">ID</th>
                    <th className="px-4 py-4 text-left">Employee</th>
                    <th className="px-4 py-4 text-center">Date</th>
                    <th className="px-4 py-4 text-center">In-1</th>
                    <th className="px-4 py-4 text-center">Out-1</th>
                    <th className="px-4 py-4 text-center">In-2</th>
                    <th className="px-4 py-4 text-center">Out-2</th>
                    <th className="px-4 py-4 text-center">Shift</th>
                    <th className="px-4 py-4 text-center">Total Hrs</th>
                    <th className="px-4 py-4 text-center">Status</th>
                    <th className="px-4 py-4 text-left">Remarks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {report.rows.map((row, i) => (
                    <tr key={i} className={`hover:bg-gray-50 transition-colors ${row.shift === 'Break Shift' ? 'bg-blue-50/30' : ''}`}>
                      <td className="px-4 py-3 text-gray-400 font-medium">{row.sno}</td>
                      <td className="px-4 py-3 font-mono text-indigo-600 font-bold">{row.id}</td>
                      <td className="px-4 py-3 font-semibold text-gray-900">{row.employee_name}</td>
                      <td className="px-4 py-3 text-center font-bold text-gray-800 whitespace-nowrap">{row.date}</td>

                      {/* Session 1 */}
                      <td className="px-4 py-3 text-center text-green-700 font-semibold whitespace-nowrap">{row.in1}</td>
                      <td className="px-4 py-3 text-center text-red-600 font-semibold whitespace-nowrap">{row.out1}</td>

                      {/* Session 2 */}
                      <td className="px-4 py-3 text-center font-semibold whitespace-nowrap">
                        {row.in2 !== '-'
                          ? <span className="text-green-700">{row.in2}</span>
                          : <span className="text-gray-300">—</span>
                        }
                      </td>
                      <td className="px-4 py-3 text-center font-semibold whitespace-nowrap">
                        {row.out2 !== '-'
                          ? <span className="text-red-600">{row.out2}</span>
                          : <span className="text-gray-300">—</span>
                        }
                      </td>

                      <td className="px-4 py-3 text-center">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          row.shift === 'Break Shift'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {row.shift}
                        </span>
                      </td>

                      <td className="px-4 py-3 text-center font-black text-indigo-700">
                        {row.total_duration_hours > 0
                          ? `${row.total_duration_hours.toFixed(2)}h`
                          : '—'}
                      </td>

                      <td className="px-4 py-3 text-center">
                        <StatusBadge status={row.status} />
                      </td>

                      <td className="px-4 py-3 text-gray-500 text-xs max-w-[220px] truncate" title={row.remarks}>
                        {row.remarks || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {report.rows.length === 0 && (
                <div className="text-center py-16 text-gray-400 font-medium">
                  No attendance records for {report.period.month_name} {report.period.year}.
                </div>
              )}
            </div>
          </div>

        </div>
      )}

      {!report && !loading && (
        <div className="bg-white rounded-3xl shadow-sm p-16 text-center border border-gray-100">
          <DollarSign className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 font-medium">Enter Employee UID → select month → Generate.</p>
        </div>
      )}
    </div>
  );
}