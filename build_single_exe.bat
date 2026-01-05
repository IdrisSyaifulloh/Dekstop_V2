@echo off
REM ============================================
REM MangoDefend - Build Single EXE
REM ============================================

echo.
echo ========================================
echo   MangoDefend - Single EXE Build
echo ========================================
echo.

if not exist "main.py" (
    echo ERROR: Please run from desktop_app directory
    pause
    exit /b 1
)

echo [1/4] Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

echo [2/4] Installing dependencies...
pip install pyinstaller

echo [3/4] Building SINGLE EXE...
pyinstaller --clean --onefile ^
  --name MangoDefend ^
  --windowed ^
  --icon assets/icon.ico ^
  --add-data "models;models" ^
  --add-data "assets;assets" ^
  --add-data "config.ini;." ^
  --exclude-module PyQt6 ^
  --exclude-module PyQt5 ^
  --hidden-import uvicorn ^
  --hidden-import fastapi ^
  --hidden-import sqlite3 ^
  --hidden-import watchdog ^
  --hidden-import win10toast ^
  --hidden-import torch ^
  --hidden-import onnxruntime ^
  main.py

if errorlevel 1 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo [4/4] Done!

echo.
echo ========================================
echo   BUILD SUCCESSFUL!
echo ========================================
echo.
echo Single EXE created:
echo   dist\MangoDefend.exe
echo.
dir dist\MangoDefend.exe
echo.
echo DISTRIBUSI:
echo 1. Copy dist\MangoDefend.exe ke flash disk
echo 2. Kasih ke User 1, 2, 3
echo 3. User cukup double-click MangoDefend.exe
echo.
echo CATATAN:
echo - File size akan lebih besar (~300-500MB)
echo - Startup lebih lambat (extract temp files)
echo - Tapi SANGAT MUDAH distribusi (1 file!)
echo.
pause
