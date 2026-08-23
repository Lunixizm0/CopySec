$dir = Join-Path $env:TEMP 'opencode'
$stopFile = Join-Path $dir 'clip-daemon.stop'
$pidFile = Join-Path $dir 'clip-daemon.pid'
Set-Content -LiteralPath $pidFile -Value $PID -Encoding ASCII

Add-Type -AssemblyName System.Windows.Forms

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class Focus {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
}
"@

function Move-ForegroundAway {
    $tray = [Focus]::FindWindow("Shell_TrayWnd", $null)
    if ($tray -eq [IntPtr]::Zero) { return }
    for ($i = 0; $i -lt 6; $i++) {
        $fg = [Focus]::GetForegroundWindow()
        $fgPid = [uint32]0
        [void][Focus]::GetWindowThreadProcessId($fg, [ref]$fgPid)
        if ($fgPid -ne $PID) { return }
        $fgTid = [Focus]::GetWindowThreadProcessId($fg, [ref]$fgPid)
        $myTid = [Focus]::GetCurrentThreadId()
        [void][Focus]::AttachThreadInput($myTid, $fgTid, $true)
        [void][Focus]::SetForegroundWindow($tray)
        [void][Focus]::AttachThreadInput($myTid, $fgTid, $false)
        Start-Sleep -Milliseconds 150
    }
}

try {
    while (-not (Test-Path -LiteralPath $stopFile)) {
        $reqs = @(Get-ChildItem -Path $dir -Filter 'clip-read.*.req' -ErrorAction SilentlyContinue)
        foreach ($rq in $reqs) {
            Remove-Item -LiteralPath $rq.FullName -Force
            $parts = $rq.BaseName.Split('.')
            $token = $parts[1]
            Move-ForegroundAway
            Start-Sleep -Milliseconds 120
            $text = [System.Windows.Forms.Clipboard]::GetText()
            $res = Join-Path $dir ('clip-read.{0}.out' -f $token)
            Set-Content -LiteralPath $res -Value $text -Encoding UTF8
        }
        Start-Sleep -Milliseconds 60
    }
}
finally {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}
