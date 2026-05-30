# Database Schema Documentation

## Database: PostgreSQL

## Tables Overview

```
┌────────────────┐
│     users      │ ──┐
└────────────────┘   │
                     │ (FK: uid)
┌────────────────┐   │
│attendance_logs │ ──┤
└────────────────┘   │
                     │
┌────────────────┐   │
│   processed_   │ ──┘
│  attendance    │
└────────────────┘

┌────────────────┐
│    devices     │ (Independent)
└────────────────┘
```

---

## Table: `users`

**Purpose:** Store employee information with dual device UIDs

### Schema
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    uid INTEGER UNIQUE NOT NULL,
    device_1_uid INTEGER,
    device_2_uid INTEGER,
    name VARCHAR(100) UNIQUE NOT NULL,
    privilege INTEGER DEFAULT 0,
    password VARCHAR(50),
    group_id VARCHAR(50),
    user_id_str VARCHAR(50),
    card_no VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_users_uid ON users(uid);
CREATE INDEX ix_users_device_1_uid ON users(device_1_uid);
CREATE INDEX ix_users_device_2_uid ON users(device_2_uid);
CREATE INDEX ix_users_name ON users(name);
```

### Columns

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| uid | INTEGER | Primary UID (usually device_1_uid) |
| device_1_uid | INTEGER | UID on Device 1 (IN device) |
| device_2_uid | INTEGER | UID on Device 2 (OUT device) |
| name | VARCHAR(100) | Employee name (unique identifier) |
| privilege | INTEGER | User privilege level (0=User, 1=Enroller, 2=Admin, 3=Super Admin, 14=Manager) |
| password | VARCHAR(50) | Device password (if any) |
| group_id | VARCHAR(50) | Group/department ID |
| user_id_str | VARCHAR(50) | String representation of user ID |
| card_no | VARCHAR(50) | RFID card number (if used) |
| is_active | BOOLEAN | Active status (false = soft deleted) |
| created_at | TIMESTAMP | Registration date |
| updated_at | TIMESTAMP | Last modification date |

### Sample Data
```sql
INSERT INTO users VALUES
(1, 7, 7, 15, 'Amudha', 0, '', '', '7', NULL, TRUE, NOW(), NOW()),
(2, 8, 8, 16, 'Babyraju', 0, '', '', '8', NULL, TRUE, NOW(), NOW()),
(3, 9, 9, NULL, 'Neelakutty', 0, '', '', '9', NULL, TRUE, NOW(), NOW());
```

### Key Points
- **Name is unique:** Used for matching across devices
- **device_1_uid & device_2_uid:** May differ, can be NULL if not registered on that device
- **uid:** Primary identifier, typically = device_1_uid
- **is_active:** Soft delete flag, false = user deleted but history preserved

---

## Table: `attendance_logs`

**Purpose:** Raw punch data from devices (immutable)

### Schema
```sql
CREATE TABLE attendance_logs (
    id SERIAL PRIMARY KEY,
    uid INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    punch_type INTEGER,
    status INTEGER,
    device_ip VARCHAR(15),
    device_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

CREATE INDEX ix_attendance_logs_uid ON attendance_logs(uid);
CREATE INDEX ix_attendance_logs_timestamp ON attendance_logs(timestamp);
CREATE INDEX ix_attendance_logs_device_ip ON attendance_logs(device_ip);
```

### Columns

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| uid | INTEGER | User UID (FK to users.uid) |
| timestamp | TIMESTAMP | Punch time |
| punch_type | INTEGER | Type from device (0=Check-in, 1=Check-out, etc.) |
| status | INTEGER | Verification status from device |
| device_ip | VARCHAR(15) | Which device recorded this (192.168.1.201 or 192.168.1.35) |
| device_id | VARCHAR(50) | Device serial/ID |
| created_at | TIMESTAMP | When record was created in DB |

### Sample Data
```sql
-- Morning IN punches from Device 1
INSERT INTO attendance_logs VALUES
(1, 7, '2026-05-30 09:00:00', 0, 0, '192.168.1.201', 'DEV001', NOW()),
(2, 8, '2026-05-30 08:30:00', 0, 0, '192.168.1.201', 'DEV001', NOW());

-- Evening OUT punches from Device 2
INSERT INTO attendance_logs VALUES
(3, 7, '2026-05-30 18:00:00', 1, 0, '192.168.1.35', 'DEV002', NOW()),
(4, 8, '2026-05-30 17:30:00', 1, 0, '192.168.1.35', 'DEV002', NOW());
```

### Key Points
- **Immutable:** Never updated after creation
- **device_ip is critical:** Determines if punch is IN or OUT
- **punch_type ignored:** System uses device_ip instead
- **Duplicate prevention:** Check (uid, timestamp, device_ip) before insert

---

## Table: `processed_attendance`

**Purpose:** Daily attendance summary after processing logs

### Schema
```sql
CREATE TABLE processed_attendance (
    id SERIAL PRIMARY KEY,
    uid INTEGER NOT NULL,
    date DATE NOT NULL,
    first_in TIMESTAMP,
    last_out TIMESTAMP,
    work_duration_hours FLOAT,
    overtime_hours FLOAT DEFAULT 0.0,
    status VARCHAR(20),
    punch_sessions TEXT,
    shift VARCHAR(50),
    total_punches INTEGER,
    remarks TEXT,
    is_finalized BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (uid) REFERENCES users(uid),
    UNIQUE(uid, date)
);

CREATE INDEX ix_processed_attendance_uid ON processed_attendance(uid);
CREATE INDEX ix_processed_attendance_date ON processed_attendance(date);
CREATE INDEX ix_processed_attendance_status ON processed_attendance(status);
```

### Columns

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| uid | INTEGER | User UID (FK to users.uid) |
| date | DATE | Attendance date (logical date) |
| first_in | TIMESTAMP | First IN punch of the day |
| last_out | TIMESTAMP | Last OUT punch of the day |
| work_duration_hours | FLOAT | Total work hours |
| overtime_hours | FLOAT | Overtime hours (if > 9) |
| status | VARCHAR(20) | PRESENT, HALF_DAY, INCOMPLETE, ABSENT, PRESENT_OT, LOP |
| punch_sessions | TEXT | JSON array of sessions: [{"in": "...", "out": "..."}, ...] |
| shift | VARCHAR(50) | "Regular" or "Break Shift" |
| total_punches | INTEGER | Total number of punches |
| remarks | TEXT | Processing notes (duplicates, orphans, etc.) |
| is_finalized | BOOLEAN | Locked for editing (true after 1hr from last_out) |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

### Sample Data
```sql
-- Regular full day
INSERT INTO processed_attendance VALUES
(1, 7, '2026-05-30', '2026-05-30 09:00:00', '2026-05-30 18:00:00', 
 9.0, 0.0, 'present', 
 '[{"in": "2026-05-30T09:00:00", "out": "2026-05-30T18:00:00"}]',
 'Regular', 2, NULL, TRUE, NOW(), NOW());

-- Half day
INSERT INTO processed_attendance VALUES
(2, 8, '2026-05-30', '2026-05-30 08:30:00', '2026-05-30 14:00:00', 
 5.5, 0.0, 'half_day', 
 '[{"in": "2026-05-30T08:30:00", "out": "2026-05-30T14:00:00"}]',
 'Regular', 2, NULL, FALSE, NOW(), NOW());

-- Break shift (2 sessions)
INSERT INTO processed_attendance VALUES
(3, 9, '2026-05-30', '2026-05-30 09:00:00', '2026-05-30 18:00:00', 
 8.0, 0.0, 'half_day', 
 '[{"in": "2026-05-30T09:00:00", "out": "2026-05-30T13:00:00"}, 
   {"in": "2026-05-30T14:00:00", "out": "2026-05-30T18:00:00"}]',
 'Break Shift', 4, NULL, TRUE, NOW(), NOW());
