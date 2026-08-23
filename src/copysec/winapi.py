import ctypes
import struct
import time
from ctypes import (
    POINTER,
    WINFUNCTYPE,
    byref,
    c_int,
    c_long,
    c_size_t,
    c_ssize_t,
    c_ubyte,
    c_uint,
    c_ulong,
    c_ushort,
    c_void_p,
    c_wchar_p,
    memmove,
    string_at,
)

HWND = c_void_p
HANDLE = c_void_p
HGLOBAL = c_void_p
HBITMAP = c_void_p
HDC = c_void_p
HINSTANCE = c_void_p
DWORD = c_ulong
UINT = c_uint
WORD = c_ushort
BYTE = c_ubyte
BOOL = c_int

WPARAM = c_size_t
LPARAM = c_ssize_t
LRESULT = c_ssize_t
UINT_PTR = c_size_t

GMEM_MOVEABLE = 0x0002
DIB_RGB_COLORS = 0
BI_RGB = 0
BI_BITFIELDS = 3

CF_TEXT = 1
CF_BITMAP = 2
CF_METAFILEPICT = 3
CF_SYLK = 4
CF_DIF = 5
CF_TIFF = 6
CF_OEMTEXT = 7
CF_DIB = 8
CF_PALETTE = 9
CF_PENDATA = 10
CF_RIFF = 11
CF_WAVE = 12
CF_UNICODETEXT = 13
CF_ENHMETAFILE = 14
CF_HDROP = 15
CF_LOCALE = 16
CF_DIBV5 = 17

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_QUIT = 0x0012
WM_TIMER = 0x0113
WM_RENDERFORMAT = 0x0305
WM_RENDERALLFORMATS = 0x0306
WM_CLIPBOARDUPDATE = 0x031D
WM_APP = 0x8000

FORMAT_NAMES = {
    CF_TEXT: "CF_TEXT",
    CF_BITMAP: "CF_BITMAP",
    CF_METAFILEPICT: "CF_METAFILEPICT",
    CF_SYLK: "CF_SYLK",
    CF_DIF: "CF_DIF",
    CF_TIFF: "CF_TIFF",
    CF_OEMTEXT: "CF_OEMTEXT",
    CF_DIB: "CF_DIB",
    CF_PALETTE: "CF_PALETTE",
    CF_PENDATA: "CF_PENDATA",
    CF_RIFF: "CF_RIFF",
    CF_WAVE: "CF_WAVE",
    CF_UNICODETEXT: "CF_UNICODETEXT",
    CF_ENHMETAFILE: "CF_ENHMETAFILE",
    CF_HDROP: "CF_HDROP",
    CF_LOCALE: "CF_LOCALE",
    CF_DIBV5: "CF_DIBV5",
}

WNDPROC = WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)
ENUMCHILDPROC = WINFUNCTYPE(BOOL, HWND, LPARAM)


class POINT(ctypes.Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", HWND),
        ("message", UINT),
        ("wParam", WPARAM),
        ("lParam", LPARAM),
        ("time", DWORD),
        ("pt", POINT),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", c_int),
        ("cbWndExtra", c_int),
        ("hInstance", HINSTANCE),
        ("hIcon", HANDLE),
        ("hCursor", HANDLE),
        ("hbrBackground", HANDLE),
        ("lpszMenuName", c_wchar_p),
        ("lpszClassName", c_wchar_p),
    ]


class METAFILEPICT(ctypes.Structure):
    _fields_ = [
        ("mm", c_long),
        ("xExt", c_long),
        ("yExt", c_long),
        ("hMF", HANDLE),
    ]


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

