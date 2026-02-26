


// frontend/src/components/Layout.jsx
import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { logout } from '../utils/auth';
import api from '../services/api';
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
  RefreshCw
} from 'lucide-react';

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [deviceStatus, setDeviceStatus] = useState({
    online: false,
    loading: true,
    info: null,
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
    { path: '/users', icon: Users, label: 'Users' },
    { path: '/attendance', icon: Clock, label: 'Attendance' },
    { path: '/payroll', icon: DollarSign, label: 'Payroll' },
    { path: '/reports', icon: FileText, label: 'Reports' },
  ];

  // Check device status
  const checkDeviceStatus = async () => {
    try {
      setDeviceStatus(prev => ({ ...prev, loading: true }));
      
      const response = await api.get('/api/v1/device/info');
      
      if (response.data.status === 'success' && response.data.data) {
        setDeviceStatus({
          online: true,
          loading: false,
          info: response.data.data,
          lastChecked: new Date()
        });
      } else {
        setDeviceStatus({
          online: false,
          loading: false,
          info: null,
          lastChecked: new Date()
        });
      }
    } catch (error) {
      console.error('Device status check failed:', error);
      setDeviceStatus({
        online: false,
        loading: false,
        info: null,
        lastChecked: new Date()
      });
    }
  };

  // Check device status on mount and every 30 seconds
  useEffect(() => {
    checkDeviceStatus();
    
    const interval = setInterval(() => {
      checkDeviceStatus();
    }, 30000); // Check every 30 seconds

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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar for Desktop */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-white shadow-lg hidden lg:block">
        <div className="p-6 border-b">
          <h1 className="text-2xl font-bold text-indigo-600">MTask</h1>
          <p className="text-sm text-gray-500 mt-1">Attendance Management</p>
        </div>
        
        <nav className="p-4 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-600 font-semibold'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Device Status in Sidebar */}
        <div className="absolute bottom-16 left-0 right-0 p-4 border-t">
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-600">Device Status</span>
              <button
                onClick={checkDeviceStatus}
                disabled={deviceStatus.loading}
                className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
                title="Refresh status"
              >
                <RefreshCw className={`w-3 h-3 ${deviceStatus.loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
            
            <div className="flex items-center space-x-2">
              {deviceStatus.loading ? (
                <>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
                  <span className="text-xs text-gray-500">Checking...</span>
                </>
              ) : deviceStatus.online ? (
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
            
            {deviceStatus.info && (
              <div className="mt-2 text-xs text-gray-500">
                <div className="truncate">IP: {deviceStatus.info.ip || 'N/A'}</div>
                <div className="truncate">SN: {deviceStatus.info.serial_number || 'N/A'}</div>
              </div>
            )}
            
            {deviceStatus.lastChecked && (
              <div className="mt-1 text-xs text-gray-400">
                {formatLastChecked()}
              </div>
            )}
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t">
          <button
            onClick={handleLogout}
            className="flex items-center space-x-3 w-full px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
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
            <div className="p-6 border-b flex justify-between items-center">
              <div>
                <h1 className="text-2xl font-bold text-indigo-600">MTask</h1>
                <p className="text-sm text-gray-500 mt-1">Attendance Management</p>
              </div>
              <button onClick={() => setSidebarOpen(false)}>
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
                    className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-indigo-50 text-indigo-600 font-semibold'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Device Status in Mobile Sidebar */}
            <div className="absolute bottom-16 left-0 right-0 p-4 border-t">
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-gray-600">Device Status</span>
                  <button
                    onClick={checkDeviceStatus}
                    disabled={deviceStatus.loading}
                    className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3 h-3 ${deviceStatus.loading ? 'animate-spin' : ''}`} />
                  </button>
                </div>
                
                <div className="flex items-center space-x-2">
                  {deviceStatus.loading ? (
                    <>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
                      <span className="text-xs text-gray-500">Checking...</span>
                    </>
                  ) : deviceStatus.online ? (
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
                
                {deviceStatus.info && (
                  <div className="mt-2 text-xs text-gray-500">
                    <div className="truncate">IP: {deviceStatus.info.ip || 'N/A'}</div>
                    <div className="truncate">SN: {deviceStatus.info.serial_number || 'N/A'}</div>
                  </div>
                )}
                
                {deviceStatus.lastChecked && (
                  <div className="mt-1 text-xs text-gray-400">
                    {formatLastChecked()}
                  </div>
                )}
              </div>
            </div>

            <div className="absolute bottom-0 left-0 right-0 p-4 border-t">
              <button
                onClick={handleLogout}
                className="flex items-center space-x-3 w-full px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
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
        <header className="bg-white shadow-sm sticky top-0 z-10">
          <div className="flex items-center justify-between px-6 py-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden"
            >
              <Menu className="w-6 h-6" />
            </button>
            
            <div className="flex-1 lg:flex-none">
              <h2 className="text-xl font-semibold text-gray-800">
                {menuItems.find(item => item.path === location.pathname)?.label || 'Dashboard'}
              </h2>
            </div>

            <div className="flex items-center space-x-4">
              {/* Device Status Indicator in Header (for desktop) */}
              <div className="hidden lg:flex items-center space-x-2 px-3 py-2 bg-gray-50 rounded-lg">
                {deviceStatus.loading ? (
                  <>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
                    <span className="text-sm text-gray-500">Checking...</span>
                  </>
                ) : deviceStatus.online ? (
                  <>
                    <Wifi className="w-4 h-4 text-green-600" />
                    <span className="text-sm text-green-600 font-medium">Device Online</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-4 h-4 text-red-600" />
                    <span className="text-sm text-red-600 font-medium">Device Offline</span>
                  </>
                )}
                <button
                  onClick={checkDeviceStatus}
                  disabled={deviceStatus.loading}
                  className="ml-2 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  title="Refresh status"
                >
                  <RefreshCw className={`w-4 h-4 ${deviceStatus.loading ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {/* User Profile */}
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-white font-semibold">
                  A
                </div>
                <span className="hidden md:block text-sm font-medium">Admin</span>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
}