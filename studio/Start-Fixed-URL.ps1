# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
$ErrorActionPreference = 'Stop'
$fintraRoot = $PSScriptRoot
$fintraData = Join-Path $fintraRoot 'team-preview'
$fintraUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$fintraTaskName = 'Fintra Fixed URL Server'
$fintraListener = Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue
if ($fintraListener) {
    $fintraState = Get-Content -LiteralPath (Join-Path $fintraData 'state.json') | ConvertFrom-Json
    if ($fintraState.manager_pid -ne $fintraListener.OwningProcess) { throw 'Port 8788 belongs to another process.' }
    if ($fintraState.provider -eq 'cloudflare' -and $fintraState.status -eq 'running') {
        Write-Host 'Fintra: https://hayden-shin-dev.github.io/Fintra-OCR/'
        exit 0
    }
    New-Item -ItemType File -Path (Join-Path $fintraData 'stop.request') -Force | Out-Null
    $fintraDeadline = (Get-Date).AddSeconds(60)
    while (Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue) {
        if ((Get-Date) -gt $fintraDeadline) { throw 'Existing server did not stop.' }
        Start-Sleep -Milliseconds 500
    }
}
$fintraAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + (Join-Path $fintraRoot 'Run-Public-Server.ps1') + '"') -WorkingDirectory $fintraRoot
$fintraTrigger = New-ScheduledTaskTrigger -AtLogOn -User $fintraUser
$fintraPrincipal = New-ScheduledTaskPrincipal -UserId $fintraUser -LogonType Interactive -RunLevel Limited
$fintraSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName $fintraTaskName -Action $fintraAction -Trigger $fintraTrigger -Principal $fintraPrincipal -Settings $fintraSettings -Force | Out-Null
Start-ScheduledTask -TaskName $fintraTaskName
Write-Host 'Fintra: https://hayden-shin-dev.github.io/Fintra-OCR/'
Write-Host 'Starting in the background. This window can be closed.'
