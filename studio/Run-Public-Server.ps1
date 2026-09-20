# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
$ErrorActionPreference = 'Stop'
Remove-Item Env:FINTRA_FIXED_ORIGIN -ErrorAction SilentlyContinue
$env:FINTRA_PUBLISH_LINK = '1'
$fintraHome = Join-Path $env:LOCALAPPDATA 'Fintra'
$fintraConfig = Get-Content -LiteralPath (Join-Path $fintraHome 'current.json') | ConvertFrom-Json
$fintraPython = Join-Path $fintraHome ('runtimes/' + $fintraConfig.runtime_id + '/python.exe')
Set-Location -LiteralPath $PSScriptRoot
& $fintraPython -X utf8 (Join-Path $PSScriptRoot 'tools/team_preview.py') >> (Join-Path $PSScriptRoot 'team-preview/public-service.log') 2>&1
exit $LASTEXITCODE
