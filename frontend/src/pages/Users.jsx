// // frontend/src/pages/Users.jsx
// import React, { useState, useEffect } from 'react';
// import api from '../services/api';
// import { Search, UserPlus, Edit, Trash2 } from 'lucide-react';

// export default function Users() {
//   const [users, setUsers] = useState([]);
//   const [loading, setLoading] = useState(true);
//   const [searchTerm, setSearchTerm] = useState('');
//   const [reportStart, setReportStart] = useState('');
//   const [reportEnd, setReportEnd] = useState('');

//   const exportUserCSV = async (uid) => {
//     if (!reportStart || !reportEnd) return alert('Please select start and end date before exporting');
//     try {
//       const res = await api.get(`/api/v1/attendance/summary/${uid}?start_date=${reportStart}&end_date=${reportEnd}&export=csv`, { responseType: 'blob' });
//       const blob = new Blob([res.data], { type: 'text/csv' });
//       const url = window.URL.createObjectURL(blob);
//       const a = document.createElement('a');
//       a.href = url;
//       a.download = `attendance_${uid}_${reportStart}_${reportEnd}.csv`;
//       document.body.appendChild(a);
//       a.click();
//       a.remove();
//       window.URL.revokeObjectURL(url);
//     } catch (err) {
//       console.error('Export failed:', err);
//       alert('Failed to export CSV');
//     }
//   }

//   useEffect(() => {
//     fetchUsers();
//   }, []);

//   const fetchUsers = async () => {
//     try {
//       setLoading(true);
//       const response = await api.get('/api/v1/users?limit=100');
//       if (response.data.status === 'success') {
//         setUsers(response.data.data.users);
//       }
//       setLoading(false);
//     } catch (error) {
//       console.error('Error fetching users:', error);
//       setLoading(false);
//     }
//   };

//   const filteredUsers = users.filter(user =>
//     user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
//     user.uid.toString().includes(searchTerm)
//   );

//   if (loading) {
//     return (
//       <div className="flex items-center justify-center h-64">
//         <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
//       </div>
//     );
//   }

//   return (
//     <div className="space-y-6">
//       {/* Header */}
//       <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
//         <div>
//           <h1 className="text-2xl font-bold text-gray-800">Employee Management</h1>
//           <p className="text-gray-600 mt-1">Manage all registered employees</p>
//         </div>
//         <button className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
//           <UserPlus className="w-5 h-5" />
//           <span>Add Employee</span>
//         </button>
//       </div>

//       {/* Search Bar & Report Filters */}
//       <div className="bg-white rounded-xl shadow-sm p-4">
//         <div className="md:flex md:items-center md:gap-4">
//           <div className="relative md:flex-1">
//             <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
//             <input
//               type="text"
//               placeholder="Search by name or UID..."
//               value={searchTerm}
//               onChange={(e) => setSearchTerm(e.target.value)}
//               className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
//             />
//           </div>

//           <div className="mt-3 md:mt-0 flex items-center gap-3">
//             <div>
//               <label className="block text-xs text-gray-500">From</label>
//               <input type="date" value={reportStart} onChange={(e) => setReportStart(e.target.value)} className="px-3 py-2 border rounded-lg" />
//             </div>
//             <div>
//               <label className="block text-xs text-gray-500">To</label>
//               <input type="date" value={reportEnd} onChange={(e) => setReportEnd(e.target.value)} className="px-3 py-2 border rounded-lg" />
//             </div>
//             <div className="text-sm text-gray-500">Select date range and click <span className="font-semibold">Export CSV</span> for a user.</div>
//           </div>
//         </div>
//       </div>

