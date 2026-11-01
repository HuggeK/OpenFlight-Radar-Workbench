#!/usr/bin/env python3
"""Save a strip of frames around the trigger of OpenFlight camera captures.

The quickest way to tell a real shot from a false trigger: a real one shows
the club through the ball and the ball gone; an address, waggle, backswing or
walk-by shows the ball still on the mat.

    ~/openflight/.venv/bin/python session_tools/camera_strip.py \\
        ~/openflight_sessions/studio/camera/camera_20261101_124819_921_003 -o /tmp/strip.png
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
from PIL import Image


def strip(capture: Path, offsets: list[int]) -> np.ndarray:
    archive = np.load(capture / "frames.npz")
    frames = archive["frames"]
    trigger = int(archive["pre_trigger_count"])
    picks = [min(max(trigger + o, 0), len(frames) - 1) for o in offsets]
    return np.concatenate([frames[i] for i in picks], axis=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("captures", nargs="+", type=Path, help="camera_* folders")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument(
        "--offsets", type=int, nargs="+", default=[-60, -20, 0, 20],
        help="frames relative to the trigger frame (450 fps: 20 frames = 44 ms)",
    )
    args = parser.parse_args()
    rows = [strip(capture, args.offsets) for capture in args.captures]
    Image.fromarray(np.concatenate(rows, axis=0)).save(args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
