"""Job benchmarks (guidelines/06_local_pilot.md, rule 4): wall time, peak memory, bytes written.

Usage:
    with Benchmark("download", unit="chl300_2026", out_path=dst) as b:
        ...work...
    -> appends one row to results/tables/benchmarks.csv (shared by all domains)

n_cell_days (grid cells x days processed) lets pilot costs be scaled to the full domain:
cost per cell-day x full-domain cell-days. Set it in the constructor or on the object inside the block.
"""
from __future__ import annotations

import csv
import datetime as dt
import platform
import threading
import time
from pathlib import Path

import psutil

from .config import BENCHMARKS, DOMAIN_NAME


class Benchmark:
    def __init__(self, step: str, unit: str, out_path: Path | None = None,
                 log: Path = BENCHMARKS, note: str = "", n_cell_days: int | None = None):
        self.step, self.unit, self.out_path, self.log, self.note = step, unit, out_path, log, note
        self.n_cell_days = n_cell_days
        self.status = "ok"

    def _sample(self):
        proc = psutil.Process()
        while not self._stop.is_set():
            try:
                rss = proc.memory_info().rss + sum(c.memory_info().rss for c in proc.children(recursive=True))
                self.peak = max(self.peak, rss)
            except psutil.Error:
                pass
            self._stop.wait(0.5)

    def __enter__(self):
        self.t0, self.peak = time.perf_counter(), 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        self._thread.join()
        wall = time.perf_counter() - self.t0
        if exc_type is not None:
            self.status = f"failed: {exc_type.__name__}"
        size = 0
        if self.out_path is not None and Path(self.out_path).exists():
            p = Path(self.out_path)
            size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size
        new = not self.log.exists()
        self.log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["utc", "host", "cpus", "domain", "step", "unit", "status", "wall_s", "peak_mem_mb",
                            "output_mb", "n_cell_days", "note"])
            w.writerow([f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ}", platform.node(),
                        psutil.cpu_count(), DOMAIN_NAME, self.step, self.unit, self.status, round(wall, 1),
                        round(self.peak / 1e6, 1), round(size / 1e6, 1), self.n_cell_days or "", self.note])
        return False
