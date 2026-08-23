import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copysec.policy import Policy, ProcInfo


class FakeTree:
    def __init__(self, names, parents, fg):
        self._names = names
        self._parents = parents
        self._fg = fg

    def resolve(self, pid):
        name = self._names.get(pid)
        return ProcInfo(pid, name) if name else None

    def ancestors(self, pid):
        return tuple(self._parents.get(pid, ()))

    def foreground(self):
        return ProcInfo(self._fg, "fgapp.exe")


class PathFakeTree:
    def __init__(self, names, paths, parents, fg):
        self._names = names
        self._paths = paths
        self._parents = parents
        self._fg = fg

    def resolve(self, pid):
        name = self._names.get(pid)
        if not name:
            return None
        return ProcInfo(pid, name, self._paths.get(pid))

    def ancestors(self, pid):
        return tuple(self._parents.get(pid, ()))

    def foreground(self):
        return ProcInfo(self._fg, "fgapp.exe")


def make_policy(**kw):
    defaults = {"allowlist": {"svchost.exe"}, "self_pid": 99999}
    defaults.update(kw)
    return Policy(FakeTree(
        names={100: "chrome.exe", 200: "helper.exe", 300: "worker.exe", 400: "evil.exe", 600: "svchost.EXE"},
        parents={200: [100], 300: [200, 100], 400: [], 600: []},
        fg=100,
    ), **defaults)


def test_self_allowed():
    d = make_policy().decide(99999)
    assert d.allowed and d.rule == "self"


def test_foreground_exact_allowed():
    d = make_policy().decide(100)
    assert d.allowed and d.rule == "foreground-window"


def test_child_of_foreground_allowed():
    d = make_policy().decide(200)
    assert d.allowed and d.rule == "descendant-of-foreground"


def test_grandchild_of_foreground_allowed():
    d = make_policy().decide(300)
    assert d.allowed and d.rule == "descendant-of-foreground"


def test_unrelated_denied():
    d = make_policy().decide(400)
    assert not d.allowed and d.rule == "no-match"


def test_unknown_requester_denied_by_default():
    d = make_policy().decide(None)
    assert not d.allowed and d.rule == "unknown-requester"


def test_unknown_requester_allowed_when_configured():
    d = make_policy(deny_unknown_requester=False).decide(None)
    assert d.allowed and d.rule == "unknown-requester-allowed"


def test_unresolvable_pid_denied():
    d = make_policy().decide(500)
    assert not d.allowed and d.rule == "unresolvable-requester"


def test_allowlist_case_insensitive():
    d = make_policy().decide(600)
    assert d.allowed and d.rule == "allowlist"


def test_uwp_frame_host_opt_in():
    policy = make_policy(allow_uwp_frame_host=True)
    policy.tree = FakeTree({700: "ApplicationFrameHost.exe"}, {700: []}, 100)
    d = policy.decide(700)
    assert d.allowed and d.rule == "uwp-frame-host"


def test_procinfo_host_pid_defaults_to_none():
    info = ProcInfo(42, "app.exe")
    assert info.host_pid is None
    assert info.name_lower == "app.exe"


def test_allowlist_full_path_matches_exact():
    policy = make_policy(allowlist={r"C:\Windows\System32\svchost.exe"})
    policy.tree = PathFakeTree(
        names={600: "svchost.EXE"},
        paths={600: r"C:\WINDOWS\system32\svchost.exe"},
        parents={600: []},
        fg=100,
    )
    d = policy.decide(600)
    assert d.allowed and d.rule == "allowlist"


def test_allowlist_full_path_rejects_same_name_other_dir():
    policy = make_policy(allowlist={r"C:\Windows\System32\svchost.exe"})
    policy.tree = PathFakeTree(
        names={400: "svchost.exe"},
        paths={400: r"C:\Users\evil\svchost.exe"},
        parents={400: []},
        fg=100,
    )
    d = policy.decide(400)
    assert not d.allowed and d.rule == "no-match"


def test_allowlist_path_entry_fail_closed_when_path_unknown():
    policy = make_policy(allowlist={r"C:\Windows\System32\svchost.exe"},)
    policy.tree = PathFakeTree(
        names={600: "svchost.exe"},
        paths={600: None},
        parents={600: []},
        fg=100,
    )
    d = policy.decide(600)
    assert not d.allowed and d.rule == "no-match"


def test_bare_name_still_matches_even_with_path_entry_present():
    policy = make_policy(
        allowlist={r"C:\Windows\System32\svchost.exe", "helper.exe"}
    )
    d = policy.decide(200)
    assert d.allowed and d.rule == "allowlist"
