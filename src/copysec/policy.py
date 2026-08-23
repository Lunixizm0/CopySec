from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    name: str
    path: str | None = None
    host_pid: int | None = None

    @property
    def name_lower(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Decision:
    allowed: bool
    rule: str
    requester: ProcInfo | None
    foreground: ProcInfo | None


class Policy:
    def __init__(
        self,
        tree,
        allowlist: set[str] | None = None,
        allow_uwp_frame_host: bool = False,
        deny_unknown_requester: bool = True,
        self_pid: int | None = None,
    ):
        self.tree = tree
        entries = allowlist or set()
        self._name_entries = set()
        self._path_entries = set()
        for entry in entries:
            lowered = entry.lower()
            if "/" in lowered or "\\" in lowered:
                self._path_entries.add(os.path.normcase(os.path.normpath(lowered)))
            else:
                self._name_entries.add(lowered)
        self.allow_uwp_frame_host = allow_uwp_frame_host
        self.deny_unknown_requester = deny_unknown_requester
        self.self_pid = os.getpid() if self_pid is None else self_pid

    def _allowlisted(self, req: ProcInfo) -> bool:
        if req.name_lower in self._name_entries:
            return True
        if req.path and self._path_entries:
            normalized = os.path.normcase(os.path.normpath(req.path))
            return normalized in self._path_entries
        return False

    def decide(self, requester_pid: int | None) -> Decision:
        fg = self.tree.foreground()
        if requester_pid is None:
            if self.deny_unknown_requester:
                return Decision(False, "unknown-requester", None, fg)
            return Decision(True, "unknown-requester-allowed", None, fg)
        if requester_pid == self.self_pid:
            return Decision(True, "self", None, fg)
        req = self.tree.resolve(requester_pid)
        if req is None:
            return Decision(False, "unresolvable-requester", None, fg)
        if self._allowlisted(req):
            return Decision(True, "allowlist", req, fg)
        if fg is not None:
            if requester_pid == fg.pid:
                return Decision(True, "foreground-window", req, fg)
            if fg.pid in self.tree.ancestors(requester_pid):
                return Decision(True, "descendant-of-foreground", req, fg)
        if self.allow_uwp_frame_host and req.name_lower == "applicationframehost.exe":
            return Decision(True, "uwp-frame-host", req, fg)
        return Decision(False, "no-match", req, fg)
