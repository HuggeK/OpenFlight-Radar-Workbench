"""Match TrackMan shots (SwingSync CSV export) to OpenFlight self-triggers.

SwingSync's "Export Session" CSV has a header row, a units row, then one row
per shot with an ISO 8601 UTC ``Date`` and speeds in km/h. The two systems'
clocks need not agree (on 2026-11-01 TrackMan ran 425.5 s ahead of the Pi's
NTP time), so the offset is found first: the one at which the most TrackMan
shots land within ``tolerance_s`` of an IWR trigger. Matching then pairs each
TrackMan shot with the nearest unclaimed trigger.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .logs import Trigger

KPH_PER_MPH = 1.609344


@dataclass(frozen=True)
class TrackmanShot:
    number: int
    time: datetime  # UTC, timezone-aware
    ball_mph: float | None
    club_mph: float | None
    smash: float | None
    launch_deg: float | None
    classification: str


@dataclass(frozen=True)
class Match:
    trackman: TrackmanShot
    trigger: Trigger | None
    delta_s: float | None  # trigger time - (TrackMan time - offset)


def _number(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


def load_swingsync_csv(path: str | Path) -> list[TrackmanShot]:
    """Shots from a SwingSync TrackMan export; the units row is skipped."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    shots = []
    for row in rows:
        if not row.get("Shot number", "").strip():
            continue  # units row
        ball = _number(row["Ball speed"])
        club = _number(row["Club speed"])
        shots.append(
            TrackmanShot(
                number=int(row["Shot number"]),
                time=datetime.fromisoformat(row["Date"].replace("Z", "+00:00")),
                ball_mph=None if ball is None else ball / KPH_PER_MPH,
                club_mph=None if club is None else club / KPH_PER_MPH,
                smash=_number(row["Smash factor"]),
                launch_deg=_number(row["Vertical Launch angle"]),
                classification=row.get("Classification", ""),
            )
        )
    return shots


def _epoch(trigger: Trigger, utc_offset_s: float) -> float:
    """Trigger time (naive local log time) as UTC epoch seconds."""
    return trigger.time.replace(tzinfo=timezone.utc).timestamp() - utc_offset_s


def find_offset(
    shots: list[TrackmanShot],
    triggers: list[Trigger],
    *,
    utc_offset_s: float,
    search_s: float = 900.0,
    step_s: float = 0.5,
    tolerance_s: float = 1.0,
) -> tuple[float, int]:
    """(TrackMan clock - OpenFlight clock, shots matched) that matches the most shots.

    Ties go to the offset with the smallest summed timing residual.
    ``utc_offset_s`` is the log's local offset from UTC (3600 for CET).
    """
    stamps = sorted(_epoch(t, utc_offset_s) for t in triggers)
    best = (0.0, -1, float("inf"))
    steps = int(search_s / step_s)
    for i in range(-steps, steps + 1):
        offset = i * step_s
        hits, residual = 0, 0.0
        for shot in shots:
            nearest = min((abs(shot.time.timestamp() - offset - s) for s in stamps), default=None)
            if nearest is not None and nearest < tolerance_s:
                hits += 1
                residual += nearest
        if hits > best[1] or (hits == best[1] and residual < best[2]):
            best = (offset, hits, residual)
    return best[0], best[1]


def match_shots(
    shots: list[TrackmanShot],
    triggers: list[Trigger],
    *,
    offset_s: float,
    utc_offset_s: float,
    tolerance_s: float = 1.5,
) -> list[Match]:
    """Each TrackMan shot with its nearest unclaimed trigger within ``tolerance_s``."""
    claimed: set[int] = set()
    matches = []
    for shot in sorted(shots, key=lambda s: s.time):
        target = shot.time.timestamp() - offset_s
        best = None
        for index, trigger in enumerate(triggers):
            if index in claimed:
                continue
            delta = _epoch(trigger, utc_offset_s) - target
            if abs(delta) <= tolerance_s and (best is None or abs(delta) < abs(best[1])):
                best = (index, delta)
        if best is None:
            matches.append(Match(shot, None, None))
        else:
            claimed.add(best[0])
            matches.append(Match(shot, triggers[best[0]], best[1]))
    return matches
