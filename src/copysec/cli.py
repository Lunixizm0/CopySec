from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from .audit import Audit
from .config import default_config_path, load_or_create
from .guard import ClipboardGuard
from .policy import Policy
from .proctree import PsutilProcTree
from .store import ContentStore


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="copysec",
        description="Clipboard guard: only the active application and its process tree can access the clipboard.",
    )
    parser.add_argument("--no-tray", action="store_true", help="Run without the tray icon")
    parser.add_argument("--verbose", action="store_true", help="Also echo log records to the console")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config.json (default: %%USERPROFILE%%\\AppData\\Local\\CopySec\\config.json)",
    )
    parser.add_argument(
        "--smoke-seconds",
        type=float,
        default=None,
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

    args = _build_parser().parse_args(argv)
    config_path = args.config or default_config_path()
    cfg = load_or_create(config_path)
    log_dir = config_path.parent / "logs"

    audit = Audit(log_dir, log_allows=cfg.log_allows, verbose=args.verbose)
    bare = [entry for entry in cfg.allowlist if "/" not in entry and "\\" not in entry]
    if bare:
        audit.event("insecure_allowlist", entries=bare)
    tree = PsutilProcTree()

    def resolve_name(pid):
        info = tree.resolve(pid)
        return info.name if info else None

    policy = Policy(
        tree,
        allowlist=set(cfg.allowlist),
        allow_uwp_frame_host=cfg.allow_uwp_frame_host,
        deny_unknown_requester=cfg.deny_unknown_requester,
    )
    store = ContentStore(audit, resolve_name, max_format_bytes=cfg.max_format_bytes)
    guard = ClipboardGuard(policy, store, audit)

    audit.event(
        "started",
        pid=os.getpid(),
        python=sys.version.split()[0],
        config=str(config_path),
    )
    guard.start()
    if not guard.hwnd:
        print("[copysec] Failed to create guard window. See logs for details.", file=sys.stderr)
        return 1
    guard.request_adopt()

    print(f"[copysec] protection active | pid={os.getpid()}", flush=True)
    print(f"[copysec] config : {config_path}", flush=True)
    print(f"[copysec] logs   : {log_dir}", flush=True)
    print("[copysec] to stop: Ctrl+C (console) or tray > Exit", flush=True)

    exit_code = 0
    try:
        if args.no_tray or args.smoke_seconds is not None:
            deadline = (
                time.monotonic() + args.smoke_seconds
                if args.smoke_seconds is not None
                else None
            )
            while guard.is_alive:
                if deadline is not None and time.monotonic() >= deadline:
                    break
                time.sleep(0.2)
        else:
            from .tray import TrayApp

            TrayApp(guard, log_dir).run()
    except KeyboardInterrupt:
        print("\n[copysec] shutting down...", flush=True)
    finally:
        guard.stop()
        if guard.thread:
            guard.thread.join(timeout=5)
        store.clear()
        audit.event("stopped")
    return exit_code
