# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
$ErrorActionPreference = 'Stop'
$fintraRoot = Split-Path -Parent $PSScriptRoot
$fintraData = Join-Path $fintraRoot 'team-preview'
$fintraStatePath = Join-Path $fintraData 'state.json'
if (-not (Test-Path -LiteralPath $fintraStatePath)) {
    Write-Host '이 폴더에서 실행 중인 팀 서버가 없습니다.'
    exit 0
}
$fintraState = Get-Content -LiteralPath $fintraStatePath -Encoding UTF8 | ConvertFrom-Json
$fintraListener = Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue
if ($fintraListener -and $fintraListener.OwningProcess -ne $fintraState.manager_pid) {
    throw '다른 폴더의 서버가 실행 중입니다. 실행한 Fintra 폴더에서 중지해 주세요.'
}
New-Item -ItemType File -Path (Join-Path $fintraData 'stop.request') -Force | Out-Null
Write-Host '서버를 종료하고 있습니다...'
$fintraDeadline = (Get-Date).AddSeconds(90)
do {
    $fintraPorts = @(Get-NetTCPConnection -LocalPort 8781,8788 -State Listen -ErrorAction SilentlyContinue)
    if ($fintraPorts.Count -eq 0) {
        Write-Host '서버가 종료되었습니다. 새로 접속하거나 데이터를 불러올 수 없습니다.'
        Write-Host '이미 열어둔 화면은 남아 있을 수 있습니다. 다음 Windows 로그인 시에는 자동 실행됩니다.'
        exit 0
    }
    if ((Get-Date) -gt $fintraDeadline) { throw '서버 종료를 확인하지 못했습니다. team-preview/public-service.log를 확인해 주세요.' }
    Start-Sleep -Milliseconds 500
} while ($true)
