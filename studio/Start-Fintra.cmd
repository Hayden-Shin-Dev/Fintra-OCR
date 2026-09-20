@echo off
REM 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
cd /d "%~dp0"
powershell -NoProfile -Command "$h=Join-Path $env:LOCALAPPDATA 'Fintra'; $c=Get-Content (Join-Path $h 'current.json') | ConvertFrom-Json; $p=Join-Path $h ('runtimes\'+$c.runtime_id+'\python.exe'); & $p -X utf8 run.py"
pause
