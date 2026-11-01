#!/usr/bin/env python3
"""Re-run OpenFlight's IWR ball tracker on saved dumps with other net distances.

Answers "did --iwr6843-net-m clip the ball track?" without another session.
Run with OpenFlight's own interpreter on the Pi:

    ~/openflight/.venv/bin/python session_tools/iwr_net_replay.py \\
        ~/openflight_sessions/iwr6843/iwr6843_20261101_*.l3dump --net 3.0 4.6 none

On 2026-11-01 a 3.0 m net (meant as ball -> net, entered as unit -> net)
clipped every track at 2.75 m: the tracker searches from 2.25 m, so ~10 ms of
flight was left and LCMF rejected it. At 4.6 m the same dumps tracked 24-41 ms.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    from openflight.iwr6843.calibration import Calibration
    from openflight.iwr6843.shot import process_dump
except ImportError:
    sys.exit("run this with OpenFlight's interpreter: ~/openflight/.venv/bin/python")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dumps", nargs="+", type=Path)
    parser.add_argument("--net", nargs="+", default=["none"], help="net ranges in m, or none")
    args = parser.parse_args()
    nets = [None if n.lower() == "none" else float(n) for n in args.net]

    cal = Calibration.load()
    for dump in sorted(args.dumps):
        raw = dump.read_bytes()
        cells = [dump.stem]
        for net in nets:
            label = f"net={net if net is not None else 'none'}"
            try:
                shot = process_dump(raw, cal, net_range_m=net)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                cells.append(f"{label}: ERROR {type(exc).__name__}")
                continue
            track = shot.track
            if track is None:
                cells.append(f"{label}: no ball")
            else:
                span_ms = 1000 * (track.t_last - track.t_first)
                cells.append(
                    f"{label}: {shot.quality or 'ok'} span={span_ms:.0f}ms "
                    f"n={track.n_inliers} rms={track.rms_bins:.2f}"
                )
        print(" | ".join(cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())
