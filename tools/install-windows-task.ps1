# Registers (or replaces) the Task Scheduler task that keeps the SavedVariables
# bridge watcher running at logon, windowless, with absolute paths resolved here
# so a typo in "Start in" can never break it.
#
#   powershell -ExecutionPolicy Bypass -File tools\install-windows-task.ps1
#   powershell -ExecutionPolicy Bypass -File tools\install-windows-task.ps1 -Uninstall
#
# Then check tools\sv_bridge.log: the first line should say "sv_watch (poll 100 ms) started".

param([switch]$Uninstall)

$ErrorActionPreference = "Stop"
$TaskName = "wow-forever-addon-kit"

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task '$TaskName'."
    exit 0
}

$Tools  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Tools "sv_bridge.py"
if (-not (Test-Path $Script)) { throw "sv_bridge.py not found next to this script ($Tools)" }

# Prefer pythonw (no console window); fall back to python.
$py = Get-Command pythonw.exe -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python.exe -ErrorAction SilentlyContinue }
if (-not $py) { throw "Python not found on PATH. Install from python.org and tick 'Add python.exe to PATH'." }
$PyExe = $py.Source

$Action    = New-ScheduledTaskAction -Execute $PyExe -Argument "`"$Script`" watch" -WorkingDirectory $Tools
$Trigger   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
                -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
                -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                -DontStopOnIdleEnd -StartWhenAvailable
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal | Out-Null
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 3
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Task '$TaskName' registered."
Write-Host "  program : $PyExe"
Write-Host "  script  : $Script"
Write-Host "  state   : $((Get-ScheduledTask -TaskName $TaskName).State), last result 0x$('{0:X}' -f $info.LastTaskResult)"
$log = Join-Path $Tools "sv_bridge.log"
if (Test-Path $log) { Write-Host "  log tail:"; Get-Content $log -Tail 3 | ForEach-Object { "    $_" } }
