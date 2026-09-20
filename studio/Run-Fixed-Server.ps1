# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
$ErrorActionPreference = 'Stop'
$fintraCli = Join-Path $env:ProgramFiles 'Tailscale/tailscale.exe'
$fintraDeadline = (Get-Date).AddSeconds(90)
do {
    $fintraStatus = & $fintraCli status --json | ConvertFrom-Json
    if ($fintraStatus.BackendState -eq 'Running' -and $fintraStatus.Self.DNSName) { break }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $fintraDeadline)
if ($fintraStatus.BackendState -ne 'Running') { exit 1 }
$fintraDns = $fintraStatus.Self.DNSName.TrimEnd('.')
if ($fintraDns -notmatch '^[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+\.ts\.net$') { exit 1 }
$env:FINTRA_FIXED_ORIGIN = 'https://' + $fintraDns
$fintraHome = Join-Path $env:LOCALAPPDATA 'Fintra'
$fintraConfig = Get-Content -LiteralPath (Join-Path $fintraHome 'current.json') | ConvertFrom-Json
$fintraPython = Join-Path $fintraHome ('runtimes/' + $fintraConfig.runtime_id + '/python.exe')
Set-Location -LiteralPath $PSScriptRoot
& $fintraPython -X utf8 (Join-Path $PSScriptRoot 'tools/team_preview.py') >> (Join-Path $PSScriptRoot 'team-preview/fixed-service.log') 2>&1
exit $LASTEXITCODE
