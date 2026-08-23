. (Join-Path $PSScriptRoot 'clipread-common.ps1')
Start-ClipReader

$cfgPath = Join-Path $env:TEMP 'opencode\cs-b-config.json'
@{
    allowlist = @('svchost.exe', 'powershell.exe')
    allow_uwp_frame_host = $false
    deny_unknown_requester = $true
    log_allows = $false
} | ConvertTo-Json | Set-Content $cfgPath -Encoding UTF8

try {
    Set-Clipboard -Value "CopySec-int-ALLOWED"

    $env:COPYSEC_DEBUG = "1"
    $p = Start-Process -FilePath ".venv\Scripts\copysec.exe" -ArgumentList "--no-tray","--verbose","--config",$cfgPath,"--smoke-seconds","10" -RedirectStandardOutput "$env:TEMP\opencode\cs-f-out.txt" -RedirectStandardError "$env:TEMP\opencode\cs-f-err.txt" -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 2.5

    "B1: guard running, powershell ALLOWED"
    $r1 = Read-Clip
    "B1 read: '$r1' (expected: CopySec-int-ALLOWED)"

    Start-Sleep -Seconds 9.5
    "B2: after exit"
    $r2 = Read-Clip
} finally {
    Stop-ClipReader
}

if ($r1 -eq 'CopySec-int-ALLOWED' -and $r2 -eq 'CopySec-int-ALLOWED') {
    "MATRIX-B: PASS"
} else {
    "MATRIX-B: FAIL r1='$r1' r2='$r2'"
    exit 1
}
