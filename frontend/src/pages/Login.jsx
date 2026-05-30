// frontend/src/pages/Login.jsx
// MS Softwares - Enterprise Login (Hidden Password)

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../utils/auth';
import logo from '../assets/logo.png';
import { Building2, Lock, CheckCircle, AlertCircle, Fingerprint } from 'lucide-react';

export default function Login() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Simulate a slight delay for better UX
    setTimeout(() => {
      if (login(password)) {
        navigate('/');
      } else {
        setError('Invalid password. Access denied.');
        setLoading(false);
      }
    }, 800);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800 flex items-center justify-center p-4">
      {/* Animated Background Pattern */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-white opacity-5 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-white opacity-5 rounded-full blur-3xl"></div>
      </div>

      {/* Login Card */}
      <div className="relative bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden">
        {/* Header Section */}
        <div className="bg-white px-8 py-10 text-center border-b border-gray-200">
          <div className="flex items-center justify-center mb-4">
            <img
              src={logo}
              alt="MS Softwares Logo"
              className="h-20 w-auto object-contain"
            />
          </div>
          <p className="text-gray-600 text-sm font-medium">Attendance Management System</p>
        </div>

        {/* Form Section */}
        <div className="px-8 py-8">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-semibold text-gray-800">Admin Login</h2>
            <p className="text-gray-500 text-sm mt-2">Enter your credentials to access the system</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Password Input */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setError('');
                  }}
                  className="w-full pl-12 pr-4 py-3.5 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-gray-900 placeholder-gray-400"
                  placeholder="Enter admin password"
                  required
                  disabled={loading}
                />
              </div>

              {/* Error Message */}
              {error && (
                <div className="mt-3 flex items-center gap-2 text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2.5">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <p className="text-sm font-medium">{error}</p>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading || !password}
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3.5 rounded-xl font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <Lock className="w-5 h-5" />
                  <span>Access Dashboard</span>
                </>
              )}
            </button>
          </form>

          {/* Security Features */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <div className="space-y-3">
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                </div>
                <span>Secure 256-bit encryption</span>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Fingerprint className="w-4 h-4 text-blue-600" />
                </div>
                <span>30-minute auto-logout for security</span>
              </div>
            </div>
          </div>

          {/* Help Text */}
          <div className="mt-6 text-center">
            <p className="text-xs text-gray-500">
              Need help? Contact system administrator
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-8 py-4 text-center border-t border-gray-200">
          <p className="text-xs text-gray-600">
            © 2026 MS Softwares. All rights reserved.
          </p>
        </div>
      </div>

      {/* Bottom Info */}
      <div className="absolute bottom-8 left-0 right-0 text-center">
        <p className="text-white text-sm opacity-80">
          Dual Device Attendance Management System
        </p>
      </div>
    </div>
  );
}
