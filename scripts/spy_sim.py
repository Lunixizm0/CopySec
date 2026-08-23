import ctypes
import time

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_int
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalSize.restype = ctypes.c_size_t
kernel32.GlobalSize.argtypes = [ctypes.c_void_p]

CF_UNICODETEXT = 13


def read_clipboard_text():
    if not user32.OpenClipboard(None):
        return "<locked>"
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return "<empty>"
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return "<null>"
        size = kernel32.GlobalSize(h)
        ptr = kernel32.GlobalLock(h)
        if not ptr:
            return "<lock-failed>"
        try:
            data = ctypes.string_at(ptr, size)
        finally:
            kernel32.GlobalUnlock(h)
        return data.decode("utf-16-le", "replace")[:80]
    finally:
        user32.CloseClipboard()


def main():
    print("[spy_sim] polling clipboard in the background... Exit: Ctrl+C")
    last = None
    while True:
        try:
            current = read_clipboard_text()
        except KeyboardInterrupt:
            break
        if current != last:
            print(f"[{time.strftime('%H:%M:%S')}] spy_sim read: {current!r}")
            last = current
        time.sleep(0.3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