user32.AddClipboardFormatListener.restype = BOOL
user32.AddClipboardFormatListener.argtypes = [HWND]
user32.RemoveClipboardFormatListener.restype = BOOL
user32.RemoveClipboardFormatListener.argtypes = [HWND]
user32.OpenClipboard.restype = BOOL
user32.OpenClipboard.argtypes = [HWND]
user32.CloseClipboard.restype = BOOL
user32.CloseClipboard.argtypes = []
user32.EmptyClipboard.restype = BOOL
user32.EmptyClipboard.argtypes = []
user32.GetClipboardOwner.restype = HWND
user32.GetClipboardOwner.argtypes = []
user32.GetOpenClipboardWindow.restype = HWND
user32.GetOpenClipboardWindow.argtypes = []
user32.GetClipboardData.restype = HANDLE
user32.GetClipboardData.argtypes = [UINT]
user32.SetClipboardData.restype = HANDLE
user32.SetClipboardData.argtypes = [UINT, HANDLE]
user32.EnumClipboardFormats.restype = UINT
user32.EnumClipboardFormats.argtypes = [UINT]
user32.IsClipboardFormatAvailable.restype = BOOL
user32.IsClipboardFormatAvailable.argtypes = [UINT]
user32.CountClipboardFormats.restype = c_int
user32.CountClipboardFormats.argtypes = []
user32.RegisterClipboardFormatW.restype = UINT
user32.RegisterClipboardFormatW.argtypes = [c_wchar_p]
user32.GetClipboardFormatNameW.restype = BOOL
user32.GetClipboardFormatNameW.argtypes = [UINT, c_wchar_p, c_int]
user32.GetForegroundWindow.restype = HWND
user32.GetForegroundWindow.argtypes = []
user32.GetWindowThreadProcessId.restype = DWORD
user32.GetWindowThreadProcessId.argtypes = [HWND, POINTER(DWORD)]
user32.EnumChildWindows.restype = BOOL
user32.EnumChildWindows.argtypes = [HWND, ENUMCHILDPROC, LPARAM]
user32.GetClassNameW.restype = c_int
user32.GetClassNameW.argtypes = [HWND, c_wchar_p, c_int]
user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = [HWND, UINT, WPARAM, LPARAM]
user32.RegisterClassW.restype = WORD
user32.RegisterClassW.argtypes = [POINTER(WNDCLASSW)]
user32.CreateWindowExW.restype = HWND
user32.CreateWindowExW.argtypes = [
    DWORD,
    c_wchar_p,
    c_wchar_p,
    DWORD,
    c_int,
    c_int,
    c_int,
    c_int,
    HWND,
    HANDLE,
    HINSTANCE,
    c_void_p,
]
user32.DestroyWindow.restype = BOOL
user32.DestroyWindow.argtypes = [HWND]
user32.ShowWindow.restype = BOOL
user32.ShowWindow.argtypes = [HWND, c_int]
user32.GetMessageW.restype = c_int
user32.GetMessageW.argtypes = [POINTER(MSG), HWND, UINT, UINT]
user32.TranslateMessage.restype = BOOL
user32.TranslateMessage.argtypes = [POINTER(MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.DispatchMessageW.argtypes = [POINTER(MSG)]
user32.PostQuitMessage.restype = None
user32.PostQuitMessage.argtypes = [c_int]
user32.PostMessageW.restype = BOOL
user32.PostMessageW.argtypes = [HWND, UINT, WPARAM, LPARAM]
user32.PostThreadMessageW.restype = BOOL
user32.PostThreadMessageW.argtypes = [DWORD, UINT, WPARAM, LPARAM]
user32.SetTimer.restype = UINT_PTR
user32.SetTimer.argtypes = [HWND, UINT_PTR, UINT, c_void_p]
user32.KillTimer.restype = BOOL
user32.KillTimer.argtypes = [HWND, UINT_PTR]
user32.GetDC.restype = c_void_p
user32.GetDC.argtypes = [HWND]
user32.ReleaseDC.restype = c_int
user32.ReleaseDC.argtypes = [HWND, HDC]

kernel32.GlobalAlloc.restype = HGLOBAL
kernel32.GlobalAlloc.argtypes = [UINT, c_size_t]
kernel32.GlobalLock.restype = c_void_p
kernel32.GlobalLock.argtypes = [HGLOBAL]
kernel32.GlobalUnlock.restype = BOOL
kernel32.GlobalUnlock.argtypes = [HGLOBAL]
kernel32.GlobalSize.restype = c_size_t
kernel32.GlobalSize.argtypes = [HGLOBAL]
kernel32.GlobalFree.restype = HGLOBAL
kernel32.GlobalFree.argtypes = [HGLOBAL]
kernel32.GetCurrentThreadId.restype = DWORD
kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentProcessId.restype = DWORD
kernel32.GetCurrentProcessId.argtypes = []
kernel32.GetModuleHandleW.restype = HINSTANCE
kernel32.GetModuleHandleW.argtypes = [c_wchar_p]

gdi32.CreateDIBSection.restype = HBITMAP
gdi32.CreateDIBSection.argtypes = [c_void_p, c_void_p, UINT, POINTER(c_void_p), c_void_p, DWORD]
gdi32.DeleteObject.restype = BOOL
gdi32.DeleteObject.argtypes = [HBITMAP]
gdi32.GetEnhMetaFileBits.restype = UINT
gdi32.GetEnhMetaFileBits.argtypes = [HANDLE, UINT, c_void_p]
gdi32.SetEnhMetaFileBits.restype = HANDLE
gdi32.SetEnhMetaFileBits.argtypes = [UINT, c_void_p]
gdi32.DeleteEnhMetaFile.restype = BOOL
gdi32.DeleteEnhMetaFile.argtypes = [HANDLE]
gdi32.GetMetaFileBitsEx.restype = UINT
gdi32.GetMetaFileBitsEx.argtypes = [HANDLE, UINT, c_void_p]
gdi32.SetMetaFileBitsEx.restype = HANDLE
gdi32.SetMetaFileBitsEx.argtypes = [UINT, c_void_p]
gdi32.DeleteMetaFile.restype = BOOL
gdi32.DeleteMetaFile.argtypes = [HANDLE]
gdi32.GetObjectW.restype = c_int
gdi32.GetObjectW.argtypes = [HANDLE, c_int, c_void_p]
gdi32.GetPaletteEntries.restype = UINT
gdi32.GetPaletteEntries.argtypes = [HANDLE, c_int, c_int, c_void_p]
gdi32.CreatePalette.restype = HANDLE
gdi32.CreatePalette.argtypes = [c_void_p]
gdi32.CreateMetaFileW.restype = HDC
gdi32.CreateMetaFileW.argtypes = [c_wchar_p]
gdi32.CloseMetaFile.restype = HANDLE
gdi32.CloseMetaFile.argtypes = [HDC]


def read_global_bytes(handle: int | None) -> bytes | None:
    if not handle:
        return None
    size = kernel32.GlobalSize(handle)
    if size == 0:
        return b""
    ptr = kernel32.GlobalLock(handle)
    if not ptr:
        return None
    try:
        return string_at(ptr, size)
    finally:
        kernel32.GlobalUnlock(handle)


def alloc_global_bytes(data) -> int | None:
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        return None
    ptr = kernel32.GlobalLock(handle)
    if not ptr:
        kernel32.GlobalFree(handle)
        return None
    try:
        src = (c_ubyte * len(data)).from_buffer(data)
        memmove(ptr, src, len(data))
    finally:
        kernel32.GlobalUnlock(handle)
    return handle


def open_clipboard_retry(owner: int | None = None, attempts: int = 10, delay: float = 0.05) -> bool:
    for i in range(attempts):
        if user32.OpenClipboard(owner):
            return True
        time.sleep(delay)
    return False


def close_clipboard() -> None:
    user32.CloseClipboard()


def enum_formats() -> list[int]:
    formats = []
    fmt = user32.EnumClipboardFormats(0)
    while fmt:
        formats.append(fmt)
        fmt = user32.EnumClipboardFormats(fmt)
    return formats


def clipboard_owner_hwnd() -> int | None:
    hwnd = user32.GetClipboardOwner()
    return hwnd or None


def open_clipboard_window_hwnd() -> int | None:
    hwnd = user32.GetOpenClipboardWindow()
    return hwnd or None


def window_pid(hwnd: int | None) -> int | None:
    if not hwnd:
        return None
    pid = DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, byref(pid))
    return pid.value or None


def foreground_pid() -> int | None:
    return window_pid(user32.GetForegroundWindow())


UWP_CORE_WINDOW_CLASS = "Windows.UI.Core.CoreWindow"


def corewindow_pid(top_hwnd: int | None) -> int | None:
    if not top_hwnd:
        return None
    found: list[int] = []
    buf = ctypes.create_unicode_buffer(64)

    def on_child(child_hwnd: int, _lparam: int) -> int:
        user32.GetClassNameW(child_hwnd, buf, 64)
        if buf.value == UWP_CORE_WINDOW_CLASS:
            pid = window_pid(child_hwnd)
            if pid:
                found.append(pid)
                return 0
        return 1

    callback = ENUMCHILDPROC(on_child)
    user32.EnumChildWindows(HWND(top_hwnd), callback, 0)
    return found[0] if found else None


def format_name(fmt: int) -> str:
    if fmt in FORMAT_NAMES:
        return FORMAT_NAMES[fmt]
    buf = ctypes.create_unicode_buffer(256)
    if user32.GetClipboardFormatNameW(fmt, buf, 256):
        return buf.value or f"0x{fmt:04X}"
    return f"0x{fmt:04X}"


class DibInfo:
    __slots__ = (
        "bpp",
        "height",
        "pixel_bytes",
        "pixel_offset",
        "valid",
        "width",
    )

    def __init__(
        self,
        width: int,
        height: int,
        bpp: int,
        pixel_offset: int,
        pixel_bytes: int,
        valid: bool,
    ):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.pixel_offset = pixel_offset
        self.pixel_bytes = pixel_bytes
        self.valid = valid


MAX_DIMENSION = 100_000


def parse_dib_header(dib: bytes) -> DibInfo | None:
    if len(dib) < 40:
        return None
    (
        header_size,
        width,
        height,
        planes,
        bpp,
        compression,
        _size_image,
        _xpels,
        _ypels,
        clr_used,
        _clr_important,
    ) = struct.unpack_from("<IiiHHIIiiII", dib, 0)
    if header_size < 12 or len(dib) < header_size:
        return None
    if planes != 1 or bpp not in (1, 4, 8, 16, 24, 32):
        return None
    if compression not in (BI_RGB, BI_BITFIELDS):
        return None
    if not (0 < abs(width) <= MAX_DIMENSION and 0 < abs(height) <= MAX_DIMENSION):
        return None
    if clr_used:
        colors = clr_used
    elif bpp <= 8:
        colors = 1 << bpp
    else:
        colors = 0
    mask_extra = 12 if compression == BI_BITFIELDS else 0
    pixel_offset = header_size + colors * 4 + mask_extra
    if len(dib) < pixel_offset:
        return None
    stride = ((abs(width) * bpp + 31) // 32) * 4
    pixel_bytes = stride * abs(height)
    if len(dib) < pixel_offset + pixel_bytes:
        return None
    return DibInfo(abs(width), height, bpp, pixel_offset, pixel_bytes, True)


def hbitmap_from_dib(dib) -> int | None:
    info = parse_dib_header(dib)
    if info is None:
        return None
    buf = ctypes.create_string_buffer(bytes(dib), len(dib))
    bits = c_void_p(0)
    hbmp = gdi32.CreateDIBSection(
        None, ctypes.addressof(buf), DIB_RGB_COLORS, byref(bits), None, 0
    )
    if not hbmp:
        return None
    if not bits:
        gdi32.DeleteObject(hbmp)
        return None
    memmove(bits, ctypes.byref(buf, info.pixel_offset), info.pixel_bytes)
    return hbmp


def enhmetafile_to_bytes(hemf: int | None) -> bytes | None:
    if not hemf:
        return None
    size = gdi32.GetEnhMetaFileBits(hemf, 0, None)
    if size <= 0:
        return None
    buf = ctypes.create_string_buffer(size)
    written = gdi32.GetEnhMetaFileBits(hemf, size, buf)
    if written <= 0 or written > size:
        return None
    return buf.raw[:written]


def bytes_to_enhmetafile(data) -> int | None:
    if not data:
        return None
    buf = ctypes.create_string_buffer(bytes(data), len(data))
    hemf = gdi32.SetEnhMetaFileBits(len(data), buf)
    return hemf or None


def metapict_pack(mm: int, x_ext: int, y_ext: int, bits: bytes) -> bytes:
    return struct.pack("<lll", mm, x_ext, y_ext) + bits


def metapict_unpack(payload) -> tuple[int, int, int, bytes] | None:
    if len(payload) < 12:
        return None
    mm, x_ext, y_ext = struct.unpack_from("<lll", payload, 0)
    return mm, x_ext, y_ext, bytes(payload[12:])


def capture_metapict(handle: int | None) -> bytes | None:
    if not handle:
        return None
    raw_ptr = kernel32.GlobalLock(handle)
    if not raw_ptr:
        return None
    try:
        pict = ctypes.cast(raw_ptr, POINTER(METAFILEPICT)).contents
        mm, x_ext, y_ext, hmf = pict.mm, pict.xExt, pict.yExt, pict.hMF
    finally:
        kernel32.GlobalUnlock(handle)
    if not hmf:
        return None
    size = gdi32.GetMetaFileBitsEx(hmf, 0, None)
    if size <= 0:
        return None
    buf = ctypes.create_string_buffer(size)
    written = gdi32.GetMetaFileBitsEx(hmf, size, buf)
    if written <= 0 or written > size:
        return None
    return metapict_pack(mm, x_ext, y_ext, buf.raw[:written])


def build_metapict_global(payload: bytes) -> int | None:
    unpacked = metapict_unpack(payload)
    if unpacked is None:
        return None
    mm, x_ext, y_ext, bits = unpacked
    hmf = None
    if bits:
        buf = ctypes.create_string_buffer(bytes(bits), len(bits))
        hmf = gdi32.SetMetaFileBitsEx(len(bits), buf)
        if not hmf:
            return None
    outer = kernel32.GlobalAlloc(GMEM_MOVEABLE, ctypes.sizeof(METAFILEPICT))
    if not outer:
        if hmf:
            gdi32.DeleteMetaFile(hmf)
        return None
    ptr = kernel32.GlobalLock(outer)
    if not ptr:
        if hmf:
            gdi32.DeleteMetaFile(hmf)
        kernel32.GlobalFree(outer)
        return None
    try:
        pict = ctypes.cast(ptr, POINTER(METAFILEPICT)).contents
        pict.mm = mm
        pict.xExt = x_ext
        pict.yExt = y_ext
        pict.hMF = HANDLE(hmf) if hmf else HANDLE(0)
    finally:
        kernel32.GlobalUnlock(outer)
    return outer


def palette_to_logpalette(hpal: int | None) -> bytes | None:
    if not hpal:
        return None
    count_buf = ctypes.create_string_buffer(2)
    got = gdi32.GetObjectW(hpal, 2, count_buf)
    if got != 2:
        return None
    (entries_count,) = struct.unpack_from("<H", count_buf.raw, 0)
    entries_buf = ctypes.create_string_buffer(entries_count * 4)
    written = gdi32.GetPaletteEntries(hpal, 0, entries_count, entries_buf)
    if written != entries_count:
        return None
    return struct.pack("<HH", 0x0300, entries_count) + entries_buf.raw[: entries_count * 4]


def palette_from_logpalette(data) -> int | None:
    if len(data) < 4:
        return None
    version, entries = struct.unpack_from("<HH", data, 0)
    if version != 0x0300:
        return None
    if len(data) < 4 + entries * 4:
        return None
    buf = ctypes.create_string_buffer(bytes(data), len(data))
    hpal = gdi32.CreatePalette(buf)
    return hpal or None
