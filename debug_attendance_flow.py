#!/usr/bin/env python3
"""
Comprehensive attendance flow diagnostic
Checks: Users, Raw Logs, Processed Attendance
"""

from app.core.database import SessionLocal
from app.models.user import User
from app.models.attendance import AttendanceLog, ProcessedAttendance
from app.services.attendance_processor import AttendanceProcessor
from datetime import datetime, date
from sqlalchemy import func
import json

def check_users():
    """Check if users are synced with device UIDs"""
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        print("\n" + "="*80)
        print("👥 USERS SYNC STATUS")
        print("="*80)
        print(f"Total active users: {len(users)}\n")
        
        for user in users[:10]:  # Show first 10
            print(f"  {user.name}")
            print(f"    UID (primary):   {user.uid}")
            print(f"    Device 1 UID:    {user.device_1_uid}")
            print(f"    Device 2 UID:    {user.device_2_uid}")
            print()
        
        if len(users) > 10:
            print(f"... and {len(users) - 10} more users\n")
            
    finally:
        db.close()


def check_raw_logs():
    """Check if attendance logs are being synced"""
    db = SessionLocal()
    try:
        total_logs = db.query(AttendanceLog).count()
        today = date.today()
        
        logs_today = db.query(AttendanceLog).filter(
            func.date(AttendanceLog.timestamp) == today
        ).all()
        
        print("="*80)
        print("📋 RAW ATTENDANCE LOGS STATUS")
        print("="*80)
        print(f"Total logs in DB:  {total_logs}")
        print(f"Logs from TODAY:   {len(logs_today)}\n")
        
        if logs_today:
            print("Recent logs from today:")
            for log in logs_today[-10:]:  # Show last 10
                user = db.query(User).filter(User.uid == log.uid).first()
                device_type = "IN (Device 1)" if log.device_ip == "192.168.1.201" else "OUT (Device 2)" if log.device_ip == "192.168.1.35" else "UNKNOWN"
                print(f"  {log.timestamp} | {user.name if user else 'UNKNOWN'} | {device_type} | {log.device_ip}")
            print()
        else:
            print("⚠️  NO LOGS FOUND FOR TODAY!\n")
        
        # Check device_ip distribution
        device_1_logs = db.query(AttendanceLog).filter(
            AttendanceLog.device_ip == "192.168.1.201"
        ).count()
        device_2_logs = db.query(AttendanceLog).filter(
            AttendanceLog.device_ip == "192.168.1.35"
        ).count()
        null_device = db.query(AttendanceLog).filter(
            AttendanceLog.device_ip.is_(None)
        ).count()
        
        print(f"Device IP distribution:")
        print(f"  Device 1 (192.168.1.201): {device_1_logs} logs")
        print(f"  Device 2 (192.168.1.35):  {device_2_logs} logs")
        print(f"  NULL/Unknown:             {null_device} logs")
        print()
        
    finally:
        db.close()


def check_processed_attendance():
    """Check if processed attendance records exist"""
    db = SessionLocal()
    try:
        today = date.today()
        
        processed_today = db.query(ProcessedAttendance).filter(
            ProcessedAttendance.date == today
        ).all()
        
        total_processed = db.query(ProcessedAttendance).count()
        
        print("="*80)
        print("✅ PROCESSED ATTENDANCE STATUS")
        print("="*80)
        print(f"Total processed records: {total_processed}")
        print(f"Processed records TODAY: {len(processed_today)}\n")
        
        if processed_today:
            print("Today's processed attendance:")
            for rec in processed_today:
                user = db.query(User).filter(User.uid == rec.uid).first()
                sessions = []
                if rec.punch_sessions:
                    try:
                        sessions = json.loads(rec.punch_sessions)
                    except:
                        pass
                
                print(f"  {user.name if user else 'UNKNOWN'}")
                print(f"    Status:           {rec.status}")
                print(f"    Work Hours:       {rec.work_duration_hours}")
                print(f"    Shift Type:       {rec.shift}")
                print(f"    First IN:         {rec.first_in}")
                print(f"    Last OUT:         {rec.last_out}")
                print(f"    Sessions:         {len(sessions)}")
                print(f"    Remarks:          {rec.remarks}")
                print()
        else:
            print("⚠️  NO PROCESSED RECORDS FOR TODAY!\n")
            
    finally:
        db.close()


def test_processor():
    """Test the attendance processor on a sample user"""
    db = SessionLocal()
    try:
        today = date.today()
        
        # Get a user with logs from today
        user_with_logs = db.query(User).join(AttendanceLog).filter(
            func.date(AttendanceLog.timestamp) == today
        ).first()
        
        if not user_with_logs:
            print("\n" + "="*80)
            print("🔧 PROCESSOR TEST")
            print("="*80)
            print("⚠️  No users with logs today to test processor\n")
            return
        
        print("\n" + "="*80)
        print("🔧 PROCESSOR TEST")
        print("="*80)
        print(f"Testing with user: {user_with_logs.name} (UID: {user_with_logs.uid})\n")
        
        processor = AttendanceProcessor(db)
        result = processor.process_user_date(user_with_logs.uid, today)
        
        print(f"Process result: {result}\n")
        
        # Check the created/updated record
        processed = db.query(ProcessedAttendance).filter(
            ProcessedAttendance.uid == user_with_logs.uid,
            ProcessedAttendance.date == today,
        ).first()
        
        if processed:
            print(f"Created/Updated record:")
            print(f"  Status:         {processed.status}")
            print(f"  Work Hours:     {processed.work_duration_hours}")
            print(f"  First IN:       {processed.first_in}")
            print(f"  Last OUT:       {processed.last_out}")
            print(f"  Total Punches:  {processed.total_punches}")
            print(f"  Remarks:        {processed.remarks}\n")
        
    finally:
        db.close()


def main():
    print("\n🔍 ATTENDANCE SYSTEM DIAGNOSTIC")
    print("="*80)
    
    check_users()
    check_raw_logs()
    check_processed_attendance()
    test_processor()
    
    print("="*80)
    print("✅ Diagnostic complete\n")


if __name__ == "__main__":
    main()
