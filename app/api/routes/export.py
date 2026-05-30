# app/api/routes/export.py
"""
Export API Routes - MS Excel Compatible
────────────────────────────────────────────────────────────────────────────────

Endpoints for exporting attendance and payroll data to Excel (.xlsx)
Compatible with Microsoft Office, Google Sheets, LibreOffice
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date, datetime

from app.core.database import get_db
from app.core.response import success_response, error_response
from app.services.excel_export import ExcelExportService

router = APIRouter(prefix="/api/v1/export", tags=["Export"])


@router.get("/today-attendance")
def export_today_attendance(db: Session = Depends(get_db)):
    """
    Export today's attendance to Excel (.xlsx).

    Returns:
        Excel file download with today's attendance data
    """
    try:
        export_service = ExcelExportService(db)
        excel_file = export_service.export_today_attendance()

        filename = f"Attendance_{date.today().strftime('%Y%m%d')}.xlsx"

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payroll-report")
def export_payroll_report(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Export payroll report to Excel (.xlsx).

    Args:
        start_date: Start date of the period
        end_date: End date of the period

    Returns:
        Excel file download with payroll summary
    """
    try:
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        export_service = ExcelExportService(db)
        excel_file = export_service.export_payroll_report(start_date, end_date)

        filename = f"Payroll_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.xlsx"

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detailed-attendance/{uid}")
def export_detailed_attendance(
    uid: int,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Export detailed attendance for a specific user to Excel (.xlsx).

    Args:
        uid: User UID
        start_date: Start date of the period
        end_date: End date of the period

    Returns:
        Excel file download with detailed attendance data
    """
    try:
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        export_service = ExcelExportService(db)
        excel_file = export_service.export_detailed_attendance(uid, start_date, end_date)

        filename = f"Attendance_UID{uid}_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.xlsx"

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
