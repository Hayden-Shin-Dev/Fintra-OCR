@echo off
cd /d "%~dp0"
set "FINTRA_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%FINTRA_PYTHON%" set "FINTRA_PYTHON=%USERPROFILE%\.cache\fintraocr-venv\Scripts\python.exe"
if not exist "%FINTRA_PYTHON%" (echo Python environment missing. See README.md & pause & exit /b 1)
"%FINTRA_PYTHON%" launch_ui.py
if errorlevel 1 pause
