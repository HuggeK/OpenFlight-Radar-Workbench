"""Trigger latency and jitter from camera trigger stamps and the J3 edge log.

OpenFlight's camera capture records ``trigger_host_timestamp_ns`` (monotonic)
for every IWR self-trigger, taken when the host acts on it and writes ``S!``.
Pairing each one with the next J3 rising edge gives S! -> OPS receipt; the
following falling edge gives the OPS capture window. Grouping by wall-clock
windows compares runs, e.g. normal scheduling against ``chrt -f 50``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import statistics

from .gpio import Edge

MAX_RISE_DELAY_S = 0.3
MAX_WINDOW_S = 0.2


@dataclass(frozen=True)
class CameraTrigger:
    sequence: int
    epoch_s: float
    monotonic_s: float


@dataclass(frozen=True)
class LatencyRow:
    trigger: CameraTrigger
    rise_ms: float | None  # S! -> J3 rising edge
    window_ms: float | None  # J3 rising -> falling edge


@dataclass(frozen=True)
class LatencyWindow:
    """A named wall-clock span, start inclusive, end exclusive."""

    name: str
    start: datetime
    end: datetime

    def contains(self, epoch_s: float) -> bool:
        return self.start.timestamp() <= epoch_s < self.end.timestamp()


def load_camera_triggers(path: str | Path) -> list[CameraTrigger]:
    """Read the CSV written from ``camera_*/metadata.json`` (see session_tools)."""
    with open(path, newline="", encoding="utf-8") as handle:
        return [
            CameraTrigger(
                sequence=int(row["sequence"]),
                epoch_s=float(row["trigger_epoch_s"]),
                monotonic_s=int(row["trigger_monotonic_ns"]) / 1e9,
            )
            for row in csv.DictReader(handle)
        ]


def match_triggers(triggers: list[CameraTrigger], edges: list[Edge]) -> list[LatencyRow]:
    """Pair every trigger with its J3 rise and fall; unmatched values stay None."""
    rising = [e.time_s for e in edges if e.kind == "rising"]
    falling = [e.time_s for e in edges if e.kind == "falling"]
    rows = []
    for trigger in sorted(triggers, key=lambda t: t.epoch_s):
        rise = next((t for t in rising if 0 <= t - trigger.monotonic_s < MAX_RISE_DELAY_S), None)
        fall = None
        if rise is not None:
            fall = next((t for t in falling if 0 < t - rise < MAX_WINDOW_S), None)
        rows.append(
            LatencyRow(
                trigger=trigger,
                rise_ms=None if rise is None else (rise - trigger.monotonic_s) * 1000,
                window_ms=None if fall is None else (fall - rise) * 1000,
            )
        )
    return rows


def describe(values: list[float]) -> dict[str, float | int | None]:
    """n, mean, stdev, min, max and p95 of ``values``."""
    if not values:
        return {"n": 0, "mean": None, "stdev": None, "min": None, "max": None, "p95": None}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "mean": statistics.fmean(ordered),
        "stdev": statistics.stdev(ordered) if len(ordered) > 1 else 0.0,
        "min": ordered[0],
        "max": ordered[-1],
        "p95": ordered[int(0.95 * (len(ordered) - 1))],
    }


def summarize(rows: list[LatencyRow], windows: list[LatencyWindow]) -> dict[str, dict]:
    """Per window: trigger count and stats for the rise and window columns."""
    out = {}
    for window in windows:
        selected = [r for r in rows if window.contains(r.trigger.epoch_s)]
        out[window.name] = {
            "triggers": len(selected),
            "rise_ms": describe([r.rise_ms for r in selected if r.rise_ms is not None]),
            "window_ms": describe([r.window_ms for r in selected if r.window_ms is not None]),
        }
    return out