```

### Key Points
- **Unique constraint on (uid, date):** One record per user per day
- **punch_sessions is JSON:** Frontend parses to show IN-1, OUT-1, etc.
- **status values:** present, present_ot, half_day, incomplete, absent, lop
- **is_finalized:** Prevents reprocessing old records
- **Updated on each processing:** Uses UPSERT logic

---

## Table: `devices`

**Purpose:** Track device connection status and sync history

### Schema
```sql
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    device_ip VARCHAR(15) UNIQUE NOT NULL,
    device_port INTEGER,
    device_name VARCHAR(100),
    serial_number VARCHAR(100),
    firmware_version VARCHAR(50),
    last_sync_at TIMESTAMP,
    last_sync_status VARCHAR(20),
    last_sync_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_devices_ip ON devices(device_ip);
```

### Columns

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| device_ip | VARCHAR(15) | Device IP address (unique) |
| device_port | INTEGER | Connection port (usually 4370) |
| device_name | VARCHAR(100) | Device name from hardware |
| serial_number | VARCHAR(100) | Device serial number |
| firmware_version | VARCHAR(50) | Firmware version |
| last_sync_at | TIMESTAMP | Last successful sync time |
| last_sync_status | VARCHAR(20) | 'success' or 'failed' |
| last_sync_message | TEXT | Sync result message or error |
| created_at | TIMESTAMP | First seen |
| updated_at | TIMESTAMP | Last update |

### Sample Data
```sql
INSERT INTO devices VALUES
(1, '192.168.1.201', 4370, 'IN Device', 'ESSL-001', 'Ver 6.60', 
 NOW(), 'success', 'Synced 25 users, 15 logs', NOW(), NOW()),
