import time

from copysec import winapi


def main(duration: float = 6.0) -> None:
    end = time.monotonic() + duration
    counts: dict[str, int] = {}
    free = 0
    while time.monotonic() < end:
        hwnd = winapi.open_clipboard_window_hwnd()
        if not hwnd:
            free += 1
            label = "(free)"
        else:
            pid = winapi.window_pid(hwnd)
            try:
                import psutil

                label = f"{psutil.Process(pid).name()} pid={pid}" if pid else "pid=?"
            except Exception:  # noqa: BLE001
                label = f"hwnd={hwnd:#x} pid={pid}"
        counts[label] = counts.get(label, 0) + 1
        time.sleep(0.05)
    for label, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"{n:4d}  {label}")


if __name__ == "__main__":
    main()
