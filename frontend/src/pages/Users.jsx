// frontend/src/pages/Users.jsx
// MS Softwares - Employee Management (Simplified)

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Search, Users as UsersIcon, CheckCircle, XCircle } from 'lucide-react';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredUsers, setFilteredUsers] = useState([]);

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    // Filter users based on search query (by name or UID)
    if (!searchQuery.trim()) {
      setFilteredUsers(users);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = users.filter(user =>
        user.name.toLowerCase().includes(query) ||
        user.uid.toString().includes(query)
      );
      setFilteredUsers(filtered);
    }
  }, [searchQuery, users]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/users?limit=1000');
      if (response.data.status === 'success') {
        setUsers(response.data.data.users || []);
        setFilteredUsers(response.data.data.users || []);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  const getPrivilegeBadge = (privilege) => {
    const badges = {
      0: { label: 'User', class: 'bg-gray-100 text-gray-800 border-gray-200' },
      1: { label: 'Enroller', class: 'bg-blue-100 text-blue-800 border-blue-200' },
      2: { label: 'Admin', class: 'bg-purple-100 text-purple-800 border-purple-200' },
      3: { label: 'Super Admin', class: 'bg-red-100 text-red-800 border-red-200' },
      14: { label: 'Manager', class: 'bg-indigo-100 text-indigo-800 border-indigo-200' },
    };
    const badge = badges[privilege] || badges[0];
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${badge.class}`}>
        {badge.label}
      </span>
    );
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
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
      <div className="flex justify-between items-center">
        <div>
          <p className="text-sm text-gray-500 uppercase tracking-wide font-semibold mb-1">Employee Directory</p>
          <p className="text-gray-600">All employees including admin & staff</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-blue-100 rounded-lg">
          <UsersIcon className="w-5 h-5 text-blue-600" />
          <span className="font-semibold text-blue-900">{users.length} Total Employees</span>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="Search by name or UID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
        </div>
        {searchQuery && (
          <p className="text-sm text-gray-600 mt-2">
            Found {filteredUsers.length} employee{filteredUsers.length !== 1 ? 's' : ''}
          </p>
        )}
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  UID
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Employee Name
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Privilege
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                  Date Added
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center text-gray-500">
                      <UsersIcon className="w-12 h-12 mb-3 text-gray-400" />
                      <p className="text-lg font-medium">No employees found</p>
                      <p className="text-sm mt-1">
                        {searchQuery ? 'Try a different search term' : 'No employees registered yet'}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.uid} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm font-mono font-medium text-gray-900">
                        {user.uid}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <span className="text-blue-700 font-semibold text-sm">
                            {user.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{user.name}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getPrivilegeBadge(user.privilege)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {user.is_active ? (
                        <span className="flex items-center gap-2 text-green-700">
                          <CheckCircle className="w-4 h-4" />
                          <span className="text-sm font-medium">Active</span>
                        </span>
                      ) : (
                        <span className="flex items-center gap-2 text-red-700">
                          <XCircle className="w-4 h-4" />
                          <span className="text-sm font-medium">Inactive</span>
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                      {formatDate(user.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer Summary */}
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-blue-900">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">
              {users.filter(u => u.is_active).length} Active Employees
            </span>
          </div>
          <div className="flex items-center gap-2 text-gray-600">
            <XCircle className="w-5 h-5" />
            <span className="font-medium">
              {users.filter(u => !u.is_active).length} Inactive
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
