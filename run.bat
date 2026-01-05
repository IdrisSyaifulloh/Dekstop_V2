@echo off
echo Starting RMAV Desktop Application...
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Virtual environment not found. Creating one...
    python -m venv venv
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate

REM Check if requirements are installed
echo Checking dependencies...
pip show PySide6 >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    echo.
)

REM Run the application
echo Launching application...
python main.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit...
    pause >nul
)
