import ctypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_int
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalSize.restype = ctypes.c_size_t
kernel32.GlobalSize.argtypes = [ctypes.c_void_p]

CF_UNICODETEXT = 13


def main():
    if not user32.OpenClipboard(None):
        print(f"RESULT: <clipboard-open-failed> err={ctypes.get_last_error()}")
        return
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            print("RESULT: <no-cfunicodetext>")
            return
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            print(f"RESULT: <null> err={ctypes.get_last_error()}")
            return
        size = kernel32.GlobalSize(h)
        ptr = kernel32.GlobalLock(h)
        if not ptr:
            print(f"RESULT: <lock-failed> size={size} err={ctypes.get_last_error()}")
            return
        try:
            raw = ctypes.string_at(ptr, size if size > 0 else 8192)
        finally:
            kernel32.GlobalUnlock(h)
        text = raw.decode("utf-16-le", "replace").split("\x00")[0]
        print(f"RESULT: {text!r} (size={size})")
    finally:
        user32.CloseClipboard()


if __name__ == "__main__":
    main()
