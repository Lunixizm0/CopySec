import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copysec.stats import RollingStats


def test_empty_stats():
    s = RollingStats()
    assert s.count() == 0
    assert s.avg() is None
    assert s.last() is None


def test_add_returns_last_and_avg():
    s = RollingStats()
    last, avg = s.add(10.0)
    assert last == 10.0
    assert avg == 10.0
    last, avg = s.add(20.0)
    assert last == 20.0
    assert avg == 15.0
    assert s.count() == 2


def test_window_eviction():
    s = RollingStats(maxlen=3)
    for v in (1.0, 2.0, 3.0, 4.0):
        s.add(v)
    assert s.count() == 3
    assert s.last() == 4.0
    assert s.avg() == 3.0


def test_rounding_to_three_decimals():
    s = RollingStats()
    _, avg = s.add(1.00004)
    assert avg == 1.0
    last, _ = s.add(2.12345)
    assert last == 2.123
