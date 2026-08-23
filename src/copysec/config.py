from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Config:
    allowlist: list[str] = field(default_factory=lambda: ["svchost.exe"])
    allow_uwp_frame_host: bool = False
    deny_unknown_requester: bool = True
    log_allows: bool = False

    def apply_dict(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        if isinstance(data.get("allowlist"), list):
            self.allowlist = [str(x) for x in data["allowlist"]]
        for key in ("allow_uwp_frame_host", "deny_unknown_requester", "log_allows"):
            if key in data and isinstance(data[key], bool):
                setattr(self, key, data[key])


def default_config_path() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / "AppData" / "Local"
    return base / "CopySec" / "config.json"


def load_or_create(path: Path) -> Config:
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = Config()
    if path.exists():
        try:
            cfg.apply_dict(json.loads(path.read_text(encoding="utf-8-sig")))
        except (OSError, json.JSONDecodeError):
            pass
    else:
        try:
            path.write_text(
                json.dumps(asdict(cfg), indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass
    return cfg
