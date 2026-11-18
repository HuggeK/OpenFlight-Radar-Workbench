#!/usr/bin/env python3
"""Write manifest_e1.json, manifest_e2.json and manifest_e3.json for a can
azimuth session: every can capture, each time against one empty scene.

Folders next to this script: e1 e2 e3 (empty hallway), b1 b2 b3 (can on
boresight), and one per mark named by its tape distance in mm along the line,
l = left and r = right of boresight seen from behind the radar: r122, l122, ...

    ~/openflight/.venv/bin/python build_manifest.py --line-m 1.40 --height-m 0.0525
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = re.compile(r"^([lr])(\d+)$")


def dumps(folder):
    files = sorted(folder.glob("*.l3dump"))
    if not files:
        sys.exit(f"{folder.name}/ has no .l3dump files: capture it or remove the folder")
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--line-m", type=float, required=True,
                        help="enclosure front to the tape line, along boresight (m)")
    parser.add_argument("--height-m", type=float, required=True,
                        help="height of the can's echo above the floor (m): the antenna height")
    parser.add_argument("--depth-m", type=float, default=0.027,
                        help="antenna face behind the enclosure front (m), measured 0.027")
    args = parser.parse_args()
    forward = round(args.line_m + args.depth_m, 4)

    captures = []
    for folder in sorted(p for p in HERE.iterdir() if p.is_dir()):
        if folder.name in ("b1", "b2", "b3"):
            lateral = 0.0
        else:
            match = MARK.match(folder.name)
            if not match:
                continue
            sign = 1 if match.group(1) == "r" else -1
            lateral = sign * int(match.group(2)) / 1000.0
        for path in dumps(folder):
            captures.append({
                "file": path.relative_to(HERE).as_posix(),
                "kind": "static",
                "lateral_m": lateral,
                "height_m": args.height_m,
                "forward_m": forward,
            })
    if len({c["lateral_m"] for c in captures}) < 3:
        sys.exit("need the can at 3 or more lateral positions before anything can be fitted")

    positions = len({Path(c["file"]).parent.name for c in captures})
    for empty_folder in ("e1", "e2", "e3"):
        files = dumps(HERE / empty_folder)
        empty = files[len(files) // 2].relative_to(HERE).as_posix()
        out = HERE / f"manifest_{empty_folder}.json"
        out.write_text(json.dumps({"empty": empty, "captures": captures}, indent=2) + "\n",
                       encoding="utf-8")
        print(f"{out.name}: {len(captures)} captures at {positions} positions, against {empty}")


if __name__ == "__main__":
    main()
