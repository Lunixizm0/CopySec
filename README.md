# CopySec

Clipboard protection: only the **active (foreground) application** and its **process tree**
can read the clipboard. Every unauthorized read attempt receives **empty data** and is
logged as JSONL.

## How it works

Windows does not allow ACLs on the clipboard; instead, CopySec takes ownership of the
clipboard via *delayed rendering*. Whenever any process calls `GetClipboardData`, the
system forwards the request to CopySec as a `WM_RENDERFORMAT` message; at that moment
`GetOpenClipboardWindow()` resolves the requester's PID and a decision is made:

- Allowed: ourselves, the foreground window's process, descendants of the foreground
  process (child/grandchild), allowlist
- Denied: no format is rendered, the reader receives `NULL`, and the event is logged

The real content is kept in memory; the clipboard always remains owned by CopySec.
On exit or pause, the real data is written back to the clipboard.

## Installation and running

```powershell
uv sync
uv run copysec            # with tray icon
uv run copysec --no-tray --verbose   # console mode + live log
```

To run as administrator, open PowerShell via "Run as administrator" and run the same
command (not required; all APIs used work with normal privileges).

## Configuration

`%LOCALAPPDATA%\CopySec\config.json` is created on first run:

| Field | Default | Meaning |
|---|---|---|
| `allowlist` | `["svchost.exe"]` | Always-allowed exe names (case-insensitive). `svchost.exe` covers the Win+V clipboard history service (cbdhsvc) |
| `allow_uwp_frame_host` | `false` | Legacy escape hatch: allows every request from `ApplicationFrameHost.exe` itself. Regular UWP paste works out of the box because CopySec resolves the frame-hosted app's real process; enable only if some packaged app still fails |
| `deny_unknown_requester` | `true` | Deny when it cannot be determined which window opened the clipboard (spyware can pass NULL) |
| `log_allows` | `false` | Also log allowed accesses |

Logs: `%LOCALAPPDATA%\CopySec\logs\audit-YYYYMMDD.jsonl`. When a file reaches 1 MB
it is rotated to `audit-YYYYMMDD.1.jsonl`, `.2.jsonl`, and so on for the rest of the day.
On every startup CopySec also checks the whole logs folder: if it exceeds 10 MB, the
oldest files are deleted until 5 MB or less remains. A `logs_pruned` record notes how
many files were removed.
Note: with `--config <path>` the log directory becomes `<path parent>\logs` instead.

Rearm benchmarking: every `rearmed` record carries `dur_ms` (the re-arm operation
itself), `avg_ms` (rolling mean over the last 64 re-arms), `samples`, and, when the
clipboard was busy before the success, `settle_ms` (time from first failed attempt to
success). Watch them live with `--verbose`.

## Testing

Everything (unit + integration) in one run:

```powershell
uv run pytest
```

The two integration tests (`matrix_a`, `matrix_b`) drive the real guard end to end
through the PowerShell scripts in `scripts\` and need an interactive desktop session;
each adds roughly 15-20 seconds. Useful selections:

```powershell
uv run pytest -m "not integration" -q   # unit tests only
uv run pytest -m integration -q         # matrices only
powershell -File scripts\matrix_a.ps1   # denied reader to empty data, restore on exit
powershell -File scripts\matrix_b.ps1   # allowlisted reader to real data
uv run python scripts\spy_sim.py        # background "spy" simulator (live monitoring)
```

Notes:

- The matrices take over the clipboard and briefly move window focus; do not run
  pytest sessions in parallel.
- Without an interactive desktop (SSH, services) they skip automatically.

Manual scenario:

1. Start CopySec and run spy_sim in the background (it sees empty data).
2. Write something in Notepad, press Ctrl+A and Ctrl+C, then Ctrl+V in Notepad (works because it is foreground).
3. spy_sim output must stay empty; `deny` lines accumulate in the audit log.
4. Tray > Pause: spy_sim now sees the content. Resume closes it again.

## Known limitations

- Between the user copying and CopySec taking ownership there is a millisecond-scale
  window in which a very fast reader can see the real data once.
- After an allowed read, the content stays as real clipboard data for a short time;
  CopySec returns it to delayed mode within ~50 ms (re-arm). Other readers racing
  during that window can see the data. Allowlisted components that read continuously,
  such as clipboard history (cbdhsvc), keep triggering this cycle; that is normal.
- Owner-tied formats (CF_OWNERDISPLAY and CF_DSP*) cannot be carried across ownership
  changes; they are skipped.
- Brief exposure window: after an allowed app reads the clipboard, Windows keeps the
  real data available until CopySec re-arms delayed rendering (normally well under a
  second, retried aggressively). A process reading inside that window may see the
  data without being checked.
- UWP paste works automatically: when the foreground window belongs to
  `ApplicationFrameHost.exe`, CopySec resolves the hosted app's process through its
  `CoreWindow` child window and applies the normal rules to it.
- Rare UIPI quirks are possible with elevated (high IL) readers plus a non-admin guard;
  if you hit issues, run both at the same integrity level.

## Troubleshooting

- **Pasted content came out empty:** The reading app is not foreground or was denied.
  Check the `deny` lines printed with `--verbose` (the `rule` field explains why:
  `no-match`, `unknown-requester`, ...). If needed add the exe name to `allowlist`,
  or for exotic packaged apps that still fail enable `allow_uwp_frame_host`.
- **Leave the clipboard cleanly:** Close CopySec with Ctrl+C or tray > Exit (the real
  data is written back to the clipboard). If you force-kill it from Task Manager the
  delayed-render data goes away too and the clipboard ends up empty; that is Windows'
  delayed rendering behavior.
- **Running elevated (admin PowerShell):** Supported and verified. Windows delivers
  clipboard render messages across integrity levels, so non-elevated apps still go
  through the normal decision path; elevation of the guard itself grants nothing to
  any reader. Verify anytime with `scripts\xil_check.ps1` (spawns a real Medium-IL
  reader via a scheduled task and checks both the deny and allow paths).
- **Do not run two copies:** Only one guard can take ownership at a time; the second
  one waits pointlessly.
- **`rearm_failed` / `rearmed` pairs in the log:** Normal when an allowlisted
  background reader (typically the clipboard history service, `cbdhsvc` inside
  `svchost.exe`) keeps the clipboard open right after reading. CopySec re-arms its
  delayed rendering as soon as the clipboard frees up (retried every 500 ms);
  during that gap the real data is briefly readable by anyone (see Known limitations).
  A `consecutive` count above a few would signal something is holding the clipboard
  open for a long time.

## Architecture

```
src/copysec/
    winapi.py     ctypes Win32 bindings (clipboard, global memory, DIB to HBITMAP)
    store.py      real content store + adopt/flush/render
    policy.py     decision engine (foreground, process tree, allowlist)
    proctree.py   psutil-based PID/exe/ancestor-chain cache
    guard.py      hidden window, WndProc, message loop
    audit.py      JSONL audit log + rate limit
    tray.py       pystray tray icon
    cli.py        entry point
```
