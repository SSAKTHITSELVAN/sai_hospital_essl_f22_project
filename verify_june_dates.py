#!/usr/bin/env python3
"""
Verify June attendance dates - show dates with records
"""

from app.core.database import SessionLocal
from app.models.attendance import ProcessedAttendance
from datetime import date
from sqlalchemy import func

def verify_june_dates():
    """Show which dates in June have attendance records"""
    db = SessionLocal()
    try:
        print("\n" + "="*80)
        print("📅 JUNE 2026 ATTENDANCE VERIFICATION")
        print("="*80 + "\n")
        
        # Get all dates in June with records
        june_dates = db.query(
            ProcessedAttendance.date,
            func.count(ProcessedAttendance.id).label('record_count')
        ).filter(
            ProcessedAttendance.date >= date(2026, 6, 1),
            ProcessedAttendance.date <= date(2026, 6, 26)
        ).group_by(ProcessedAttendance.date).order_by(ProcessedAttendance.date).all()
        
        if not june_dates:
            print("⚠️  No June records found\n")
            return
        
        print("Dates with attendance records:")
        print("-" * 80)
        for record_date, count in june_dates:
            day_name = record_date.strftime("%A")
            print(f"  ✅ {record_date.strftime('%d.%m.%Y')} ({day_name:10s}) - {count:3d} employees")
        
        print("\n" + "-" * 80)
        total_records = sum(count for _, count in june_dates)
        total_dates = len(june_dates)
        print(f"📊 Summary:")
        print(f"   Dates covered: {total_dates} days")
        print(f"   Total records: {total_records} employee-days")
        print(f"   Avg per day:   {total_records/total_dates:.0f} employees")
        print()
        
        # Show status breakdown
        print("Status breakdown for June:")
        print("-" * 80)
        status_summary = db.query(
            ProcessedAttendance.status,
            func.count(ProcessedAttendance.id).label('count')
        ).filter(
            ProcessedAttendance.date >= date(2026, 6, 1),
            ProcessedAttendance.date <= date(2026, 6, 26)
        ).group_by(ProcessedAttendance.status).all()
        
        for status, count in status_summary:
            status_val = status.value if hasattr(status, 'value') else str(status)
            print(f"  {status_val:15s}: {count:4d} records")
        
        print("\n" + "="*80 + "\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    verify_june_dates()
