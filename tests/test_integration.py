import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.platform != "win32", reason="requires the Windows clipboard"),
]

MATRICES = [
    ("matrix_a.ps1", "MATRIX-A: PASS"),
    ("matrix_b.ps1", "MATRIX-B: PASS"),
]


@pytest.mark.parametrize("script,expected", MATRICES)
def test_matrix(script: str, expected: str) -> None:
    proc = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / script),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=180,
        check=False,
    )
    combined = proc.stdout + proc.stderr
    if "clipboard reader daemon did not start" in combined:
        pytest.skip("interactive desktop session unavailable")
    detail = f"\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    assert proc.returncode == 0 and expected in proc.stdout, detail
