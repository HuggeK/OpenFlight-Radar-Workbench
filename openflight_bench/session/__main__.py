"""Command line for the field-session tools.

    python -m openflight_bench.session triage LOG [LOG ...] [--triggers]
    python -m openflight_bench.session latency --camera CSV --gpio LOG \\
        --window NAME START END [--window ...]
"""

from __future__ import annotations

import argparse
from datetime import datetime
import re
import sys

from .gpio import load_edges
from .latency import LatencyWindow, load_camera_triggers, match_triggers, summarize
from .logs import MAX_SMASH, parse_kiosk_log


def _fmt(value, spec: str = ".2f") -> str:
    """``format(value, spec)``, or a dash padded to the spec's width."""
    if value is None:
        width = re.match(r"\d*", spec).group()
        return "-".rjust(int(width) if width else 1)
    return format(value, spec)


def triage(args) -> int:
    for path in args.logs:
        session = parse_kiosk_log(path)
        summary = session.summary()
        print(f"== {summary.pop('log')}")
        for key, value in summary.items():
            print(f"  {key:30s} {_fmt(value, '.2f') if isinstance(value, float) else value}")
        if args.triggers:
            print(
                "  seq  time          since_rearm  verdict    peak  rd  shot   ball   club  smash"
                "    launch / withheld         impact->S!  blind"
            )
            for t in session.triggers:
                shot = t.shot
                smash = shot.smash if shot else None
                flag = " !" if smash is not None and smash > MAX_SMASH else "  "
                launch = (
                    f"{t.launch_deg:.1f} deg" if t.launch_deg is not None else t.launch_status or "-"
                )
                print(
                    f"  {t.sequence:>3}  {t.time:%H:%M:%S}.{t.time.microsecond // 1000:03d}"
                    f"  {_fmt(t.since_rearm_s, '11.2f')}  {t.verdict or '-':9s}"
                    f"  {_fmt(t.peak_mph, '5.1f')} {_fmt(t.readings, '3d')}"
                    f"  {('#' + str(shot.number)) if shot else '-':>4}"
                    f"  {_fmt(shot.ball_mph if shot else None, '5.1f')}"
                    f"  {_fmt(shot.club_mph if shot else None, '5.1f')}"
                    f"  {_fmt(smash, '5.2f')}{flag}"
                    f"  {launch:26s}"
                    f"  {_fmt(t.impact_to_s_ms, '8.1f')}"
                    f"  {_fmt(t.blind_s, '5.1f')}"
                    + (f"  ERROR {t.capture_error}" if t.capture_error else "")
                )
    return 0


def latency(args) -> int:
    rows = match_triggers(load_camera_triggers(args.camera), load_edges(args.gpio))
    windows = [
        LatencyWindow(name, datetime.fromisoformat(start), datetime.fromisoformat(end))
        for name, start, end in args.window
    ]
    for name, result in summarize(rows, windows).items():
        print(f"== {name}: {result['triggers']} triggers")
        for column, label in (("rise_ms", "S! -> OPS (J3 rise)"), ("window_ms", "J3 rise -> fall")):
            s = result[column]
            print(
                f"  {label:22s} n={s['n']:<3} mean={_fmt(s['mean'])} stdev={_fmt(s['stdev'])}"
                f" min={_fmt(s['min'])} max={_fmt(s['max'])} p95={_fmt(s['p95'])} ms"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m openflight_bench.session")
    sub = parser.add_subparsers(dest="command", required=True)

    p_triage = sub.add_parser("triage", help="summarize self-triggers and shots in kiosk logs")
    p_triage.add_argument("logs", nargs="+")
    p_triage.add_argument("--triggers", action="store_true", help="also list every trigger")
    p_triage.set_defaults(func=triage)

    p_latency = sub.add_parser("latency", help="S! latency and OPS window jitter per window")
    p_latency.add_argument("--camera", required=True, help="camera trigger CSV")
    p_latency.add_argument("--gpio", required=True, help="gpiomon J3 edge log")
    p_latency.add_argument(
        "--window", nargs=3, action="append", required=True, metavar=("NAME", "START", "END"),
        help="ISO 8601 times with UTC offset, e.g. 2026-11-01T11:32:21+01:00",
    )
    p_latency.set_defaults(func=latency)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
