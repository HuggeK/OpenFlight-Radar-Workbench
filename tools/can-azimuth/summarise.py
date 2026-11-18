#!/usr/bin/env python3
"""Angle per mark from an azimuth_check report: taped against measured, the
spread over the repeats, the hottest RX channel, and the boresight drift
across b1, b2, b3.

    ~/openflight/.venv/bin/python summarise.py e2
"""
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from openflight.iwr6843.dump import parse_header

tag = sys.argv[1] if len(sys.argv) > 1 else "e2"
here = Path(__file__).resolve().parent
manifest = json.loads((here / f"manifest_{tag}.json").read_text(encoding="utf-8"))
report = json.loads((here / f"report_{tag}.json").read_text(encoding="utf-8"))

mark_of, taped, rx_temp = {}, {}, defaultdict(list)
for capture in manifest["captures"]:
    path = Path(capture["file"])
    mark_of[path.name] = path.parent.name
    taped[path.parent.name] = math.degrees(math.atan2(capture["lateral_m"], capture["forward_m"]))
    try:
        temps = parse_header((here / path).read_bytes()).get("temperature_report")
    except (OSError, ValueError):
        temps = None
    if temps:
        rx_temp[path.parent.name].append(max(temps[k] for k in ("rx0_c", "rx1_c", "rx2_c", "rx3_c")))

seen = defaultdict(list)
for static in report["static"]:
    x, y, _ = static["position_m"]  # golf frame: x downrange, y right
    seen[mark_of[static["file"]]].append(math.degrees(math.atan2(y, x)))

fit = report.get("fit")
if fit:
    print(f"[{tag}] offset {fit['azimuth_offset_rad']:+.4f} rad, slope {fit['slope']:.3f}, "
          f"median |lateral error| {100 * fit['median_abs_lateral_error_m']:.1f} cm")
else:
    print(f"[{tag}] no offset fitted")
print(f"{'mark':>6} {'taped':>7} {'seen':>7} {'error':>7} {'spread':>7} {'rx_C':>5}  n")
for mark in sorted(seen, key=lambda m: (taped[m], m)):
    angles = seen[mark]
    median = statistics.median(angles)
    spread = statistics.stdev(angles) if len(angles) > 1 else float("nan")
    temp = statistics.median(rx_temp[mark]) if rx_temp[mark] else float("nan")
    print(f"{mark:>6} {taped[mark]:7.2f} {median:7.2f} {median - taped[mark]:+7.2f} "
          f"{spread:7.2f} {temp:5.0f}  {len(angles)}")
