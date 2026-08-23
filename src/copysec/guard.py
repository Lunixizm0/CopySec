from __future__ import annotations

import threading
import time
import traceback

from . import winapi
from .stats import RollingStats
from .winapi import (
    MSG,
    WM_APP,
    WM_CLIPBOARDUPDATE,
    WM_CLOSE,
    WM_DESTROY,
    WM_QUIT,
    WM_RENDERALLFORMATS,
    WM_RENDERFORMAT,
    WM_TIMER,
    WNDCLASSW,
    byref,
    c_wchar_p,
)


class ClipboardGuard:
    CMD_PAUSE = WM_APP + 1
    CMD_RESUME = WM_APP + 2
    CMD_ADOPT = WM_APP + 3
    CMD_REARM = WM_APP + 4

    WINDOW_CLASS = "CopySecGuardWindowClass"
    TIMER_ID = 1
    TIMER_INTERVAL_MS = 2000
    REARM_TIMER_ID = 2
    REARM_RETRY_MS = 500

    def __init__(self, policy, store, audit):
        self.policy = policy
        self.store = store
        self.audit = audit
        self.paused = False
        self.hwnd = None
        self.thread = None
        self._tid = 0
        self._ready = threading.Event()
        self._rearm_fail_streak = 0
        self.rearm_stats = RollingStats()
        self._fail_started: float | None = None
        self._proc = winapi.WNDPROC(self._dispatch)

    @property
    def is_alive(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def start(self) -> threading.Thread:
        self.thread = threading.Thread(target=self._run, name="copysec-guard", daemon=True)
        self.thread.start()
        self._ready.wait(timeout=5.0)
        return self.thread

    def stop(self) -> None:
        if self._tid:
            winapi.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)

    def pause(self) -> None:
        self._post(self.CMD_PAUSE)

    def resume(self) -> None:
        self._post(self.CMD_RESUME)

    def request_adopt(self) -> None:
        self._post(self.CMD_ADOPT)

    def _post(self, cmd: int) -> bool:
        if not self.hwnd:
            return False
        return bool(winapi.user32.PostMessageW(self.hwnd, cmd, 0, 0))

    def _run(self) -> None:
        self._tid = winapi.kernel32.GetCurrentThreadId()
        instance = winapi.kernel32.GetModuleHandleW(None)
        wc = WNDCLASSW()
        wc.lpfnWndProc = self._proc
        wc.hInstance = instance
        wc.lpszClassName = c_wchar_p(self.WINDOW_CLASS)
        if not winapi.user32.RegisterClassW(byref(wc)):
            self.audit.event("fatal", reason="register-class-failed")
            self._ready.set()
            return
        hwnd = winapi.user32.CreateWindowExW(
            0,
            c_wchar_p(self.WINDOW_CLASS),
            c_wchar_p("CopySec"),
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            instance,
            None,
        )
        if not hwnd:
            self.audit.event("fatal", reason="create-window-failed")
            self._ready.set()
            return
        self.hwnd = hwnd
        if not winapi.user32.AddClipboardFormatListener(hwnd):
            self.audit.event("fatal", reason="listener-failed")
            self._ready.set()
            return
        winapi.user32.SetTimer(hwnd, self.TIMER_ID, self.TIMER_INTERVAL_MS, None)
        self._ready.set()
        msg = MSG()
        try:
            while True:
                if winapi.user32.GetMessageW(byref(msg), None, 0, 0) <= 0:
                    break
                winapi.user32.TranslateMessage(byref(msg))
                winapi.user32.DispatchMessageW(byref(msg))
        except BaseException as exc:  # noqa: BLE001
            try:
                self.audit.event("fatal", reason="pump-crash", error=repr(exc))
            except Exception:  # noqa: BLE001, S110
                pass
        finally:
            winapi.user32.KillTimer(hwnd, self.TIMER_ID)
            winapi.user32.KillTimer(hwnd, self.REARM_TIMER_ID)
            winapi.user32.RemoveClipboardFormatListener(hwnd)
            if not winapi.user32.DestroyWindow(hwnd) and self.store.active:
                self.store.flush_back()
        self.hwnd = None

    def _dispatch(self, hwnd, msg, wparam, lparam) -> int:
        try:
            if msg == WM_CLIPBOARDUPDATE:
                self._on_update()
                return 0
            if msg == WM_RENDERFORMAT:
                self._on_render(int(wparam))
                return 0
            if msg == WM_RENDERALLFORMATS:
                self._on_renderall()
                return 0
            if msg == WM_TIMER:
                if wparam == self.TIMER_ID:
                    self._on_timer()
                    return 0
                if wparam == self.REARM_TIMER_ID:
                    winapi.user32.KillTimer(hwnd, self.REARM_TIMER_ID)
                    self._on_rearm()
                    return 0
            if msg == WM_DESTROY:
                self._on_destroy()
                return 0
            if msg == WM_CLOSE:
                self.audit.event("wm_close_external", rate_key="wm_close_external")
                return 0
            if msg == self.CMD_PAUSE:
                self._on_pause()
                return 0
            if msg == self.CMD_RESUME:
                self._on_resume()
                return 0
            if msg == self.CMD_ADOPT:
                self._on_update(force=True)
                return 0
            if msg == self.CMD_REARM:
                self._on_rearm()
                return 0
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            try:
                self.audit.event("handler_error", msg=hex(msg), error=repr(exc))
            except Exception:  # noqa: BLE001, S110
                pass
        return winapi.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _owner_is_us(self) -> bool:
        return self.hwnd is not None and winapi.clipboard_owner_hwnd() == self.hwnd

    def _on_update(self, force: bool = False) -> None:
        if self.paused and not force:
            return
        if self._owner_is_us():
            return
        if not self.store.adopt(self.hwnd):
            self.audit.event("adopt_failed", rate_key="adopt_failed")

    def _on_timer(self) -> None:
        if self.paused:
            return
        if self.store.pending_rearm:
            self._post(self.CMD_REARM)
            return
        if not self._owner_is_us():
            self._on_update()

    def _on_rearm(self) -> None:
        if self.paused:
            self._fail_started = None
            return
        if winapi.open_clipboard_window_hwnd() is not None:
            self._rearm_retry("clipboard-busy")
            return
        t0 = time.perf_counter()
        ok = self.store.rearm_delayed(self.hwnd)
        dur_ms = (time.perf_counter() - t0) * 1000.0
        if ok:
            fails = self._rearm_fail_streak
            self._rearm_fail_streak = 0
            settle_ms = None
            if self._fail_started is not None:
                settle_ms = round((time.monotonic() - self._fail_started) * 1000.0, 1)
                self._fail_started = None
            if self.hwnd:
                winapi.user32.KillTimer(self.hwnd, self.REARM_TIMER_ID)
            last_ms, avg_ms = self.rearm_stats.add(dur_ms)
            fields = {
                "failed_attempts": fails,
                "dur_ms": last_ms,
                "avg_ms": avg_ms,
                "samples": self.rearm_stats.count(),
            }
            if settle_ms is not None:
                fields["settle_ms"] = settle_ms
            self.audit.event("rearmed", rate_key="rearmed", **fields)
        else:
            self._rearm_retry("open-failed")

    def _rearm_retry(self, reason: str) -> None:
        self._rearm_fail_streak += 1
        if self._fail_started is None:
            self._fail_started = time.monotonic()
        n = self._rearm_fail_streak
        if n == 1 or n % 20 == 0:
            self.audit.event(
                "rearm_failed", rate_key="rearm_failed", consecutive=n, reason=reason
            )
        if self.hwnd:
            winapi.user32.SetTimer(self.hwnd, self.REARM_TIMER_ID, self.REARM_RETRY_MS, None)

    def _on_render(self, fmt: int) -> None:
        self.audit.probe(stage="render-start", fmt=fmt)
        requester_hwnd = winapi.open_clipboard_window_hwnd()
        requester_pid = winapi.window_pid(requester_hwnd)
        decision = self.policy.decide(requester_pid)
        name = winapi.format_name(fmt)
        rendered = None
        if decision.allowed:
            rendered = self.store.render(fmt)
            if not rendered:
                self.audit.event(
                    "unsupported_format",
                    fmt=fmt,
                    fmt_name=name,
                    rule=decision.rule,
                )
            else:
                self._post(self.CMD_REARM)
        self.audit.probe(
            stage="render-done",
            fmt=fmt,
            requester_pid=requester_pid,
            rule=decision.rule,
            allowed=decision.allowed,
            rendered=rendered,
        )
        self.audit.access(
            allowed=decision.allowed,
            rule=decision.rule,
            fmt=fmt,
            fmt_name=name,
            requester=decision.requester,
            foreground=decision.foreground,
        )

    def _on_renderall(self) -> None:
        self.audit.probe(stage="renderall")
        if self.store.active:
            self.store.flush_back(self.hwnd)

    def _on_destroy(self) -> None:
        self.audit.probe(stage="destroy")
        if not self.paused and self._owner_is_us() and self.store.active:
            self.store.flush_back(self.hwnd)

    def _on_pause(self) -> None:
        self.paused = True
        if self._owner_is_us() and self.store.active:
            self.store.flush_back(self.hwnd)
        self.audit.event("paused")

    def _on_resume(self) -> None:
        self.paused = False
        self.audit.event("resumed")
        if not self._owner_is_us():
            self._on_update()
