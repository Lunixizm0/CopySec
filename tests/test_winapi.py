import ctypes
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copysec import winapi
from copysec.winapi import (
    METAFILEPICT,
    build_metapict_global,
    bytes_to_enhmetafile,
    capture_metapict,
    corewindow_pid,
    enhmetafile_to_bytes,
    metapict_pack,
    metapict_unpack,
    palette_from_logpalette,
    palette_to_logpalette,
)


def make_enhmetafile():
    hdc_ref = winapi.gdi32.CreateEnhMetaFileW(None, None, None, None)
    assert hdc_ref
    hemf = winapi.gdi32.CloseEnhMetaFile(hdc_ref)
    assert hemf
    return hemf


def test_enhmetafile_roundtrip():
    hemf = make_enhmetafile()
    try:
        data = enhmetafile_to_bytes(hemf)
        assert data and len(data) >= 88
        signature = struct.unpack_from("<I", data, 40)[0]
        assert signature == 0x464D4520
        rebuilt = bytes_to_enhmetafile(data)
        try:
            assert rebuilt
            data2 = enhmetafile_to_bytes(rebuilt)
            assert data2 == data
        finally:
            if rebuilt:
                winapi.gdi32.DeleteEnhMetaFile(rebuilt)
    finally:
        winapi.gdi32.DeleteEnhMetaFile(hemf)


def test_metapict_struct_layout():
    assert ctypes.sizeof(METAFILEPICT) == 24
    offsets = {name: getattr(METAFILEPICT, name).offset for name, _ in METAFILEPICT._fields_}
    assert offsets == {"mm": 0, "xExt": 4, "yExt": 8, "hMF": 16}


def test_metapict_pack_unpack():
    payload = metapict_pack(8, 100, -50, b"\x01\x02\x03")
    mm, xe, ye, bits = metapict_unpack(payload)
    assert (mm, xe, ye, bits) == (8, 100, -50, b"\x01\x02\x03")


def test_metapict_unpack_rejects_short():
    assert metapict_unpack(b"\x01") is None


def make_memory_metafile():
    hdc = winapi.gdi32.CreateMetaFileW(None)
    assert hdc
    hmf = winapi.gdi32.CloseMetaFile(hdc)
    assert hmf
    return hmf


def build_source_metapict(mm=8, x_ext=640, y_ext=480):
    hmf = make_memory_metafile()
    outer = winapi.kernel32.GlobalAlloc(winapi.GMEM_MOVEABLE, ctypes.sizeof(METAFILEPICT))
    assert outer
    ptr = winapi.kernel32.GlobalLock(outer)
    assert ptr
    try:
        pict = ctypes.cast(ptr, ctypes.POINTER(METAFILEPICT)).contents
        pict.mm = mm
        pict.xExt = x_ext
        pict.yExt = y_ext
        pict.hMF = ctypes.c_void_p(hmf)
    finally:
        winapi.kernel32.GlobalUnlock(outer)
    return outer


def test_build_and_capture_metapict_global():
    outer = build_source_metapict()
    payload = capture_metapict(outer)
    winapi.kernel32.GlobalFree(outer)
    assert payload is not None
    mm, xe, ye, bits = metapict_unpack(payload)
    assert (mm, xe, ye) == (8, 640, 480)
    assert bits

    rebuilt = build_metapict_global(payload)
    assert rebuilt
    captured_again = capture_metapict(rebuilt)
    winapi.kernel32.GlobalFree(rebuilt)
    assert captured_again == payload


def test_build_metapict_global_rejects_invalid_bits():
    payload = metapict_pack(8, 10, 10, b"not-a-metafile")
    assert build_metapict_global(payload) is None


def test_palette_roundtrip():
    logpalette = struct.pack(
        "<HH4B4B",
        0x0300,
        2,
        255, 0, 0, 0,
        0, 255, 0, 0,
    )
    hpal = palette_from_logpalette(logpalette)
    assert hpal
    try:
        serialized = palette_to_logpalette(hpal)
        assert serialized == logpalette
    finally:
        winapi.gdi32.DeleteObject(hpal)


def test_palette_from_logpalette_rejects_bad_version():
    bad = struct.pack("<HH", 0x0200, 0)
    assert palette_from_logpalette(bad) is None


def test_corewindow_pid_invalid_hwnd():
    assert corewindow_pid(None) is None
