@echo off
echo ================================================================================
echo DATABASE MIGRATION - Add Device UID Columns
echo ================================================================================
echo.

REM Activate virtual environment if it exists
if exist "saienv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call saienv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo.
echo Running migration script...
echo.

python migrate_add_device_uids.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ================================================================================
    echo ERROR: Migration failed!
    echo ================================================================================
    echo.
    echo If you see "ModuleNotFoundError", you can run the SQL script manually:
    echo.
    echo Option 1 - Using pgAdmin:
    echo   1. Open pgAdmin
    echo   2. Connect to your database
    echo   3. Open Query Tool
    echo   4. Load and run: migrate_device_uids.sql
    echo.
    echo Option 2 - Using psql command:
    echo   psql -U postgres -d your_database_name -f migrate_device_uids.sql
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo SUCCESS! Migration completed.
echo ================================================================================
echo.
echo Please restart your backend server now.
echo.
pause