//       {/* Users Table */}
//       <div className="bg-white rounded-xl shadow-sm overflow-hidden">
//         <div className="overflow-x-auto">
//           <table className="w-full">
//             <thead className="bg-gray-50 border-b">
//               <tr>
//                 <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">UID</th>
//                 <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Name</th>
//                 <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Card No</th>
//                 <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Privilege</th>
//                 <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Status</th>
//                 <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Actions</th>
//               </tr>
//             </thead>
//             <tbody>
//               {filteredUsers.map((user) => (
//                 <tr key={user.id} className="border-b hover:bg-gray-50 transition-colors">
//                   <td className="py-4 px-6">
//                     <span className="font-mono text-sm font-semibold text-indigo-600">
//                       {user.uid}
//                     </span>
//                   </td>
//                   <td className="py-4 px-6">
//                     <div className="flex items-center space-x-3">
//                       <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-semibold">
//                         {user.name.charAt(0)}
//                       </div>
//                       <span className="font-medium text-gray-800">{user.name}</span>
//                     </div>
//                   </td>
//                   <td className="py-4 px-6 text-gray-600">
//                     {user.card_no || 'N/A'}
//                   </td>
//                   <td className="py-4 px-6">
//                     <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-semibold">
//                       Level {user.privilege}
//                     </span>
//                   </td>
//                   <td className="py-4 px-6">
//                     <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
//                       user.is_active
//                         ? 'bg-green-100 text-green-700'
//                         : 'bg-gray-100 text-gray-700'
//                     }`}>
//                       {user.is_active ? 'Active' : 'Inactive'}
//                     </span>
//                   </td>
//                   <td className="py-4 px-6">
//                     <div className="flex items-center space-x-2">
//                       <button onClick={() => exportUserCSV(user.uid)} title="Export attendance CSV" className="px-3 py-2 bg-green-50 text-green-700 rounded-lg text-sm font-semibold hover:bg-green-100 transition-colors">
//                         Export CSV
//                       </button>
//                       <button className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
//                         <Edit className="w-4 h-4" />
//                       </button>
//                       <button className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors">
//                         <Trash2 className="w-4 h-4" />
//                       </button>
//                     </div>
//                   </td>
//                 </tr>
//               ))}
//             </tbody>
//           </table>
//         </div>
//       </div>

//       {/* Stats */}
//       <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
//         <div className="bg-white rounded-xl shadow-sm p-6">
//           <p className="text-gray-500 text-sm mb-1">Total Employees</p>
//           <p className="text-3xl font-bold text-gray-800">{users.length}</p>
//         </div>
//         <div className="bg-white rounded-xl shadow-sm p-6">
//           <p className="text-gray-500 text-sm mb-1">Active</p>
//           <p className="text-3xl font-bold text-green-600">
//             {users.filter(u => u.is_active).length}
//           </p>
//         </div>
//         <div className="bg-white rounded-xl shadow-sm p-6">
//           <p className="text-gray-500 text-sm mb-1">Inactive</p>
//           <p className="text-3xl font-bold text-gray-400">
//             {users.filter(u => !u.is_active).length}
//           </p>
//         </div>
//       </div>
//     </div>
//   );
// }






// frontend/src/pages/Users.jsx
import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Search, UserPlus, Edit, Trash2, X, Save } from 'lucide-react';

