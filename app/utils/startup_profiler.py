from __future__ import annotations

import time
from contextlib import contextmanager


class StartupProfiler:
    def __init__(self, process_start: float | None = None):
        self.process_start = process_start or time.perf_counter()
        self._last = self.process_start
        self.events: list[tuple[str, float, float]] = []

    def checkpoint(self, name: str, at: float | None = None):
        now = at or time.perf_counter()
        duration_ms = (now - self._last) * 1000
        total_ms = (now - self.process_start) * 1000
        self.events.append((name, duration_ms, total_ms))
        print(f"[Startup] {name}: {duration_ms:.0f} ms (total {total_ms:.0f} ms)")
        self._last = now

    @contextmanager
    def span(self, name: str):
        start = time.perf_counter()
        yield
        now = time.perf_counter()
        duration_ms = (now - start) * 1000
        total_ms = (now - self.process_start) * 1000
        self.events.append((name, duration_ms, total_ms))
        print(f"[Startup] {name}: {duration_ms:.0f} ms (total {total_ms:.0f} ms)")
        self._last = now

    def top(self, count: int = 3) -> list[tuple[str, float]]:
        return sorted(((name, duration) for name, duration, _ in self.events), key=lambda x: x[1], reverse=True)[:count]
