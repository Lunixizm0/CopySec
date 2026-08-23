param(
    [string]$Marker = ("CS-XIL-{0}" -f [guid]::NewGuid().ToString("N").Substring(0, 12))
)

$ErrorActionPreference = "Stop"
$work = Join-Path $env:TEMP "opencode\xil"
New-Item -ItemType Directory -Force -Path $work | Out-Null

if (Get-Process -Name "copysec" -ErrorAction SilentlyContinue) {
    Write-Host "XIL-CHECK: ABORT - an existing copysec instance is running, close it first"
    exit 1
}

$repo = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $repo ".venv\Scripts\copysec.exe"
$env:COPYSEC_DEBUG = "1"

function New-TempConfig([string[]]$Allowlist) {
    $path = Join-Path $work ("cs-xil-{0}.json" -f [guid]::NewGuid().ToString("N"))
    @{ allowlist = $Allowlist } | ConvertTo-Json | Set-Content -Path $path -Encoding UTF8
    return $path
}

function Start-Guard([string]$ConfigPath) {
    $out = Join-Path $work ("xil-guard-out-{0}.txt" -f [guid]::NewGuid().ToString("N").Substring(0, 6))
    Remove-Item $out -ErrorAction SilentlyContinue
    $p = Start-Process -FilePath $exe `
        -ArgumentList @("--no-tray", "--config", $ConfigPath, "--verbose") `
        -RedirectStandardOutput $out -RedirectStandardError "$out.err" `
        -WindowStyle Hidden -PassThru
    $deadline = (Get-Date).AddSeconds(10)
    while ((Get-Date) -lt $deadline) {
        if ($p.HasExited) { throw "guard exited early code=$($p.ExitCode)" }
        $txt = if (Test-Path $out) { Get-Content $out -Raw -ErrorAction SilentlyContinue } else { "" }
        if ($txt -match '"event": "adopted"') { return ,@($p, $out) }
        Start-Sleep -Milliseconds 100
    }
    Stop-Guard $p
    throw "guard did not adopt clipboard in time"
}

function Stop-Guard($Proc) {
    try {
        if ($Proc -and -not $Proc.HasExited) {
            $Proc.Kill()
            $Proc.WaitForExit(5000) | Out-Null
        }
    } catch {}
}

function Invoke-SpyRead([string]$Tag) {
    $txtFile = Join-Path $work ("xil-text-{0}.txt" -f $Tag)
    $metaFile = Join-Path $work ("xil-meta-{0}.txt" -f $Tag)
    $pidFile = Join-Path $work ("xil-pid-{0}.txt" -f $Tag)
    Remove-Item $txtFile, $metaFile, $pidFile -ErrorAction SilentlyContinue
    $inner = "Add-Type -AssemblyName System.Windows.Forms; " +
        "`$t = [System.Windows.Forms.Clipboard]::GetText(); " +
        "Set-Content -Path '$txtFile' -Value `$t -Encoding UTF8; " +
        "`$line = (whoami /groups | Select-String 'Mandatory Label').Line; " +
        "Set-Content -Path '$metaFile' -Value `$line -Encoding UTF8; " +
        "Set-Content -Path '$pidFile' -Value `$PID -Encoding UTF8"
    $enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($inner))
    $taskName = "CSXilSpy_" + [guid]::NewGuid().ToString("N").Substring(0, 8)
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -STA -WindowStyle Hidden -EncodedCommand $enc"
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
        -LogonType Interactive -RunLevel Limited
    try {
        Register-ScheduledTask -TaskName $taskName -Action $action `
            -Principal $principal -ErrorAction Stop | Out-Null
        Start-ScheduledTask -TaskName $taskName
        $deadline = (Get-Date).AddSeconds(25)
        while ((Get-Date) -lt $deadline) {
            if ((Test-Path $txtFile) -and (Test-Path $pidFile)) { break }
            Start-Sleep -Milliseconds 250
        }
    } finally {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path $pidFile)) {
        throw "spy did not run"
    }
    [pscustomobject]@{
        SpyPid = [int](Get-Content $pidFile)
        Text = if (Test-Path $txtFile) { (Get-Content $txtFile -Raw) } else { "<no-output>" }
        Il = if (Test-Path $metaFile) { ((Get-Content $metaFile) -join " ").Trim() } else { "<no-il-info>" }
    }
}

function Read-GuardEvents([string]$OutFile, [int]$SpyPid) {
    $events = @()
    foreach ($line in Get-Content $OutFile) {
        if (-not $line.StartsWith("{")) { continue }
        try { $r = $line | ConvertFrom-Json } catch { continue }
        $rp = $null
        if ($r.requester_pid) { $rp = [int]$r.requester_pid }
        elseif ($r.requester -and $r.requester.pid) { $rp = [int]$r.requester.pid }
        if ($rp -eq $SpyPid) { $events += $r }
    }
    return $events
}

$origClip = try { Get-Clipboard -Raw } catch { "" }

$results = @()
foreach ($phase in @(
    @{ Tag = "deny"; Allowlist = @() },
    @{ Tag = "allow"; Allowlist = @("powershell.exe") }
)) {
    Write-Host ("XIL-CHECK: phase '{0}' starting..." -f $phase.Tag)
    Set-Clipboard -Value $Marker
    $cfg = New-TempConfig $phase.Allowlist
    $pair = Start-Guard $cfg
    $guard = $pair[0]
    $guardOut = $pair[1]
    try {
        Start-Sleep -Milliseconds 500
        $spy = Invoke-SpyRead $phase.Tag
        Start-Sleep -Milliseconds 300
        $events = Read-GuardEvents $guardOut $spy.SpyPid
        $denyCount = @($events | Where-Object { $_.event -eq "deny" }).Count
        $renderCount = @($events | Where-Object { $_.event -eq "probe" -and $_.stage -eq "render-done" }).Count
        $allowCount = @($events | Where-Object { $_.event -eq "allow" }).Count
        $results += [pscustomobject]@{
            Phase = $phase.Tag
            SpyPid = $spy.SpyPid
            Il = ($spy.Il -replace "\s+", " ")
            GotMarker = ($spy.Text -like "*$Marker*")
            DenyLogged = ($denyCount -gt 0)
            RenderSeen = ($renderCount -gt 0)
            AllowLogged = ($allowCount -gt 0)
            RawTextPreview = (($spy.Text.Trim()) -replace "`r`n", " ")
        }
    } finally {
        Stop-Guard $guard
    }
}

Set-Clipboard -Value $origClip

Write-Host ""
Write-Host "=== XIL-CHECK RESULTS ==="
foreach ($r in $results) {
    Write-Host ("[{0}] spy_pid={1} il='{2}'" -f $r.Phase, $r.SpyPid, $r.Il)
    Write-Host ("     got_marker={0} render_seen={1} deny_logged={2} allow_logged={3} raw='{4}'" -f `
        $r.GotMarker, $r.RenderSeen, $r.DenyLogged, $r.AllowLogged, $r.RawTextPreview)
}
$d = $results | Where-Object Phase -eq "deny"
$a = $results | Where-Object Phase -eq "allow"
Write-Host ""
if ($d.Il -notmatch "Medium") {
    Write-Host "WARNING: spy did not run at Medium IL - NOT a valid cross-IL test."
}
if (-not $d.RenderSeen) {
    Write-Host "DENY:    WM_RENDERFORMAT never arrived from medium-IL reader (UIPI block?)."
} elseif ($d.GotMarker) {
    Write-Host "DENY:    SECURITY LEAK - reader received data despite deny!"
} else {
    Write-Host "DENY:    OK - request reached guard, was denied, reader got empty text."
}
if (-not $a.RenderSeen) {
    Write-Host "ALLOW:   no request seen - delivery broken."
} elseif ($a.GotMarker) {
    Write-Host "ALLOW:   OK - allowed medium-IL reader received data end-to-end."
} else {
    Write-Host "ALLOW:   request arrived and was allowed, but reader got nothing (handoff broken)."
}
exit 0


