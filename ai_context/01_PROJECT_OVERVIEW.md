# Project Overview - MS Softwares Attendance Management System

## Project Name
**MS Softwares - Dual Device Fingerprint Attendance Management System**

## Purpose
A complete attendance tracking system for Sai Hospital using two ESSL F22 fingerprint devices - one for IN punches and one for OUT punches.

## Technology Stack

### Backend
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Device Integration:** pyzk (ZKTeco library)
- **Background Tasks:** Threading, APScheduler

### Frontend
- **Framework:** React.js
- **Routing:** React Router
- **HTTP Client:** Axios
- **Icons:** Lucide React
- **Styling:** Tailwind CSS

## Project Structure

```
sai_hospital_essl_f22_project/
├── app/                          # Backend application
│   ├── api/
│   │   ├── routes/              # API endpoints
│   │   │   ├── users.py
│   │   │   ├── attendance.py
│   │   │   ├── payroll.py
│   │   │   ├── device.py
│   │   │   ├── auth.py
│   │   │   ├── lop.py
│   │   │   └── export.py
│   │   └── dependencies.py
│   ├── models/                  # Database models
│   │   ├── user.py
│   │   ├── attendance.py
│   │   └── device.py
│   ├── services/                # Business logic
│   │   ├── device_sync.py
│   │   └── attendance_processor.py
│   ├── core/                    # Core utilities
│   │   ├── database.py
│   │   ├── response.py
│   │   └── exceptions.py
│   ├── background/              # Background tasks
│   │   └── tasks.py
│   └── main.py                  # FastAPI application
├── frontend/                     # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   └── DeviceStatus.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Users.jsx
│   │   │   ├── Attendance.jsx
│   │   │   ├── Payroll.jsx
│   │   │   ├── Reports.jsx
│   │   │   └── Login.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── utils/
│   │   │   └── auth.js
│   │   └── assets/
│   │       └── logo.png
├── .env                         # Environment configuration
├── requirements.txt             # Python dependencies
└── run.py                       # Application entry point
```

## Key Features

### 1. Dual Device Architecture
- **Device 1 (192.168.1.201):** IN device at entrance
- **Device 2 (192.168.1.35):** OUT device at exit
- Separate UID tracking for each device

### 2. User Management
- Employee registration with dual device UIDs
- Privilege levels (User, Enroller, Admin, Super Admin, Manager)
- Active/Inactive status
- Device registration tracking

### 3. Attendance Processing
- Automatic punch pairing (IN → OUT)
- Session-based tracking (up to 2 sessions per day)
- Real-time status calculation
- Live timer for ongoing sessions

### 4. Payroll Integration
- LOP (Loss of Pay) calculation
- Monthly payroll generation
- Absent day tracking
- Present day calculation

### 5. Reporting
- Daily attendance reports
- Monthly summaries
- Excel export functionality
- User-specific reports

## Hardware Integration

### ESSL F22 Fingerprint Devices
- **Protocol:** ZKTeco ADMS protocol
- **Connection:** TCP/IP (LAN)
- **Communication:** Push-based (webhook) and Pull-based (sync)
- **Data:** User info, fingerprint templates, attendance logs

### Network Configuration
- Both devices on same local network
- Static IP addresses assigned
- Port 4370 (default ZKTeco port)
- Backend server accessible to both devices

## Database Schema

### Core Tables
1. **users** - Employee information
2. **attendance_logs** - Raw punch data from devices
3. **processed_attendance** - Daily attendance summaries
4. **devices** - Device status and sync logs

## Authentication & Security
- Session-based authentication
- 30-minute session expiry
- Password hint system
- JWT token storage in localStorage
- Protected API routes with middleware

## Deployment
- **Development:** Local development server
- **Production:** Can be deployed on any Linux server
- **Access:** Local network (LAN) or cloud-hosted
