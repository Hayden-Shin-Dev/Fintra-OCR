# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
$fintraRoot = $PSScriptRoot
$fintraHome = Join-Path $env:LOCALAPPDATA 'Fintra'
$fintraConfig = Get-Content -LiteralPath (Join-Path $fintraHome 'current.json') | ConvertFrom-Json
$fintraPython = Join-Path $fintraHome ('runtimes/' + $fintraConfig.runtime_id + '/python.exe')
$fintraScript = Join-Path $fintraRoot 'tools/team_preview.py'
Start-Process -FilePath $fintraPython -ArgumentList @('-X','utf8',('"'+$fintraScript+'"')) -WorkingDirectory $fintraRoot -WindowStyle Hidden
