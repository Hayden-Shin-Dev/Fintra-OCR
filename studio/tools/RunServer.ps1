# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
$ErrorActionPreference = 'Stop'
$fintraRoot = Split-Path -Parent $PSScriptRoot
Remove-Item Env:FINTRA_FIXED_ORIGIN -ErrorAction SilentlyContinue
$env:FINTRA_PUBLISH_LINK = '1'
$fintraHome = Join-Path $env:LOCALAPPDATA 'Fintra'
$fintraConfig = Get-Content -LiteralPath (Join-Path $fintraHome 'current.json') | ConvertFrom-Json
$fintraPython = Join-Path $fintraHome ('runtimes/' + $fintraConfig.runtime_id + '/python.exe')
Set-Location -LiteralPath $fintraRoot
& $fintraPython -X utf8 (Join-Path $fintraRoot 'tools/service_runner.py')
exit $LASTEXITCODE
