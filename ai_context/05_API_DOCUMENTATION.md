# API Documentation

## Base URL
```
http://localhost:8000  (Development)
http://<server-ip>:8000  (Production)
```

## Response Format

### Success Response
```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "data": { ... },
  "error": null
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Error description",
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "details": "Detailed error information"
  }
}
```

---

## Authentication

### Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "password": "admin_password"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "token": "jwt_token_here",
    "user": {
      "username": "admin",
      "role": "admin"
    }
  }
}
```

### Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer <token>
```

---

## Users API

### List All Users
```http
GET /api/v1/users?skip=0&limit=1000&include_inactive=false
Authorization: Bearer <token>
```

**Query Parameters:**
- `skip` (int, default=0): Pagination offset
- `limit` (int, default=100, max=10000): Number of records
- `include_inactive` (bool, default=false): Include soft-deleted users

**Response:**
```json
{
  "status": "success",
  "message": "Retrieved 25 users",
  "data": {
    "users": [
      {
        "id": 1,
        "uid": 7,
        "device_1_uid": 7,
        "device_2_uid": 15,
        "name": "Amudha",
        "privilege": 0,
        "card_no": null,
        "is_active": true,
        "created_at": "2026-05-30T12:00:00"
      }
    ],
    "pagination": {
      "skip": 0,
      "limit": 1000,
      "total": 25
    }
  }
}
```

### Get User by UID
```http
GET /api/v1/users/{uid}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "User found",
  "data": {
    "id": 1,
    "uid": 7,
    "device_1_uid": 7,
    "device_2_uid": 15,
    "name": "Amudha",
    "privilege": 0,
    "card_no": null,
    "group_id": "",
    "is_active": true,
    "created_at": "2026-05-30T12:00:00",
    "updated_at": "2026-05-30T12:00:00"
  }
}
```

### Update User
```http
PUT /api/v1/users/{uid}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Amudha Updated",
  "privilege": 2,
  "card_no": "12345",
  "is_active": true
}
```

### Delete User (Soft Delete)
```http
DELETE /api/v1/users/{uid}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "User 'Amudha' (UID 7) deleted successfully",
  "data": {
    "uid": 7,
    "name": "Amudha"
  }
}
```

---

## Attendance API

### Get Processed Attendance
```http
GET /api/v1/attendance/processed?start_date=2026-05-30&end_date=2026-05-30&limit=1000
Authorization: Bearer <token>
```

**Query Parameters:**
- `uid` (int, optional): Filter by user UID
- `start_date` (date, optional): Start date (YYYY-MM-DD)
- `end_date` (date, optional): End date (YYYY-MM-DD)
- `skip` (int, default=0): Pagination offset
- `limit` (int, default=100, max=10000): Number of records

**Response:**
```json
{
  "status": "success",
  "message": "Retrieved 25 processed attendance records",
  "data": {
    "records": [
      {
        "id": 1,
        "uid": 7,
        "user_name": "Amudha",
        "date": "2026-05-30",
        "sessions": [
          {
            "in": "2026-05-30T09:00:00",
            "out": "2026-05-30T18:00:00"
          }
        ],
        "shift": "Regular",
        "first_in": "2026-05-30T09:00:00",
        "last_out": "2026-05-30T18:00:00",
        "work_duration_hours": 9.0,
        "overtime_hours": 0.0,
        "status": "present",
        "total_punches": 2,
        "is_finalized": true,
        "remarks": null
      }
    ],
    "pagination": {
      "skip": 0,
      "limit": 1000,
      "total": 25
    }
  }
}
```

### Get Today's Attendance
```http
GET /api/v1/attendance/today
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Today's attendance: 25 users",
  "data": {
    "date": "2026-05-30",
    "total_users": 25,
    "records": [
      {
        "uid": 7,
        "user_name": "Amudha",
        "name": "Amudha",
        "shift": "Regular",
        "first_in": "2026-05-30T09:00:00",
        "last_out": "2026-05-30T18:00:00",
        "status": "present",
        "work_duration_hours": 9.0,
        "overtime_hours": 0.0,
        "is_finalized": true,
        "punch_sessions": "[{\"in\": \"2026-05-30T09:00:00\", \"out\": \"2026-05-30T18:00:00\"}]"
      }
    ]
  }
}
```

