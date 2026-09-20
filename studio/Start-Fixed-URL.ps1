# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
$ErrorActionPreference = 'Stop'
$fintraRoot = $PSScriptRoot
$fintraCli = Join-Path $env:ProgramFiles 'Tailscale/tailscale.exe'
if (-not (Test-Path -LiteralPath $fintraCli)) {
    throw 'Install Tailscale from https://tailscale.com/download/windows and sign in first.'
}
$fintraStatusText = & $fintraCli status --json
if ($LASTEXITCODE -ne 0) { throw 'Tailscale is unavailable. Open Tailscale and sign in.' }
$fintraStatus = $fintraStatusText | ConvertFrom-Json
if ($fintraStatus.BackendState -ne 'Running') { throw 'Open Tailscale and finish signing in, then run this file again.' }
$fintraDns = $fintraStatus.Self.DNSName.TrimEnd('.')
if ($fintraDns -notmatch '^[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+\.ts\.net$') { throw 'Tailscale DNS name is unavailable.' }
$fintraOrigin = 'https://' + $fintraDns
$fintraData = Join-Path $fintraRoot 'team-preview'
$fintraHome = Join-Path $env:LOCALAPPDATA 'Fintra'
$fintraConfig = Get-Content -LiteralPath (Join-Path $fintraHome 'current.json') | ConvertFrom-Json
$fintraPython = Join-Path $fintraHome ('runtimes/' + $fintraConfig.runtime_id + '/python.exe')
if (-not (Test-Path -LiteralPath $fintraPython)) { throw 'Fintra Python runtime is missing.' }
if (-not (Test-Path -LiteralPath (Join-Path $fintraData 'account.json'))) { throw 'Run the existing team preview once to prepare its login account.' }

# Do not replace an unrelated web service already published through Tailscale.
$fintraFunnel = & $fintraCli funnel status --json
if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect existing Funnel settings.' }
$fintraExisting = $fintraFunnel | ConvertFrom-Json
if ($fintraExisting.Web) {
    foreach ($fintraHost in $fintraExisting.Web.PSObject.Properties) {
        if ($fintraHost.Name -ne ($fintraDns + ':443')) { throw 'Another Tailscale web service exists. Keep its configuration and review manually.' }
        foreach ($fintraHandler in $fintraHost.Value.Handlers.PSObject.Properties) {
            if ($fintraHandler.Name -ne '/' -or $fintraHandler.Value.Proxy -ne 'http://127.0.0.1:8781') {
                throw 'Another Tailscale web service exists. Keep its configuration and review manually.'
            }
        }
    }
}
Write-Host 'Enabling the fixed HTTPS address. If Tailscale prints a setup link, open it and complete setup.'
& $fintraCli funnel --bg --yes http://127.0.0.1:8781
if ($LASTEXITCODE -ne 0) { throw 'Funnel setup did not complete. The existing preview has not been stopped.' }

# Change the app origin only after Funnel is ready. Reuse the existing team workspace.
$fintraListener = Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue
if ($fintraListener) {
    $fintraStatePath = Join-Path $fintraData 'state.json'
    if (-not (Test-Path -LiteralPath $fintraStatePath)) { throw 'Preview manager cannot be identified.' }
    $fintraState = Get-Content -LiteralPath $fintraStatePath | ConvertFrom-Json
    if ($fintraState.manager_pid -ne $fintraListener.OwningProcess) { throw 'Port 8788 belongs to another process.' }
    if ($fintraState.url -eq $fintraOrigin -and $fintraState.status -eq 'running') {
        Write-Host ('Fintra URL: ' + $fintraOrigin)
        exit 0
    }
    New-Item -ItemType File -Path (Join-Path $fintraData 'stop.request') -Force | Out-Null
    $fintraStopDeadline = (Get-Date).AddSeconds(30)
    while (Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue) {
        if ((Get-Date) -gt $fintraStopDeadline) { throw 'Existing preview did not stop. No processes were forcibly terminated.' }
        Start-Sleep -Milliseconds 500
    }
}
if (Get-NetTCPConnection -LocalPort 8781 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8781 is still occupied.' }
$env:FINTRA_FIXED_ORIGIN = $fintraOrigin
$fintraTaskName = 'Fintra Fixed URL Server'
$fintraUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$fintraAction = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + (Join-Path $fintraRoot 'Run-Fixed-Server.ps1') + '"') -WorkingDirectory $fintraRoot
$fintraTrigger = New-ScheduledTaskTrigger -AtLogOn -User $fintraUser
$fintraPrincipal = New-ScheduledTaskPrincipal -UserId $fintraUser -LogonType Interactive -RunLevel Limited
$fintraSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -StartWhenAvailable
Register-ScheduledTask -TaskName $fintraTaskName -Action $fintraAction -Trigger $fintraTrigger -Principal $fintraPrincipal -Settings $fintraSettings -Force | Out-Null
Start-ScheduledTask -TaskName $fintraTaskName
$fintraDeadline = (Get-Date).AddSeconds(60)
while ((Get-Date) -lt $fintraDeadline) {
    $fintraStatePath = Join-Path $fintraData 'state.json'
    if (Test-Path -LiteralPath $fintraStatePath) {
        try {
            $fintraState = Get-Content -LiteralPath $fintraStatePath | ConvertFrom-Json
            if ($fintraState.status -eq 'running' -and (Get-NetTCPConnection -LocalPort 8788 -State Listen -ErrorAction SilentlyContinue).OwningProcess -eq $fintraState.manager_pid -and $fintraState.url -eq $fintraOrigin) {
                Write-Host ('Fintra URL: ' + $fintraOrigin)
                Write-Host 'Login details: team-preview/access.txt. Keep this PC awake and connected.'
                exit 0
            }
        } catch { }
    }
    Start-Sleep -Milliseconds 500
}
throw 'Fintra startup timed out. Check team-preview/app.log.'
