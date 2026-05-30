// frontend/src/components/DeviceStatus.jsx
// MS Softwares - Dual Device Status Display

import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

export default function DeviceStatus() {
  const [deviceInfo, setDeviceInfo] = useState({
    device_1: null,
    device_2: null
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchDeviceInfo();
    // Refresh every 30 seconds
    const interval = setInterval(fetchDeviceInfo, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDeviceInfo = async () => {
    try {
      const response = await api.get('/api/v1/device/info');
      if (response.data.status === 'success') {
        setDeviceInfo(response.data.data);
      }
    } catch (error) {
      console.error('Error fetching device info:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDeviceInfo();
  };

  const DeviceCard = ({ device, deviceNum, deviceType }) => {
    const isOnline = device && device.ip;

    return (
      <div className={`bg-white rounded-lg border-2 p-4 ${isOnline ? 'border-green-200' : 'border-red-200'}`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {isOnline ? (
              <Wifi className="w-5 h-5 text-green-600" />
            ) : (
              <WifiOff className="w-5 h-5 text-red-600" />
            )}
            <span className="font-semibold text-gray-900">Device {deviceNum}</span>
          </div>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
            isOnline ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {isOnline ? 'Online' : 'Offline'}
          </span>
        </div>

        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Type:</span>
            <span className="font-medium text-gray-900">{deviceType}</span>
          </div>
          {isOnline ? (
            <>
              <div className="flex justify-between">
                <span className="text-gray-600">IP:</span>
                <span className="font-mono text-gray-900">{device.ip}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Serial:</span>
                <span className="font-mono text-gray-900 text-xs">{device.serial_number || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Firmware:</span>
                <span className="text-gray-900 text-xs">{device.firmware_version || 'N/A'}</span>
              </div>
            </>
          ) : (
            <div className="text-center py-2 text-red-600 text-xs">
              Device is unreachable
            </div>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Device Status</h2>
          <p className="text-sm text-gray-600 mt-1">Dual ESSL F22 Devices</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <DeviceCard
          device={deviceInfo.device_1}
          deviceNum={1}
          deviceType="IN Device (Entry)"
        />
        <DeviceCard
          device={deviceInfo.device_2}
          deviceNum={2}
          deviceType="OUT Device (Exit)"
        />
      </div>

      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
        <p className="text-xs text-gray-600">
          <span className="font-medium">Note:</span> Device 1 records all IN punches | Device 2 records all OUT punches
        </p>
      </div>
    </div>
  );
}
