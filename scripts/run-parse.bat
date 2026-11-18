@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"

if "%~1"=="" (
    echo Drag one eNSP .topo file onto this script.
    pause
    exit /b 1
)

if not exist "%~f1" (
    echo File not found: %~f1
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH. Install Python 3.9 or newer first.
    pause
    exit /b 1
)

set "OUT=%~dp1ensp-out\%~n1"
python "%~dp0ensp_topology.py" "%~f1" -o "%OUT%"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" echo Output folder: %OUT%
pause
exit /b %RC%
