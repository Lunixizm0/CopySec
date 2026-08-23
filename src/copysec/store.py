from __future__ import annotations

import datetime as _dt

from . import winapi
from .winapi import (
    CF_BITMAP,
    CF_DIB,
    CF_ENHMETAFILE,
    CF_METAFILEPICT,
    CF_OEMTEXT,
    CF_PALETTE,
    CF_TEXT,
    CF_UNICODETEXT,
)


def text_preview(fmt: int, data: bytes | None) -> str | None:
    if data is None:
        return None
    try:
        if fmt == CF_UNICODETEXT:
            text = data.decode("utf-16-le", "replace")
        elif fmt in (CF_TEXT, CF_OEMTEXT):
            text = data.decode("cp1252", "replace")
        else:
            return None
    except Exception:  # noqa: BLE001
        return None
    cleaned = "".join(ch if ch.isprintable() or ch == " " else " " for ch in text[:160])
    return cleaned.strip()


class ContentStore:
    def __init__(self, audit=None, resolve_name=None):
        self.audit = audit
        self._resolve_name = resolve_name or (lambda pid: None)
        self._payloads: dict[int, bytes] = {}
        self._registered: list[int] = []
        self._has_bitmap = False
        self._materialized: set[int] = set()
        self.active = False
        self.source: dict | None = None

    def _capture(self, fmt: int, raw_handle) -> bytes | None:
        if raw_handle is None:
            return None
        if fmt == CF_ENHMETAFILE:
            return winapi.enhmetafile_to_bytes(raw_handle)
        if fmt == CF_METAFILEPICT:
            return winapi.capture_metapict(raw_handle)
        if fmt == CF_PALETTE:
            return winapi.palette_to_logpalette(raw_handle)
        return winapi.read_global_bytes(raw_handle)

    def _build_handle(self, fmt: int, data: bytes | None):
        if fmt == CF_BITMAP:
            if self._has_bitmap and CF_DIB in self._payloads:
                return winapi.hbitmap_from_dib(self._payloads[CF_DIB])
            return None
        if not data:
            return None
        if fmt == CF_ENHMETAFILE:
            return winapi.bytes_to_enhmetafile(data)
        if fmt == CF_METAFILEPICT:
            return winapi.build_metapict_global(data)
        if fmt == CF_PALETTE:
            return winapi.palette_from_logpalette(data)
        return winapi.alloc_global_bytes(data)

    def _release_failed(self, fmt: int, handle) -> None:
        if handle is None:
            return
        if fmt == CF_ENHMETAFILE:
            winapi.gdi32.DeleteEnhMetaFile(handle)
        elif fmt in (CF_PALETTE, CF_BITMAP):
            winapi.gdi32.DeleteObject(handle)
        else:
            winapi.kernel32.GlobalFree(handle)

    def _place(self, fmt: int, data: bytes | None) -> bool:
        if fmt == CF_BITMAP:
            if self._has_bitmap and CF_DIB in self._payloads:
                hbmp = winapi.hbitmap_from_dib(self._payloads[CF_DIB])
                ok = bool(hbmp and winapi.user32.SetClipboardData(CF_BITMAP, hbmp))
                if hbmp and not ok:
                    winapi.gdi32.DeleteObject(hbmp)
                return ok
            return False
        handle = self._build_handle(fmt, data)
        if handle is None:
            return False
        if winapi.user32.SetClipboardData(fmt, handle):
            return True
        self._release_failed(fmt, handle)
        return False

    def adopt(self, owner_hwnd=None) -> bool:
        owner_hwnd_before = winapi.clipboard_owner_hwnd()
        owner_pid = winapi.window_pid(owner_hwnd_before) if owner_hwnd_before else None
        source = {"pid": owner_pid, "exe": self._resolve_name(owner_pid) if owner_pid else None}
        if not winapi.open_clipboard_retry(owner_hwnd):
            return False
        try:
            formats = winapi.enum_formats()
            payloads: dict[int, bytes] = {}
            registered: list[int] = []
            skipped: list[int] = []
            has_bitmap = False
            for fmt in formats:
                if fmt == CF_BITMAP:
                    has_bitmap = True
                    if fmt not in registered:
                        registered.append(fmt)
                    continue
                handle = winapi.user32.GetClipboardData(fmt)
                data = self._capture(fmt, handle)
                if data is None:
                    skipped.append(fmt)
                    continue
                payloads[fmt] = data
                registered.append(fmt)
            if has_bitmap and CF_DIB not in payloads:
                handle = winapi.user32.GetClipboardData(CF_DIB)
                synthesized = winapi.read_global_bytes(handle) if handle else None
                if synthesized is not None:
                    payloads[CF_DIB] = synthesized
                    registered.append(CF_DIB)
            self.source = {
                **source,
                "ts": _dt.datetime.now().astimezone().isoformat(timespec="milliseconds"),
            }
            if not payloads:
                self.active = False
                self._payloads = {}
                self._registered = []
                self._has_bitmap = False
                self._materialized.clear()
                return True
            self._payloads = payloads
            self._registered = registered
            self._has_bitmap = has_bitmap
            winapi.user32.EmptyClipboard()
            for fmt in registered:
                winapi.user32.SetClipboardData(fmt, None)
            self.active = True
            if self.audit:
                preview = text_preview(CF_UNICODETEXT, payloads.get(CF_UNICODETEXT))
                self.audit.event(
                    "adopted",
                    rate_key="adopted",
                    formats=len(registered),
                    skipped=skipped,
                    source=source,
                    sizes={fmt: len(data) for fmt, data in payloads.items()},
                    preview_chars=len(preview) if preview else 0,
                )
            return True
        finally:
            winapi.close_clipboard()

    def flush_back(self, owner=None) -> bool:
        if not self.active:
            return False
        ok = True
        if not winapi.open_clipboard_retry(owner):
            if self.audit:
                self.audit.event("flush_failed", rate_key="flush_failed", reason="open-clipboard")
            return False
        try:
            winapi.user32.EmptyClipboard()
            for fmt, data in self._payloads.items():
                if not self._place(fmt, data):
                    ok = False
            if (
                self._has_bitmap
                and CF_BITMAP not in self._payloads
                and CF_DIB in self._payloads
                and not self._place(CF_BITMAP, None)
            ):
                ok = False
        finally:
            winapi.close_clipboard()
        self.active = False
        if self.audit:
            self.audit.event("flushed", complete=ok)
        return ok

    def render(self, fmt: int) -> bool:
        if not self.active:
            return False
        has_payload = fmt in self._payloads
        is_bitmap = (
            fmt == CF_BITMAP
            and self._has_bitmap
            and CF_DIB in self._payloads
        )
        if not has_payload and not is_bitmap:
            return False
        if self._place(fmt, self._payloads.get(fmt)):
            self._materialized.add(fmt)
            return True
        return False

    @property
    def pending_rearm(self) -> bool:
        return bool(self._materialized)

    def rearm_delayed(self, owner_hwnd=None) -> bool:
        if not self.active or not self._materialized:
            return True
        if not winapi.open_clipboard_retry(owner_hwnd, attempts=10, delay=0.02):
            return False
        try:
            winapi.user32.EmptyClipboard()
            for fmt in self._registered:
                winapi.user32.SetClipboardData(fmt, None)
        finally:
            winapi.close_clipboard()
        self._materialized.clear()
        return True

    def clear(self) -> None:
        self._payloads.clear()
        self._registered.clear()
        self._materialized.clear()
        self._has_bitmap = False
        self.active = False
        self.source = None
