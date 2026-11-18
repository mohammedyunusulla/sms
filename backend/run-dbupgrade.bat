@echo off
echo ====================================
echo   School Management System
echo   Database Upgrade
echo ====================================

REM Set environment variables
set FLASK_APP=run.py
set FLASK_ENV=development

echo.
echo Setting up Python environment...
REM Activate virtual environment if it exists
if exist Scripts\activate.bat (
    call Scripts\activate.bat
    echo Virtual environment activated.
) else (
    echo Warning: Virtual environment not found. Using system Python.
)

echo.
echo Checking current database revision...
flask db current

echo.
echo Showing pending migrations...
flask db show

echo.
echo Applying database migrations...
flask db init
flask db migrate
flask db upgrade

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo Database upgrade completed successfully!
    echo ====================================
    echo.
    echo Current database revision:
    flask db current
    
    echo.
    echo Database is now ready for use.
    echo You can start the application with: python run.py
) else (
    echo.
    echo ====================================
    echo Database upgrade failed!
    echo ====================================
    echo Please check the error messages above.
    echo You may need to resolve conflicts manually.
)

echo.
pause