### Get Attendance Logs (Raw)
```http
GET /api/v1/attendance/logs?uid=7&start_date=2026-05-30&end_date=2026-05-30
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Retrieved 2 attendance logs",
  "data": {
    "logs": [
      {
        "id": 1,
        "uid": 7,
        "timestamp": "2026-05-30T09:00:00",
        "punch_type": 0,
        "status": 0,
        "device_id": "192.168.1.201"
      },
      {
        "id": 2,
        "uid": 7,
        "timestamp": "2026-05-30T18:00:00",
        "punch_type": 1,
        "status": 0,
        "device_id": "192.168.1.35"
      }
    ],
    "pagination": {
      "skip": 0,
      "limit": 100,
      "total": 2
    }
  }
}
```

### Get User Attendance Summary
```http
GET /api/v1/attendance/summary/{uid}?start_date=2026-05-01&end_date=2026-05-31&detailed=true
Authorization: Bearer <token>
```

**Query Parameters:**
- `start_date` (date, required): Start date
- `end_date` (date, required): End date
- `detailed` (bool, default=false): Include daily breakdown
- `export` (string, optional): "csv" for CSV export

**Response:**
```json
{
  "status": "success",
  "message": "Attendance summary generated",
  "data": {
    "user": {
      "uid": 7,
      "name": "Amudha"
    },
    "period": {
      "start_date": "2026-05-01",
      "end_date": "2026-05-31"
    },
    "summary": {
      "total_days": 31,
      "present_days": 22,
      "half_days": 3,
      "absent_days": 6,
      "total_work_hours": 198.5,
      "total_overtime": 2.5
    },
    "months": [
      {
        "month": "2026-05",
        "days": [
          {
            "date": "2026-05-01",
            "status": "present",
            "first_in": "09:00:00",
            "last_out": "18:00:00",
            "work_hours": 9.0,
            "overtime": 0.0
          }
        ]
      }
    ]
  }
}
```

### Process Attendance
```http
POST /api/v1/attendance/process?force=false
Authorization: Bearer <token>
```

**Query Parameters:**
- `uid` (int, optional): Process specific user
- `target_date` (date, optional): Process specific date
- `force` (bool, default=false): Force reprocess finalized records

**Response:**
```json
{
  "status": "success",
  "message": "Pending attendance processed",
  "data": {
    "processed": 15,
    "skipped": 2,
    "errors": 0
  }
}
```

### Get Attendance Statistics
```http
GET /api/v1/attendance/stats?start_date=2026-05-01&end_date=2026-05-31
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Attendance statistics retrieved",
  "data": {
    "period": {
      "start_date": "2026-05-01",
      "end_date": "2026-05-31"
    },
    "statistics": {
      "total_records": 775,
      "present": 550,
      "half_day": 150,
      "incomplete": 50,
      "total_work_hours": 4950.0,
      "total_overtime_hours": 125.0,
      "average_work_hours": 6.39
    },
    "percentages": {
      "present": 70.97,
      "half_day": 19.35,
      "incomplete": 6.45
    }
  }
}
```

---

## Device API

### Get Device Status
```http
GET /api/v1/device/info
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Device information retrieved",
  "data": {
    "device_1": {
      "device_num": 1,
      "device_type": "IN Device",
      "ip": "192.168.1.201",
      "port": 4370,
      "firmware_version": "Ver 6.60",
      "serial_number": "ESSL-F22-001",
      "platform": "ZEM560",
      "device_name": "IN Device",
      "mac_address": "00:17:61:XX:XX:XX"
    },
    "device_2": {
      "device_num": 2,
      "device_type": "OUT Device",
      "ip": "192.168.1.35",
      "port": 4370,
      "firmware_version": "Ver 6.60",
      "serial_number": "ESSL-F22-002",
      "platform": "ZEM560",
      "device_name": "OUT Device",
      "mac_address": "00:17:61:XX:XX:YY"
    }
  }
}
```

