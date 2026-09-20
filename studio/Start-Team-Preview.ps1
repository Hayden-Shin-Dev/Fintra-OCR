# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
$fintraRoot = $PSScriptRoot
$fintraPython = Join-Path $env:LOCALAPPDATA 'Fintra/runtimes/8a307c021740a0e4/python.exe'
$fintraScript = Join-Path $fintraRoot 'tools/team_preview.py'
Start-Process -FilePath $fintraPython -ArgumentList @('-X','utf8',('"'+$fintraScript+'"')) -WorkingDirectory $fintraRoot -WindowStyle Hidden
