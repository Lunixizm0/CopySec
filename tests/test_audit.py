import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copysec.audit import Audit


def make_audit(tmp_path, max_bytes):
    a = Audit(tmp_path, log_allows=False, verbose=False)
    a.MAX_FILE_BYTES = max_bytes
    return a


def sorted_files(tmp_path):
    def seq(path):
        parts = path.stem.split(".")
        return int(parts[1]) if len(parts) > 1 else -1

    return sorted(tmp_path.glob("audit-*.jsonl"), key=seq)


def test_rotation_creates_suffixed_files(tmp_path):
    audit = make_audit(tmp_path, 400)
    for i in range(40):
        audit.event("tick", rate_key=None, n=i)

    files = sorted_files(tmp_path)
    assert len(files) >= 3
    for f in files:
        assert f.stat().st_size < 400 + 200


def test_rotation_writes_latest_to_last_file(tmp_path):
    audit = make_audit(tmp_path, 400)
    for i in range(40):
        audit.event("tick", rate_key=None, n=i)

    files = sorted_files(tmp_path)
    last_line = files[-1].read_text(encoding="utf-8").strip().splitlines()[-1]
    assert '"n": 39' in last_line


def test_no_rotation_under_limit(tmp_path):
    audit = make_audit(tmp_path, 1_000_000)
    for i in range(10):
        audit.event("tick", rate_key=None, n=i)
    files = list(tmp_path.glob("audit-*.jsonl"))
    assert len(files) == 1


def test_resume_after_restart_picks_next_file(tmp_path):
    first = make_audit(tmp_path, 400)
    for i in range(30):
        first.event("tick", rate_key=None, n=i)

    second = Audit(tmp_path, log_allows=False, verbose=False)
    second.MAX_FILE_BYTES = 400
    second.event("after-restart", rate_key=None)

    files = sorted_files(tmp_path)
    assert len(files) >= 2
    last_line = files[-1].read_text(encoding="utf-8").strip().splitlines()[-1]
    assert "after-restart" in last_line

def test_rate_limit_does_not_starve(tmp_path, monkeypatch):
    from copysec import audit as audit_mod

    clock = {"t": 0.0}
    monkeypatch.setattr(audit_mod.time, "monotonic", lambda: clock["t"])
    audit = make_audit(tmp_path, 1_000_000)
    for _ in range(8):
        audit.event("tick", rate_key="tick")
        clock["t"] += 0.25
    files = sorted_files(tmp_path)
    assert len(files) == 1
    lines = files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

def test_prune_deletes_oldest_over_budget(tmp_path):
    audit = make_audit(tmp_path, 1_000_000)
    audit.MAX_DIR_BYTES = 1000
    audit.TARGET_DIR_BYTES = 400
    for i in range(5):
        f = tmp_path / f"audit-2026010{i}.jsonl"
        f.write_text("x" * 300, encoding="utf-8")
        os.utime(f, (1000 + i * 100, 1000 + i * 100))
    audit.event("boot", rate_key=None)
    audit._prune()
    remaining = sorted(p.name for p in tmp_path.glob("audit-*.jsonl"))
    total = sum(p.stat().st_size for p in tmp_path.glob("audit-*.jsonl"))
    assert len(remaining) == 2
    assert "audit-20260104.jsonl" in remaining
    assert "audit-20260103.jsonl" not in remaining
    assert total <= 400 + 200


def test_prune_keeps_everything_under_budget(tmp_path):
    audit = make_audit(tmp_path, 1_000_000)
    for i in range(3):
        f = tmp_path / f"audit-2026010{i}.jsonl"
        f.write_text("x" * 100, encoding="utf-8")
    audit._prune()
    assert len(list(tmp_path.glob("audit-*.jsonl"))) == 3


def test_prune_leaves_non_audit_files_alone(tmp_path):
    audit = make_audit(tmp_path, 1_000_000)
    audit.MAX_DIR_BYTES = 100
    audit.TARGET_DIR_BYTES = 50
    other = tmp_path / "other.txt"
    other.write_text("y" * 500, encoding="utf-8")
    os.utime(other, (1, 1))
    audit._prune()
    assert other.exists()
