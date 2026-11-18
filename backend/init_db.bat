@echo off
echo ====================================
echo   School Management System
echo   1. Activating and Setting Up Environment
echo   2. Installing Dependencies from requirements.txt
echo ====================================

REM Set environment variables
set FLASK_APP=run.py
set FLASK_ENV=development

echo.
echo [1] Setting up Python environment...
REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Virtual environment activated.
) else (
    echo Warning: Virtual environment not found. Using system Python.
    echo Consider creating a virtual environment: python -m venv venv
)

echo.
echo [2] Installing dependencies...
pip install -r requirements.txt

echo.
echo Installation complete 