(2, '192.168.1.35', 4370, 'OUT Device', 'ESSL-002', 'Ver 6.60', 
 NOW(), 'success', 'Synced 23 users, 12 logs', NOW(), NOW());
```

### Key Points
- **device_ip is unique:** One record per device
- **Updated by sync service:** After each sync attempt
- **Used for monitoring:** Frontend shows device online/offline status

---

## Enum Types

### AttendanceStatus (Python Enum)
```python
class AttendanceStatus(enum.Enum):
    PRESENT = "present"
    PRESENT_OT = "present_ot"
    HALF_DAY = "half_day"
    INCOMPLETE = "incomplete"
    ABSENT = "absent"
    LOP = "lop"
```

Stored as VARCHAR in database.

---

## Indexes

### Performance Indexes
```sql
-- Users
CREATE INDEX ix_users_uid ON users(uid);
CREATE INDEX ix_users_device_1_uid ON users(device_1_uid);
CREATE INDEX ix_users_device_2_uid ON users(device_2_uid);
CREATE INDEX ix_users_name ON users(name);

-- Attendance Logs
CREATE INDEX ix_attendance_logs_uid ON attendance_logs(uid);
CREATE INDEX ix_attendance_logs_timestamp ON attendance_logs(timestamp);
CREATE INDEX ix_attendance_logs_device_ip ON attendance_logs(device_ip);

-- Processed Attendance
CREATE INDEX ix_processed_attendance_uid ON processed_attendance(uid);
CREATE INDEX ix_processed_attendance_date ON processed_attendance(date);
CREATE INDEX ix_processed_attendance_status ON processed_attendance(status);

-- Devices
CREATE INDEX ix_devices_ip ON devices(device_ip);
```

### Query Optimization
- **Date range queries:** Use `ix_processed_attendance_date`
- **User lookups:** Use `ix_users_uid` or `ix_users_name`
- **Device matching:** Use `ix_users_device_1_uid` and `ix_users_device_2_uid`
- **Log queries:** Use composite (uid, timestamp) for best performance

---

## Foreign Key Constraints

```sql
ALTER TABLE attendance_logs 
    ADD CONSTRAINT fk_attendance_logs_uid 
    FOREIGN KEY (uid) REFERENCES users(uid);

ALTER TABLE processed_attendance 
    ADD CONSTRAINT fk_processed_attendance_uid 
    FOREIGN KEY (uid) REFERENCES users(uid);
```

**Note:** ON DELETE behavior not set (default RESTRICT) - prevents deleting users with attendance history

---

## Common Queries

### Get today's attendance
```sql
SELECT pa.*, u.name
FROM processed_attendance pa
JOIN users u ON pa.uid = u.uid
WHERE pa.date = CURRENT_DATE
ORDER BY u.name;
```

### Get user's monthly summary
```sql
SELECT 
    date,
    status,
    work_duration_hours,
    punch_sessions
FROM processed_attendance
WHERE uid = 7 
    AND date >= '2026-05-01' 
    AND date <= '2026-05-31'
ORDER BY date;
```

### Find incomplete sessions
```sql
SELECT pa.*, u.name
FROM processed_attendance pa
JOIN users u ON pa.uid = u.uid
WHERE pa.status = 'incomplete'
    AND pa.date = CURRENT_DATE;
```

### Users not registered on both devices
```sql
SELECT name, device_1_uid, device_2_uid
FROM users
WHERE is_active = TRUE
    AND (device_1_uid IS NULL OR device_2_uid IS NULL);
```

---

## Migration Notes

### Adding device_1_uid and device_2_uid (Migration)
```sql
-- Add columns
ALTER TABLE users ADD COLUMN device_1_uid INTEGER;
ALTER TABLE users ADD COLUMN device_2_uid INTEGER;

-- Create indexes
CREATE INDEX ix_users_device_1_uid ON users(device_1_uid);
CREATE INDEX ix_users_device_2_uid ON users(device_2_uid);

-- Populate from existing uid
UPDATE users SET device_1_uid = uid WHERE device_1_uid IS NULL;

-- Make name unique
ALTER TABLE users ADD CONSTRAINT users_name_unique UNIQUE (name);
```

---

## Backup & Maintenance

### Daily Backup
```bash
pg_dump -U postgres sai_hospital_attendance > backup_$(date +%Y%m%d).sql
```

### Cleanup Old Logs (Optional)
```sql
-- Delete logs older than 1 year
DELETE FROM attendance_logs 
WHERE created_at < NOW() - INTERVAL '1 year';
```

### Vacuum & Analyze
```sql
VACUUM ANALYZE users;
VACUUM ANALYZE attendance_logs;
VACUUM ANALYZE processed_attendance;
```
