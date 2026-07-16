@echo off
setlocal
set ROOT=%~dp0
set LAB=%~1
if "%LAB%"=="" (
  echo Usage: run_lab.cmd ^<lab-number-or-folder^>
  echo Example: run_lab.cmd 01
  echo          run_lab.cmd 03_gatt_ops
  exit /b 1
)
cd /d "%ROOT%"
if "%LAB:~1,1%"=="" (
  rem single digit pad
  set LAB=0%LAB%
)
for /d %%D in ("labs\%LAB%_*") do (
  if exist "%%D\lab.py" (
    python "%%D\lab.py" %2 %3 %4 %5
    exit /b %ERRORLEVEL%
  )
)
if exist "labs\%LAB%\lab.py" (
  python "labs\%LAB%\lab.py" %2 %3 %4 %5
  exit /b %ERRORLEVEL%
)
echo Lab not found: %LAB%
exit /b 1
