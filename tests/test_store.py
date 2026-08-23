import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copysec.store import ContentStore


def test_clear_zeroes_payload_buffers():
    store = ContentStore()
    secret = bytearray(b"top-secret-data")
    store._payloads[13] = secret
    store._registered.append(13)
    store.active = True
    store.source = {"pid": 1, "exe": "x.exe"}
    store.clear()
    assert secret == bytes(len(secret))
    assert not store._payloads
    assert not store._registered
    assert not store.active
    assert store.source is None


def test_default_max_format_bytes_positive():
    store = ContentStore()
    assert store.max_format_bytes > 0
    tiny = ContentStore(max_format_bytes=4)
    assert tiny.max_format_bytes == 4


def test_capture_enforces_max_format_bytes():
    from copysec import winapi

    data = b"A" * 16
    handle = winapi.kernel32.GlobalAlloc(winapi.GMEM_MOVEABLE, len(data))
    assert handle
    ptr = winapi.kernel32.GlobalLock(handle)
    assert ptr
    try:
        winapi.memmove(ptr, data, len(data))
    finally:
        winapi.kernel32.GlobalUnlock(handle)
    try:
        store = ContentStore(max_format_bytes=8)
        captured = store._capture(1, handle)
        assert captured is None
        generous = ContentStore(max_format_bytes=len(data))
        ok = generous._capture(1, handle)
        assert ok == bytearray(data)
    finally:
        winapi.kernel32.GlobalFree(handle)


def test_capture_returns_none_for_null_handle():
    store = ContentStore()
    assert store._capture(1, None) is None
