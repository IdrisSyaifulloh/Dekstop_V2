@echo off
setlocal EnableDelayedExpansion
title MangoDefend - Installer Builder

cd /d "%~dp0"

echo.
echo ============================================
echo   MangoDefend - Installer Builder
echo ============================================
echo.

if not exist "main.py" (
    echo ERROR: Run this script from the MangoDefend repo root.
    pause
    exit /b 1
)

set "PYTHON="
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if exist "venv\Scripts\python.exe" set "PYTHON=venv\Scripts\python.exe"

if "%PYTHON%"=="" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python was not found. Install Python 3.11 or activate a virtualenv.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if "%ISCC%"=="" (
    echo ERROR: Inno Setup 6 was not found.
    echo Install it from https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)

if not exist "assets\icon.ico" (
    echo [1/6] Generating icon.ico...
    %PYTHON% -c "from PIL import Image; img=Image.open('assets/mango_icon.png').convert('RGBA'); sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]; imgs=[img.resize(s,Image.LANCZOS) for s in sizes]; imgs[0].save('assets/icon.ico',format='ICO',sizes=sizes,append_images=imgs[1:])"
    if errorlevel 1 (
        echo ERROR: Failed to generate assets\icon.ico.
        pause
        exit /b 1
    )
) else (
    echo [1/6] icon.ico already exists.
)

echo [2/6] Installing Python dependencies...
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)

echo [3/6] Cleaning previous build output...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "installer\MangoDefend" rmdir /s /q "installer\MangoDefend"
if not exist "installer" mkdir "installer"

echo [4/6] Building app with PyInstaller...
%PYTHON% -m PyInstaller --clean --noconfirm MangoDefend.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

if not exist "dist\MangoDefend\MangoDefend.exe" (
    echo ERROR: dist\MangoDefend\MangoDefend.exe was not created.
    pause
    exit /b 1
)

echo [5/6] Preparing Inno Setup source folder...
xcopy "dist\MangoDefend" "installer\MangoDefend" /E /I /Y >nul
if errorlevel 1 (
    echo ERROR: Failed to copy dist\MangoDefend to installer\MangoDefend.
    pause
    exit /b 1
)

if not exist "installer\vc_redist.x64.exe" (
    echo WARNING: installer\vc_redist.x64.exe is missing.
    echo Download the Microsoft Visual C++ Redistributable x64 and place it there,
    echo or remove the vc_redist entry from installer\MangoDefend_Setup.iss.
    pause
    exit /b 1
)

echo [6/6] Building setup installer with Inno Setup...
pushd "installer"
"%ISCC%" "MangoDefend_Setup.iss"
set "ISCC_EXIT=%ERRORLEVEL%"
popd

if not "%ISCC_EXIT%"=="0" (
    echo ERROR: Inno Setup build failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   INSTALLER BUILD SUCCESSFUL
echo ============================================
echo   Output: installer\dist\MangoDefend_Setup.exe
echo ============================================
echo.
pause
