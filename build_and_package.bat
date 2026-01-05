@echo off
REM ============================================
REM MangoDefend - Build & Package Script
REM ============================================

echo.
echo ========================================
echo   MangoDefend - Build Script
echo ========================================
echo.

REM Check if in correct directory
if not exist "main.py" (
    echo ERROR: Please run this script from desktop_app directory
    pause
    exit /b 1
)

echo [1/5] Cleaning previous build...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "MangoDefend.spec" del MangoDefend.spec

echo [2/5] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo [3/5] Building EXE with PyInstaller...
pyinstaller --clean --onedir ^
  --name MangoDefend ^
  --windowed ^
  --icon assets/icon.ico ^
  --add-data "models;models" ^
  --add-data "assets;assets" ^
  --add-data "config.ini;." ^
  --hidden-import uvicorn ^
  --hidden-import fastapi ^
  --hidden-import sqlite3 ^
  --hidden-import watchdog ^
  --hidden-import win10toast ^
  --hidden-import torch ^
  --hidden-import onnxruntime ^
  main.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo [4/5] Copying additional files...
copy README.md dist\MangoDefend\ 2>nul
copy DISTRIBUTION_GUIDE.md dist\MangoDefend\ 2>nul

echo [5/5] Creating distribution package...
cd dist
powershell Compress-Archive -Path MangoDefend -DestinationPath MangoDefend_v1.0.zip -Force
cd ..

echo.
echo ========================================
echo   BUILD SUCCESSFUL!
echo ========================================
echo.
echo Distribution package created:
echo   dist\MangoDefend_v1.0.zip
echo.
echo Folder size: 
dir dist\MangoDefend_v1.0.zip
echo.
echo Next steps:
echo 1. Test the EXE: dist\MangoDefend\MangoDefend.exe
echo 2. Share MangoDefend_v1.0.zip to users
echo 3. Users extract and run MangoDefend.exe
echo.
pause
