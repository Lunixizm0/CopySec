$dir = Join-Path $env:TEMP 'opencode'
New-Item -ItemType Directory -Force -Path $dir | Out-Null

function Start-ClipReader {
    $stopFile = Join-Path $dir 'clip-daemon.stop'
    $pidFile = Join-Path $dir 'clip-daemon.pid'
    Remove-Item -LiteralPath $stopFile, $pidFile -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $dir -Filter 'clip-read.*.*' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
    $cmdline = "powershell.exe -NoProfile -STA -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PSScriptRoot\clipread-daemon.ps1`""
    $null = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList $cmdline, $null, $null, 0x08000000
    $deadline = (Get-Date).AddSeconds(6)
    while (-not (Test-Path -LiteralPath $pidFile) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 80 }
    if (-not (Test-Path -LiteralPath $pidFile)) { throw "clipboard reader daemon did not start" }
}

function Stop-ClipReader {
    New-Item -ItemType File -Path (Join-Path $dir 'clip-daemon.stop') -Force | Out-Null
    Start-Sleep -Milliseconds 400
}

function Read-Clip {
    $token = [Guid]::NewGuid().ToString('N')
    $req = Join-Path $dir ('clip-read.{0}.req' -f $token)
    $out = Join-Path $dir ('clip-read.{0}.out' -f $token)
    New-Item -ItemType File -Path $req -Force | Out-Null
    $deadline = (Get-Date).AddSeconds(8)
    while (-not (Test-Path -LiteralPath $out) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 80 }
    if (Test-Path -LiteralPath $out) {
        return (Get-Content -LiteralPath $out -Raw).TrimEnd("`r", "`n")
    }
    return ''
}
