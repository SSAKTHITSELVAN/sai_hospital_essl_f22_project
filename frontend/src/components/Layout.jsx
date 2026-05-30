// frontend/src/components/Layout.jsx
// MS Softwares - Enterprise Layout with Dual Device Status

import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { logout } from '../utils/auth';
import api from '../services/api';
import logo from '../assets/logo.png';
import {
  LayoutDashboard,
  Users,
  Clock,
  DollarSign,
  FileText,
  LogOut,
  Menu,
  X,
  Wifi,
  WifiOff,
  RefreshCw,
  Building2
} from 'lucide-react';

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [deviceStatus, setDeviceStatus] = useState({
    device_1: { online: false, info: null },
    device_2: { online: false, info: null },
    loading: true,
    lastChecked: null
  });
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/users', icon: Users, label: 'Employees' },
    { path: '/attendance', icon: Clock, label: 'Attendance' },
    { path: '/payroll', icon: DollarSign, label: 'Payroll' },
    { path: '/reports', icon: FileText, label: 'Reports' },
  ];

  // Check both devices status
  const checkDeviceStatus = async () => {
    try {
      setDeviceStatus(prev => ({ ...prev, loading: true }));

      const response = await api.get('/api/v1/device/info');

      if (response.data.status === 'success' && response.data.data) {
        const data = response.data.data;

        setDeviceStatus({
          device_1: {
            online: data.device_1 && data.device_1.ip ? true : false,
            info: data.device_1 || null
          },
          device_2: {
            online: data.device_2 && data.device_2.ip ? true : false,
            info: data.device_2 || null
          },
          loading: false,
          lastChecked: new Date()
        });
      } else {
        setDeviceStatus({
          device_1: { online: false, info: null },
          device_2: { online: false, info: null },
          loading: false,
          lastChecked: new Date()
        });
      }
    } catch (error) {
      console.error('Device status check failed:', error);
      setDeviceStatus({
        device_1: { online: false, info: null },
        device_2: { online: false, info: null },
        loading: false,
        lastChecked: new Date()
      });
    }
  };

  // Check device status on mount and every 30 seconds
  useEffect(() => {
    checkDeviceStatus();

    const interval = setInterval(() => {
      checkDeviceStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const formatLastChecked = () => {
    if (!deviceStatus.lastChecked) return '';

    const now = new Date();
    const diff = Math.floor((now - deviceStatus.lastChecked) / 1000);

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  };

  const DeviceStatusSidebar = () => (
    <div className="border-t p-4">
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-3">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-700 flex items-center gap-1">
            <Wifi className="w-3 h-3" />
            Device Status
          </span>
          <button
            onClick={checkDeviceStatus}
            disabled={deviceStatus.loading}
            className="text-gray-500 hover:text-gray-700 disabled:opacity-50"
            title="Refresh status"
          >
            <RefreshCw className={`w-3 h-3 ${deviceStatus.loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Device 1 */}
        <div className="mb-2 bg-white rounded p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-gray-600">Device 1 (IN)</span>
            <div className="flex items-center gap-1">
              {deviceStatus.device_1.online ? (
                <>
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs text-green-600 font-medium">Online</span>
                </>
              ) : (
                <>
                  <div className="w-2 h-2 bg-red-500 rounded-full" />
                  <span className="text-xs text-red-600 font-medium">Offline</span>
                </>
              )}
            </div>
          </div>
          {deviceStatus.device_1.info && (
            <div className="text-xs text-gray-500 font-mono">
              {deviceStatus.device_1.info.ip}
            </div>
          )}
        </div>

        {/* Device 2 */}
        <div className="bg-white rounded p-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-gray-600">Device 2 (OUT)</span>
            <div className="flex items-center gap-1">
              {deviceStatus.device_2.online ? (
                <>
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs text-green-600 font-medium">Online</span>
                </>
              ) : (
                <>
                  <div className="w-2 h-2 bg-red-500 rounded-full" />
                  <span className="text-xs text-red-600 font-medium">Offline</span>
                </>
              )}
            </div>
          </div>
          {deviceStatus.device_2.info && (
            <div className="text-xs text-gray-500 font-mono">
              {deviceStatus.device_2.info.ip}
            </div>
          )}
        </div>

        {deviceStatus.lastChecked && (
          <div className="mt-2 text-xs text-gray-400 text-center">
            Updated {formatLastChecked()}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar for Desktop */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-white shadow-lg hidden lg:block border-r border-gray-200">
        {/* Company Header */}
        <div className="p-6 border-b border-gray-200 bg-white">
          <div className="flex items-center justify-center mb-2">
            <img
              src={logo}
              alt="MS Softwares Logo"
              className="h-16 w-auto object-contain"
            />
          </div>
          <p className="text-xs text-gray-600 text-center font-medium">Attendance Management System</p>
        </div>

        <nav className="p-4 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 font-semibold shadow-sm'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-blue-600' : ''}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Device Status in Sidebar */}
        <div className="absolute bottom-16 left-0 right-0">
          <DeviceStatusSidebar />
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={handleLogout}
            className="flex items-center space-x-3 w-full px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition-colors font-medium"
          >
            <LogOut className="w-5 h-5" />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Mobile Sidebar */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setSidebarOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 bg-white shadow-lg">
            {/* Company Header */}
            <div className="p-6 border-b border-gray-200 bg-white flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center justify-center mb-2">
                  <img
                    src={logo}
                    alt="MS Softwares Logo"
                    className="h-14 w-auto object-contain"
                  />
                </div>
                <p className="text-xs text-gray-600 text-center font-medium">Attendance System</p>
              </div>
              <button onClick={() => setSidebarOpen(false)} className="text-gray-600 hover:text-gray-800 ml-2">
                <X className="w-6 h-6" />
              </button>
            </div>

            <nav className="p-4 space-y-1">
              {menuItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setSidebarOpen(false)}
                    className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-all ${
                      isActive
                        ? 'bg-blue-50 text-blue-700 font-semibold shadow-sm'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className={`w-5 h-5 ${isActive ? 'text-blue-600' : ''}`} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Device Status in Mobile Sidebar */}
            <div className="absolute bottom-16 left-0 right-0">
              <DeviceStatusSidebar />
            </div>

            <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 bg-gray-50">
              <button
                onClick={handleLogout}
                className="flex items-center space-x-3 w-full px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition-colors font-medium"
              >
                <LogOut className="w-5 h-5" />
                <span>Logout</span>
              </button>
            </div>
          </aside>
        </div>
      )}

      {/* Main Content */}
      <div className="lg:ml-64">
        {/* Top Bar */}
        <header className="bg-white shadow-sm sticky top-0 z-10 border-b border-gray-200">
          <div className="flex items-center justify-between px-6 py-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 hover:bg-gray-100 rounded-lg"
            >
              <Menu className="w-6 h-6" />
            </button>

            <div className="flex-1 lg:flex-none lg:hidden">
              <h2 className="text-xl font-semibold text-gray-800">
                {menuItems.find(item => item.path === location.pathname)?.label || 'Dashboard'}
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">MS Softwares</p>
            </div>

            <div className="flex items-center space-x-4">
              {/* Dual Device Status Indicator in Header (for desktop) */}
              <div className="hidden lg:flex items-center space-x-3">
                {/* Device 1 */}
                <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
                  {deviceStatus.device_1.online ? (
                    <>
                      <Wifi className="w-4 h-4 text-green-600" />
                      <div>
                        <span className="text-xs font-medium text-green-700">Device 1</span>
                        <p className="text-xs text-gray-500">IN • Online</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-4 h-4 text-red-600" />
                      <div>
                        <span className="text-xs font-medium text-red-700">Device 1</span>
                        <p className="text-xs text-gray-500">IN • Offline</p>
                      </div>
                    </>
                  )}
                </div>

                {/* Device 2 */}
                <div className="flex items-center space-x-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
                  {deviceStatus.device_2.online ? (
                    <>
                      <Wifi className="w-4 h-4 text-green-600" />
                      <div>
                        <span className="text-xs font-medium text-green-700">Device 2</span>
                        <p className="text-xs text-gray-500">OUT • Online</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-4 h-4 text-red-600" />
                      <div>
                        <span className="text-xs font-medium text-red-700">Device 2</span>
                        <p className="text-xs text-gray-500">OUT • Offline</p>
                      </div>
                    </>
                  )}
                </div>

                <button
                  onClick={checkDeviceStatus}
                  disabled={deviceStatus.loading}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50 transition-colors"
                  title="Refresh device status"
                >
                  <RefreshCw className={`w-4 h-4 ${deviceStatus.loading ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {/* User Profile */}
              <div className="flex items-center space-x-3 pl-4 border-l border-gray-200">
                <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-full flex items-center justify-center text-white font-bold shadow-sm">
                  A
                </div>
                <div className="hidden md:block">
                  <p className="text-sm font-semibold text-gray-900">Admin</p>
                  <p className="text-xs text-gray-500">MS Softwares</p>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6">
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-white border-t border-gray-200 py-4 px-6 mt-8">
          <div className="flex flex-col md:flex-row justify-between items-center text-sm text-gray-600">
            <p>© 2026 MS Softwares. All rights reserved.</p>
            <p className="mt-2 md:mt-0">Dual Device Attendance Management System</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
