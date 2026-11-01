#!/usr/bin/env python3
"""Write one CSV row per OpenFlight camera capture: its trigger timestamps.

Feeds ``python -m openflight_bench.session latency --camera`` without copying
the clips themselves (~6 MB each).

    python3 session_tools/export_camera_triggers.py \\
        ~/openflight_sessions/studio/camera --day 20261101 > camera_triggers.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("camera_dir", type=Path, help="folder holding camera_*/metadata.json")
    parser.add_argument("--day", default="", help="only captures named camera_<day>_*")
    parser.add_argument("--until", type=float, help="skip triggers after this epoch second")
    args = parser.parse_args()

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(
        ["capture", "sequence", "trigger_epoch_s", "trigger_monotonic_ns", "frames", "fps", "gaps"]
    )
    for meta in sorted(args.camera_dir.glob(f"camera_{args.day}*/metadata.json")):
        data = json.loads(meta.read_text())
        if args.until is not None and data["trigger_timestamp"] > args.until:
            continue
        writer.writerow(
            [
                meta.parent.name,
                data["sequence"],
                f"{data['trigger_timestamp']:.6f}",
                data["trigger_host_timestamp_ns"],
                data["frame_count"],
                f"{data['delivered_fps']:.1f}",
                data["gap_count"],
            ]
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
