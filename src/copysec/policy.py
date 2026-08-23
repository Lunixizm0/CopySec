from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcInfo:
    pid: int
    exe: str
    host_pid: int | None = None

    @property
    def exe_lower(self) -> str:
        return self.exe.lower()


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
        self.allowlist = {a.lower() for a in (allowlist or set())}
        self.allow_uwp_frame_host = allow_uwp_frame_host
        self.deny_unknown_requester = deny_unknown_requester
        self.self_pid = os.getpid() if self_pid is None else self_pid

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
        if req.exe_lower in self.allowlist:
            return Decision(True, "allowlist", req, fg)
        if fg is not None:
            if requester_pid == fg.pid:
                return Decision(True, "foreground-window", req, fg)
            if fg.pid in self.tree.ancestors(requester_pid):
                return Decision(True, "descendant-of-foreground", req, fg)
        if self.allow_uwp_frame_host and req.exe_lower == "applicationframehost.exe":
            return Decision(True, "uwp-frame-host", req, fg)
        return Decision(False, "no-match", req, fg)
