"""Read a ``gpiomon -F "%S %E"`` edge log.

On the OPS243-A, J3 pin 1 (the alert output) rises about 0.1-0.2 ms after the
radar receives ``S!`` in rolling-buffer mode and falls when its capture
closes. Logging it on a Pi GPIO gives the host a hardware timestamp for both,
on the same monotonic clock as the camera's trigger timestamps:

    gpiomon -c gpiochip0 -e both -F "%S %E" 18 > ops_j3.log
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Edge:
    """One edge: CLOCK_MONOTONIC seconds and ``rising`` or ``falling``."""

    time_s: float
    kind: str


def load_edges(path: str | Path) -> list[Edge]:
    """Edges in file order; lines that are not ``<seconds> <rising|falling>`` are skipped."""
    edges = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) != 2 or parts[1] not in ("rising", "falling"):
            continue
        try:
            edges.append(Edge(float(parts[0]), parts[1]))
        except ValueError:
            continue
    return edges
