import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copysec.config import Config, load_or_create


def test_creates_default_config(tmp_path):
    path = tmp_path / "config.json"
    cfg = load_or_create(path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["allowlist"] == ["svchost.exe"]
    assert data["deny_unknown_requester"] is True
    assert cfg.allow_uwp_frame_host is False


def test_loads_existing_config(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "allowlist": ["foo.exe", "bar.exe"],
        "log_allows": True,
        "deny_unknown_requester": False,
    }), encoding="utf-8")
    cfg = load_or_create(path)
    assert cfg.allowlist == ["foo.exe", "bar.exe"]
    assert cfg.log_allows is True
    assert cfg.deny_unknown_requester is False


def test_invalid_json_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")
    cfg = load_or_create(path)
    assert cfg == Config()
