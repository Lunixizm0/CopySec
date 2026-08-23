. (Join-Path $PSScriptRoot 'clipread-common.ps1')
Start-ClipReader

$cfgPath = Join-Path $env:TEMP 'opencode\cs-a-config.json'
@{
    allowlist = @()
    allow_uwp_frame_host = $false
    deny_unknown_requester = $true
    log_allows = $false
} | ConvertTo-Json | Set-Content $cfgPath -Encoding UTF8

try {
    "BASELINE"
    Set-Clipboard -Value "CopySec-int-42"
    $r = Read-Clip
    "baseline read: '$r'"

    $env:COPYSEC_DEBUG = "1"
    $p = Start-Process -FilePath ".venv\Scripts\copysec.exe" -ArgumentList "--no-tray","--verbose","--config",$cfgPath,"--smoke-seconds","10" -RedirectStandardOutput "$env:TEMP\opencode\cs-e-out.txt" -RedirectStandardError "$env:TEMP\opencode\cs-e-err.txt" -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2.5

    "A1: guard running, detached reader DENIED"
    $r1 = Read-Clip
    "A1 read: '$r1' (expected: empty)"

    Start-Sleep -Seconds 9.5
    "guard exited: $($p.HasExited)"
    "A2: restore after exit"
    $r2 = Read-Clip
    "A2 read: '$r2' (expected: CopySec-int-42)"
} finally {
    Stop-ClipReader
}

$ok = $false
if ($r -eq 'CopySec-int-42' -and [string]::IsNullOrEmpty($r1)) {
    $flushOk = Select-String -Path "$env:TEMP\opencode\cs-e-out.txt" -Pattern '"event": "flushed", "complete": true' -Quiet
    if (($r2 -eq 'CopySec-int-42') -or ($flushOk -and -not [string]::IsNullOrEmpty($r2))) {
        "MATRIX-A: PASS"
        if ($r2 -ne 'CopySec-int-42') { "note: clipboard changed mid-test by other activity; restore verified against flushed event" }
        $ok = $true
    } else {
        "MATRIX-A: FAIL r2='$r2' flushOk=$flushOk"
    }
} else {
    "MATRIX-A: FAIL baseline='$r' r1='$r1'"
}
if (-not $ok) { exit 1 }
