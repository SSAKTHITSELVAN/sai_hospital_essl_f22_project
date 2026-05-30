-- Migration: Add device_ip column to attendance_logs table
-- Purpose: Track which device (IN or OUT) each punch came from
-- Date: 2026-05-30

-- Add device_ip column
ALTER TABLE attendance_logs
ADD COLUMN IF NOT EXISTS device_ip VARCHAR(50);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_attendance_logs_device_ip
ON attendance_logs(device_ip);

-- Optionally: Set default values for existing records
-- (If you have existing data and want to mark it as from Device 1)
-- UPDATE attendance_logs
-- SET device_ip = '192.168.1.201'
-- WHERE device_ip IS NULL;

-- Verify
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'attendance_logs'
  AND column_name = 'device_ip';
