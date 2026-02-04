from __future__ import annotations
from typing import Dict, List
import time
import threading
import tracemalloc


class MetricsRegistry:
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.errors: Dict[str, int] = {}
        self.timers: Dict[str, List[float]] = {}
        self.gauges: Dict[str, float] = {}
        self.created_at = time.perf_counter()
        tracemalloc.start()
        self.lock = threading.Lock()

    def inc(self, name: str, amount: int = 1):
        with self.lock:
            self.counters[name] = self.counters.get(name, 0) + amount

    def error(self, name: str, amount: int = 1):
        with self.lock:
            self.errors[name] = self.errors.get(name, 0) + amount

    def observe(self, name: str, value_ms: float):
        with self.lock:
            arr = self.timers.get(name)
            if arr is None:
                arr = []
                self.timers[name] = arr
            arr.append(value_ms)

    def set_gauge(self, name: str, value: float):
        with self.lock:
            self.gauges[name] = value

    def snapshot(self):
        with self.lock:
            now = time.perf_counter()
            uptime = now - self.created_at
            current, peak = tracemalloc.get_traced_memory()
            return {
                "counters": dict(self.counters),
                "errors": dict(self.errors),
                "timers": {k: list(v) for k, v in self.timers.items()},
                "gauges": dict(self.gauges),
                "uptime_sec": uptime,
                "memory_bytes": {"current": current, "peak": peak},
                "threads": threading.active_count(),
                "process_cpu_sec": time.process_time(),
            }


metrics = MetricsRegistry()
