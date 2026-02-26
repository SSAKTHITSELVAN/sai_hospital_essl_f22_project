@echo off
REM Navigate to project directory
cd /d C:\Users\user\sai_hospital_essl_f22_project

REM Activate virtual environment
call saienv\Scripts\activate.bat

REM Start the application (hidden window)
start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM Optional: Keep window open to see any immediate errors (remove in production)
REM timeout /t 5