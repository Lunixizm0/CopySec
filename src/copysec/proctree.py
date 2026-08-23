from __future__ import annotations

import time

import psutil

from . import winapi
from .policy import ProcInfo

UWP_FRAME_HOST_EXE = "applicationframehost.exe"


class PsutilProcTree:
    TTL = 5.0

    def __init__(self):
        self._cache: dict[int, tuple[float, ProcInfo | None, tuple[int, ...]]] = {}

    def _entry(self, pid: int) -> tuple[float, ProcInfo | None, tuple[int, ...]]:
        now = time.monotonic()
        cached = self._cache.get(pid)
        if cached is not None and now - cached[0] < self.TTL:
            return cached
        info = None
        chain: tuple[int, ...] = ()
        try:
            proc = psutil.Process(pid)
            try:
                path = proc.exe()
            except (psutil.Error, OSError):
                path = None
            info = ProcInfo(pid, proc.name(), path)
            chain = tuple(p.pid for p in proc.parents())
        except (psutil.Error, OSError):
            pass
        entry = (now, info, chain)
        self._cache[pid] = entry
        return entry

    def resolve(self, pid: int) -> ProcInfo | None:
        return self._entry(pid)[1]

    def ancestors(self, pid: int) -> tuple[int, ...]:
        return self._entry(pid)[2]

    def foreground(self) -> ProcInfo | None:
        hwnd = winapi.user32.GetForegroundWindow()
        pid = winapi.window_pid(hwnd)
        if pid is None:
            return None
        info = self.resolve(pid)
        if info is None:
            return None
        if info.name_lower == UWP_FRAME_HOST_EXE and hwnd:
            inner_pid = winapi.corewindow_pid(hwnd)
            if inner_pid and inner_pid != pid:
                inner_info = self.resolve(inner_pid)
                return ProcInfo(
                    inner_pid,
                    inner_info.name if inner_info else "",
                    inner_info.path if inner_info else None,
                    host_pid=pid,
                )
        return info
