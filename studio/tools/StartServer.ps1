# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
$ErrorActionPreference = 'Stop'
$fintraRoot = Split-Path -Parent $PSScriptRoot
$fintraData = Join-Path $fintraRoot 'team-preview'
$fintraUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$fintraTaskName = 'Fintra Fixed URL Server'
function Wait-FintraReady {
    $fintraDeadline = (Get-Date).AddSeconds(100)
    Write-Host '서버와 고정 접속 링크를 준비하고 있습니다...'
    do {
        try {
            $fintraCurrent = Get-Content -LiteralPath (Join-Path $fintraData 'state.json') -Encoding UTF8 | ConvertFrom-Json
            $fintraManager = Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue
            if ($fintraCurrent.status -eq 'running' -and $fintraCurrent.manager_pid -eq $fintraManager.OwningProcess) {
                $fintraHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8781/api/public-health' -TimeoutSec 3
                if ($fintraHealth.online) {
                    $fintraPublicHealth = Invoke-RestMethod -Uri ($fintraCurrent.url + '/api/public-health') -TimeoutSec 5
                    if (-not $fintraPublicHealth.online -or $fintraPublicHealth.service -ne 'fintra') { throw 'Public connection is not ready.' }
                    $fintraFile = Invoke-RestMethod -Uri ('https://api.github.com/repos/Hayden-Shin-Dev/Fintra-OCR/contents/endpoint.json?ref=fintra-live&t=' + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -TimeoutSec 10
                    $fintraEndpoint = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($fintraFile.content)) | ConvertFrom-Json
                    if ($fintraEndpoint.online -and $fintraEndpoint.origin -eq $fintraCurrent.url) {
                        Write-Host '서버가 시작되었습니다. 이 창은 닫아도 됩니다.'
                        Write-Host 'https://hayden-shin-dev.github.io/Fintra-OCR/'
                        return
                    }
                }
            }
        } catch { }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $fintraDeadline)
    throw '서버 또는 공유 링크 준비를 확인하지 못했습니다. team-preview/public-service.log를 확인해 주세요.'
}
$fintraListener = Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue
if ($fintraListener) {
    $fintraState = Get-Content -LiteralPath (Join-Path $fintraData 'state.json') | ConvertFrom-Json
    if ($fintraState.manager_pid -ne $fintraListener.OwningProcess) { throw 'Port 8788 belongs to another process.' }
    if ($fintraState.provider -eq 'cloudflare' -and $fintraState.status -eq 'running') {
        try { Wait-FintraReady; exit 0 }
        catch { Write-Host '기존 연결이 응답하지 않아 서버를 다시 시작합니다.' }
    }
    New-Item -ItemType File -Path (Join-Path $fintraData 'stop.request') -Force | Out-Null
    $fintraDeadline = (Get-Date).AddSeconds(60)
    while (Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue) {
        if ((Get-Date) -gt $fintraDeadline) { throw 'Existing server did not stop.' }
        Start-Sleep -Milliseconds 500
    }
}
$fintraAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + (Join-Path $fintraRoot 'tools/RunServer.ps1') + '"') -WorkingDirectory $fintraRoot
$fintraTrigger = New-ScheduledTaskTrigger -AtLogOn -User $fintraUser
$fintraPrincipal = New-ScheduledTaskPrincipal -UserId $fintraUser -LogonType Interactive -RunLevel Limited
$fintraSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName $fintraTaskName -Action $fintraAction -Trigger $fintraTrigger -Principal $fintraPrincipal -Settings $fintraSettings -Force | Out-Null
$fintraTaskDeadline = (Get-Date).AddSeconds(60)
while ((Get-ScheduledTask -TaskName $fintraTaskName).State -eq 'Running') {
    if ((Get-Date) -gt $fintraTaskDeadline) { throw '이전 서버 종료 처리가 끝나지 않았습니다.' }
    Start-Sleep -Milliseconds 500
}
Start-ScheduledTask -TaskName $fintraTaskName
Wait-FintraReady