function EditModal({ user, onClose, onSaved }) {
  const [form, setForm]     = useState({ name: user.name, privilege: user.privilege, card_no: user.card_no || '', is_active: user.is_active });
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState('');

  const handleSave = async () => {
    if (!form.name.trim()) return setError('Name is required');
    try {
      setSaving(true);
      const res = await api.put(`/api/v1/users/${user.uid}`, {
        name: form.name.trim(),
        privilege: Number(form.privilege),
        card_no: form.card_no || null,
        is_active: form.is_active,
      });
      if (res.data.status === 'success') {
        onSaved({ ...user, ...form });
      } else {
        setError(res.data.message || 'Save failed');
      }
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 z-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-800">Edit Employee</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input type="text" value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Card No</label>
            <input type="text" value={form.card_no} onChange={e => setForm(p => ({ ...p, card_no: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
              placeholder="Leave blank if none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Privilege Level (0-14)</label>
            <input type="number" min={0} max={14} value={form.privilege}
              onChange={e => setForm(p => ({ ...p, privilege: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
          <div className="flex items-center gap-3">
            <input type="checkbox" id="is_active" checked={form.is_active}
              onChange={e => setForm(p => ({ ...p, is_active: e.target.checked }))}
              className="w-4 h-4 accent-indigo-600" />
            <label htmlFor="is_active" className="text-sm font-medium text-gray-700">Active</label>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
        <div className="flex gap-3 mt-6">
          <button onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
          <button onClick={handleSave} disabled={saving}
            className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50">
            {saving
              ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              : <Save className="w-4 h-4" />}
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Users() {
  const [users, setUsers]             = useState([]);
  const [loading, setLoading]         = useState(true);
  const [searchTerm, setSearchTerm]   = useState('');
  const [reportStart, setReportStart] = useState('');
  const [reportEnd, setReportEnd]     = useState('');
  const [deletingUid, setDeletingUid] = useState(null);
  const [editingUser, setEditingUser] = useState(null);

  useEffect(() => { fetchUsers(); }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/v1/users?limit=500&include_inactive=false');
      if (res.data.status === 'success') setUsers(res.data.data.users);
    } catch (e) {
      console.error('Error fetching users:', e);
    } finally {
      setLoading(false);
    }
  };

  const deleteUser = async (uid, name) => {
    if (!window.confirm(`Delete "${name}" (UID: ${uid})?\n\nAttendance history will be preserved.`)) return;
    try {
      setDeletingUid(uid);
      const res = await api.delete(`/api/v1/users/${uid}`);
      if (res.data.status === 'success') {
        setUsers(prev => prev.filter(u => u.uid !== uid));
      } else {
        alert(`Failed: ${res.data.message}`);
      }
    } catch (e) {
      alert('Delete failed. Please try again.');
    } finally {
      setDeletingUid(null);
    }
  };

  const handleEditSaved = (updated) => {
    setUsers(prev => prev.map(u => u.uid === updated.uid ? { ...u, ...updated } : u));
    setEditingUser(null);
  };

  const exportUserCSV = async (uid) => {
    if (!reportStart || !reportEnd) return alert('Please select start and end date before exporting');
    try {
      const res = await api.get(
        `/api/v1/attendance/summary/${uid}?start_date=${reportStart}&end_date=${reportEnd}&export=csv`,
        { responseType: 'blob' }
      );
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `attendance_${uid}_${reportStart}_${reportEnd}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert('Failed to export CSV');
    }
  };

  const filtered = users.filter(u =>
    u.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.uid.toString().includes(searchTerm)
  );

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600" />
    </div>
  );

  return (
    <div className="space-y-6">
      {editingUser && (
        <EditModal user={editingUser} onClose={() => setEditingUser(null)} onSaved={handleEditSaved} />
      )}

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Employee Management</h1>
          <p className="text-gray-600 mt-1">Manage all registered employees</p>
        </div>
        <button className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
          <UserPlus className="w-5 h-5" />
          <span>Add Employee</span>
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-4">
        <div className="md:flex md:items-center md:gap-4">
          <div className="relative md:flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input type="text" placeholder="Search by name or UID..." value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
          </div>
          <div className="mt-3 md:mt-0 flex items-center gap-3 flex-wrap">
            <div>
              <label className="block text-xs text-gray-500">From</label>
              <input type="date" value={reportStart} onChange={e => setReportStart(e.target.value)} className="px-3 py-2 border rounded-lg" />
            </div>
            <div>
              <label className="block text-xs text-gray-500">To</label>
              <input type="date" value={reportEnd} onChange={e => setReportEnd(e.target.value)} className="px-3 py-2 border rounded-lg" />
            </div>
            <p className="text-sm text-gray-500 mt-4">Select range then click <span className="font-semibold">Export CSV</span>.</p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">UID</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Name</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Card No</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Privilege</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Status</th>
                <th className="text-left py-4 px-6 text-sm font-semibold text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(user => (
                <tr key={user.uid} className="border-b hover:bg-gray-50 transition-colors">
                  <td className="py-4 px-6">
                    <span className="font-mono text-sm font-semibold text-indigo-600">{user.uid}</span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-semibold">
                        {user.name.charAt(0).toUpperCase()}
                      </div>
                      <span className="font-medium text-gray-800">{user.name}</span>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-gray-600">{user.card_no || 'N/A'}</td>
                  <td className="py-4 px-6">
                    <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs font-semibold">
                      Level {user.privilege}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <span className="px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700">Active</span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center space-x-2">
                      <button onClick={() => exportUserCSV(user.uid)}
                        className="px-3 py-2 bg-green-50 text-green-700 rounded-lg text-sm font-semibold hover:bg-green-100 transition-colors">
                        Export CSV
                      </button>
                      <button onClick={() => setEditingUser(user)} title="Edit user"
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                        <Edit className="w-4 h-4" />
                      </button>
                      <button onClick={() => deleteUser(user.uid, user.name)}
                        disabled={deletingUid === user.uid} title="Delete user"
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50">
                        {deletingUid === user.uid
                          ? <div className="w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
                          : <Trash2 className="w-4 h-4" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No active users found{searchTerm ? ` matching "${searchTerm}"` : ''}.
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm mb-1">Total Active</p>
          <p className="text-3xl font-bold text-gray-800">{users.length}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm mb-1">Showing</p>
          <p className="text-3xl font-bold text-green-600">{filtered.length}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm mb-1">Filtered Out</p>
          <p className="text-3xl font-bold text-gray-400">{users.length - filtered.length}</p>
        </div>
      </div>
    </div>
  );
}