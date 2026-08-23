from __future__ import annotations

from collections import deque


class RollingStats:
    def __init__(self, maxlen: int = 64):
        self._samples: deque[float] = deque(maxlen=maxlen)

    def add(self, value_ms: float) -> tuple[float, float]:
        self._samples.append(value_ms)
        return round(value_ms, 3), round(sum(self._samples) / len(self._samples), 3)

    def avg(self) -> float | None:
        if not self._samples:
            return None
        return round(sum(self._samples) / len(self._samples), 3)

    def last(self) -> float | None:
        if not self._samples:
            return None
        return round(self._samples[-1], 3)

    def count(self) -> int:
        return len(self._samples)
