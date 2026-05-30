-- Migration: Add device_1_uid and device_2_uid columns to users table
-- Run this SQL script directly in your PostgreSQL database

-- Add device_1_uid column
ALTER TABLE users ADD COLUMN IF NOT EXISTS device_1_uid INTEGER;

-- Add device_2_uid column
ALTER TABLE users ADD COLUMN IF NOT EXISTS device_2_uid INTEGER;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS ix_users_device_1_uid ON users(device_1_uid);
CREATE INDEX IF NOT EXISTS ix_users_device_2_uid ON users(device_2_uid);

-- Populate device_1_uid from existing uid for all users
UPDATE users SET device_1_uid = uid WHERE device_1_uid IS NULL;

-- Make name column unique (only if not already unique)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_name_unique'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_name_unique UNIQUE (name);
    END IF;
END $$;

-- Show results
SELECT
    COUNT(*) as total_users,
    COUNT(device_1_uid) as with_device1_uid,
    COUNT(device_2_uid) as with_device2_uid
FROM users;

-- Display sample of updated data
SELECT id, uid, device_1_uid, device_2_uid, name
FROM users
LIMIT 10;
