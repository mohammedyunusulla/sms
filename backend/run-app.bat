@echo off
REM Script to start the Flask application on Windows

echo ======================================
echo    School Management System
echo    Starting Backend Server
echo ======================================

REM Check if virtual environment exists and activate it
if defined VIRTUAL_ENV (
    echo Virtual environment already activated.
) else (
    if exist "Scripts\activate.bat" (
        echo Activating virtual environment...
        call Scripts\activate.bat
    ) else (
        echo Error: Virtual environment not found!
        echo Please create a virtual environment first:
        echo   python -m venv venv
        echo   Scripts\activate
        exit /b 1
    )
)

REM Set environment variables
set FLASK_APP=run.py
set FLASK_ENV=development

echo.
echo Starting Flask development server...
echo.
echo Server will be available at:
echo   http://localhost:5000
echo   http://127.0.0.1:5000
echo.
echo Press CTRL+C to stop the server
echo.

REM Run the Flask application
python run.py
