@echo off
REM Author: Shin Mincheol | min.developer.acc@gmail.com
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Stop-Team-Preview.ps1"
if errorlevel 1 (
  echo Fintra command failed. Review the error above.
  pause
  exit /b 1
)
pause
