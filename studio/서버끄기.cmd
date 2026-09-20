@echo off
REM Author: Shin Mincheol, email: min.developer.acc@gmail.com
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\StopServer.ps1"
if errorlevel 1 (
  echo Fintra command failed. Review the error above.
  pause
  exit /b 1
)
pause