### Manual Sync Trigger
```http
POST /api/v1/device/sync
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Dual device sync completed successfully",
  "data": {
    "timestamp": "2026-05-30T15:30:00",
    "users": {
      "total_unique_names": 25,
      "device_1_users": 25,
      "device_2_users": 23,
      "added": 2,
      "updated": 23
    },
    "logs": {
      "total": 45,
      "device_1_logs": 25,
      "device_2_logs": 20,
      "new": 45,
      "duplicates": 0,
      "skipped_unknown": 0,
      "errors": 0
    },
    "processed_attendance": {
      "processed": 25,
      "skipped": 0,
      "errors": 0
    }
  }
}
```

---

## Payroll API

### Get Monthly Payroll
```http
GET /api/v1/payroll/monthly?month=2026-05&per_day_salary=500
Authorization: Bearer <token>
```

**Query Parameters:**
- `month` (string, required): Month in YYYY-MM format
- `per_day_salary` (float, default=500): Daily salary rate

**Response:**
```json
{
  "status": "success",
  "message": "Payroll calculated for 2026-05",
  "data": {
    "month": "2026-05",
    "total_days": 31,
    "working_days": 31,
    "per_day_salary": 500,
    "employees": [
      {
        "uid": 7,
        "name": "Amudha",
        "present_days": 22,
        "half_days": 3,
        "absent_days": 6,
        "lop_days": 6,
        "payable_days": 23.5,
        "salary": 11750.0
      }
    ],
    "summary": {
      "total_employees": 25,
      "total_salary": 293750.0
    }
  }
}
```

### Get User Payroll
```http
GET /api/v1/payroll/user/{uid}?month=2026-05
Authorization: Bearer <token>
```

---

## LOP API

### Get LOP Records
```http
GET /api/v1/lop?start_date=2026-05-01&end_date=2026-05-31
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "LOP records retrieved",
  "data": {
    "records": [
      {
        "uid": 7,
        "name": "Amudha",
        "date": "2026-05-15",
        "reason": "No attendance recorded"
      }
    ],
    "total": 6
  }
}
```

### Run LOP Check
```http
POST /api/v1/lop/check?date=2026-05-30
Authorization: Bearer <token>
```

**Response:**
```json
{
  "status": "success",
  "message": "LOP check completed",
  "data": {
    "date": "2026-05-30",
    "total_users": 25,
    "marked_lop": 3,
    "details": [
      {
        "uid": 10,
        "name": "John Doe",
        "marked_lop": true
      }
    ]
  }
}
```

---

## Export API

### Export Today's Attendance
```http
GET /api/v1/export/today-attendance?date=2026-05-30
Authorization: Bearer <token>
```

**Response:** Excel file download

### Export Monthly Payroll
```http
GET /api/v1/export/monthly-payroll?month=2026-05
Authorization: Bearer <token>
```

**Response:** Excel file download

---

## Health Check

### API Health
```http
GET /api/health
```

**Response:**
```json
{
  "status": "success",
  "message": "System is healthy",
  "data": {
    "database": "connected",
    "background_sync": "running",
    "lop_check": "scheduled at 7 AM daily"
  },
  "error": null
}
```

### Root Endpoint
```http
GET /
```

**Response:** Serves frontend (if built) or API info

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or expired token |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error - Server exception |

---

## Rate Limiting

Currently: No rate limiting implemented
Recommended for production: 100 requests/minute per IP

---

## Pagination

Default pagination:
- `skip`: 0
- `limit`: 100
- `max_limit`: 10000

Example:
```http
GET /api/v1/users?skip=0&limit=50
GET /api/v1/users?skip=50&limit=50
```

---

## Date Format

All dates use ISO 8601 format:
- Date: `YYYY-MM-DD` (e.g., "2026-05-30")
- DateTime: `YYYY-MM-DDTHH:MM:SS` (e.g., "2026-05-30T15:30:00")
- Timezone: All times in UTC or local server time
