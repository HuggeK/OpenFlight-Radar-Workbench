"""Field-session tools for an OpenFlight unit running the IWR6843 self-trigger.

These read what OpenFlight already writes during a range or studio session:
the kiosk terminal log, a ``gpiomon`` edge log of the OPS243 J3 pin 1 line,
and the camera captures' trigger timestamps. Nothing here talks to a radar.

    python -m openflight_bench.session triage kiosk_20261101_113221.log
    python -m openflight_bench.session latency --camera camera_triggers.csv \\
        --gpio ops_j3.log --window normal 2026-11-01T11:32:21+01:00 2026-11-01T12:13:44+01:00
"""

from .gpio import Edge, load_edges
from .latency import LatencyRow, LatencyWindow, load_camera_triggers, match_triggers, summarize
from .logs import KioskSession, Shot, Trigger, parse_kiosk_log

__all__ = [
    "Edge",
    "KioskSession",
    "LatencyRow",
    "LatencyWindow",
    "Shot",
    "Trigger",
    "load_camera_triggers",
    "load_edges",
    "match_triggers",
    "parse_kiosk_log",
    "summarize",
]
