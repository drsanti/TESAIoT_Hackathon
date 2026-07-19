@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv ...
  py -3 -m venv .venv 2>nul || python -m venv .venv
  if errorlevel 1 (
    echo Failed to create venv. Install Python 3.10+ and retry.
    exit /b 1
  )
)

echo Ensuring dependencies ...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo pip install failed.
  exit /b 1
)

echo Starting TESAIoT BLE Flet app ...
".venv\Scripts\python.exe" main.py
exit /b %ERRORLEVEL%
