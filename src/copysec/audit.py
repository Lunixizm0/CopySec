from __future__ import annotations

import datetime as _dt
import json
import time
from pathlib import Path


class Audit:
    MIN_INTERVAL = 1.0
    MAX_FILE_BYTES = 1_000_000
    MAX_DIR_BYTES = 10_000_000
    TARGET_DIR_BYTES = 5_000_000
    RATE_KEY_TTL = 3600.0
    RATE_PRUNE_INTERVAL = 600.0

    def __init__(self, log_dir: Path, log_allows: bool = False, verbose: bool = False):
        import os

        self.log_allows = log_allows
        self.verbose = verbose
        self.debug = os.environ.get("COPYSEC_DEBUG") == "1"
        if self.debug:
            self.log_allows = True
        self._log_dir = Path(log_dir)
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            self._log_dir = None
        self._last: dict[tuple, float] = {}
        self._dropped: dict[tuple, int] = {}
        self._rate_pruned_at = time.monotonic()
        self._prune()

    def _prune(self) -> None:
        if self._log_dir is None:
            return
        try:
            sized = []
            total = 0
            for path in sorted(self._log_dir.glob("audit-*.jsonl")):
                try:
                    st = path.stat()
                except OSError:
                    continue
                sized.append((st.st_mtime, path.name, st.st_size, path))
                total += st.st_size
            if total <= self.MAX_DIR_BYTES:
                return
            freed = 0
            removed = 0
            for _, _, size, path in sorted(sized):
                if total - freed <= self.TARGET_DIR_BYTES:
                    break
                try:
                    path.unlink()
                except OSError:
                    continue
                freed += size
                removed += 1
            if removed:
                self.event("logs_pruned", removed=removed, freed_bytes=freed)
        except OSError:
            pass

    def _path(self) -> Path | None:
        if self._log_dir is None:
            return None
        day = _dt.datetime.now().astimezone().date().strftime("%Y%m%d")
        base = f"audit-{day}"
        path = self._log_dir / f"{base}.jsonl"
        seq = 0
        try:
            while path.exists() and path.stat().st_size >= self.MAX_FILE_BYTES:
                seq += 1
                path = self._log_dir / f"{base}.{seq}.jsonl"
        except OSError:
            return None
        return path

    def _write(self, record: dict) -> None:
        record.setdefault("ts", _dt.datetime.now().astimezone().isoformat(timespec="milliseconds"))
        line = json.dumps(record, ensure_ascii=False)
        path = self._path()
        if path is not None:
            try:
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError:
                pass
        if self.verbose:
            try:
                print(line, flush=True)
            except (OSError, UnicodeEncodeError):
                pass

    def _prune_rate_keys(self, now: float) -> None:
        self._rate_pruned_at = now
        stale = [key for key, ts in self._last.items() if now - ts > self.RATE_KEY_TTL]
        for key in stale:
            del self._last[key]
            self._dropped.pop(key, None)

    def _rate_ok(self, key: tuple) -> bool:
        now = time.monotonic()
        if now - self._rate_pruned_at >= self.RATE_PRUNE_INTERVAL:
            self._prune_rate_keys(now)
        last = self._last.get(key)
        if last is not None and now - last < self.MIN_INTERVAL:
            self._dropped[key] = self._dropped.get(key, 0) + 1
            return False
        self._last[key] = now
        return True

    @staticmethod
    def _proc_dict(info) -> dict | None:
        if info is None:
            return None
        record = {"pid": info.pid, "exe": info.name}
        if info.path:
            record["path"] = info.path
        if getattr(info, "host_pid", None):
            record["host_pid"] = info.host_pid
        return record

    def access(
        self,
        allowed: bool,
        rule: str,
        fmt: int,
        fmt_name: str,
        requester=None,
        foreground=None,
    ) -> None:
        if allowed and not self.log_allows:
            return
        key = ("access", allowed, getattr(requester, "pid", None), fmt)
        if not self._rate_ok(key):
            return
        record = {
            "event": "allow" if allowed else "deny",
            "rule": rule,
            "fmt": fmt,
            "fmt_name": fmt_name,
            "requester": self._proc_dict(requester),
            "foreground": self._proc_dict(foreground),
        }
        dropped = self._dropped.pop(key, None)
        if dropped:
            record["suppressed_repeats"] = dropped
        self._write(record)

    def event(self, name: str, rate_key: str | None = None, **fields) -> None:
        if rate_key is not None:
            key = ("event", rate_key)
            if not self._rate_ok(key):
                return
            dropped = self._dropped.pop(key, None)
            if dropped:
                fields["suppressed_repeats"] = dropped
        self._write({"event": name, **fields})

    def probe(self, **fields) -> None:
        if self.debug:
            self._write({"event": "probe", **fields})
