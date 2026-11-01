"""Replay LCMF-v1 on saved IWR dumps with different radar/ball heights, against TrackMan launch.

Run with OpenFlight's interpreter on the Pi. The shots file lists each matched
shot: {"tm", "hhmmss", "tm_ball", "tm_launch"} (built from the compare output).
Edit VARIANTS, NET_M, TEE_M and TILT_DEG for another session.

    ~/openflight/.venv/bin/python lcmf_height_replay.py shots.json
"""

import glob
import json
import math
import os
import statistics
import sys
from dataclasses import replace

from openflight.iwr6843.calibration import Calibration
from openflight.iwr6843.lcmf import estimate_lcmf_v1, prepare_lcmf_capture

DUMPS = os.path.expanduser("~/openflight_sessions/iwr6843")
VARIANTS = [  # (label, radar_height_m, ball_height_m)
    ("sunday radar 0.04 / ball 0.04", 0.04, 0.04),
    ("radar 0.04 / ball 0.061", 0.04, 0.061),
    ("radar 0.03 / ball 0.061", 0.03, 0.061),
    ("radar 0.05 / ball 0.061", 0.05, 0.061),
    ("radar 0.06 / ball 0.061", 0.06, 0.061),
]
NET_M = 5.30
TEE_M = 1.57
TILT_DEG = 9.9


def find_dump(hhmmss: str) -> str | None:
    hits = sorted(glob.glob(f"{DUMPS}/iwr6843_20261101_{hhmmss}_*.l3dump"))
    return hits[0] if hits else None


def main() -> int:
    shots = json.load(open(sys.argv[1]))
    base = Calibration.load()
    base.tee_range_m = TEE_M
    base.tilt_rad = math.radians(TILT_DEG)
    results = {label: [] for label, *_ in VARIANTS}
    for shot in shots:
        path = find_dump(shot["hhmmss"])
        if path is None:
            continue
        raw = open(path, "rb").read()
        prepared = prepare_lcmf_capture(raw)
        cells = [f"TM#{shot['tm']:<3} {shot['hhmmss']} TM {shot['tm_launch']:5.1f}"]
        for label, radar_h, ball_h in VARIANTS:
            cal = replace(base, meta=dict(base.meta, radar_height_m=radar_h))
            cal.tee_ball_height_m = ball_h
            try:
                r = estimate_lcmf_v1(raw, cal, ball_speed_mph=shot["tm_ball"], net_range_m=NET_M,
                                     tdm_sign_policy="positive", prepared=prepared)
                angle = r.angle_deg if r.accepted else None
            except Exception as exc:  # pylint: disable=broad-exception-caught
                angle, r = None, None
                print("  error", label, type(exc).__name__, exc)
            results[label].append((shot["tm"], angle, shot["tm_launch"]))
            cells.append("   -  " if angle is None else f"{angle:6.1f}")
        print(" ".join(cells))
    print()
    both = set.intersection(*[{tm for tm, a, _ in v if a is not None} for v in results.values()])
    for label, rows in results.items():
        errs = [a - t for tm, a, t in rows if a is not None]
        common = [a - t for tm, a, t in rows if tm in both]
        def fmt(e):
            if not e:
                return "n=0"
            ab = sorted(abs(x) for x in e)
            return (f"n={len(e):2d} bias={statistics.mean(e):+5.2f} MAE={statistics.mean(ab):4.2f} "
                    f"p50={statistics.median(ab):4.2f}")
        print(f"{label:32s} all accepted: {fmt(errs)} | common set: {fmt(common)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
