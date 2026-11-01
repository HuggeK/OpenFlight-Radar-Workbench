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
from .latency import LatencyWindow, describe, load_camera_triggers, match_triggers, summarize
from .logs import MAX_SMASH, parse_kiosk_log
from .trackman import find_offset, load_swingsync_csv, match_shots


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


def compare(args) -> int:
    triggers = [t for path in args.logs for t in parse_kiosk_log(path).triggers]
    shots = load_swingsync_csv(args.trackman)
    utc_offset_s = args.utc_offset_h * 3600
    if args.offset is None:
        offset_s, hits = find_offset(shots, triggers, utc_offset_s=utc_offset_s)
        print(f"clock offset TrackMan - OpenFlight: {offset_s:+.1f} s ({hits} of {len(shots)} shots)")
    else:
        offset_s = args.offset
    matches = match_shots(shots, triggers, offset_s=offset_s, utc_offset_s=utc_offset_s)

    if args.shots:
        print(
            "  TM#  OF time       dt_s  verdict   OF#   TM ball  OF ball  ratio"
            "   TM club  OF club  ratio   TM launch  OF launch"
        )
    ball_ratio, club_ratio, launch_diff = [], [], []
    missed = []
    for m in matches:
        t = m.trigger
        shot = t.shot if t else None
        tm = m.trackman
        rb = shot.ball_mph / tm.ball_mph if shot and tm.ball_mph else None
        rc = shot.club_mph / tm.club_mph if shot and shot.club_mph and tm.club_mph else None
        dl = t.launch_deg - tm.launch_deg if t and t.launch_deg is not None and tm.launch_deg else None
        if rb is not None:
            ball_ratio.append((tm.ball_mph, rb))
        if rc is not None:
            club_ratio.append(rc)
        if dl is not None:
            launch_diff.append(dl)
        if shot is None:
            missed.append(m)
        if args.shots:
            print(
                f"  {tm.number:>3}  {t.time:%H:%M:%S}" if t else f"  {tm.number:>3}  {'-':>8}",
                end="",
            )
            print(
                f"  {_fmt(m.delta_s, '6.2f')}  {(t.verdict if t else 'no trigger'):9s}"
                f" {('#' + str(shot.number)) if shot else '-':>4}"
                f"  {_fmt(tm.ball_mph, '7.1f')}  {_fmt(shot.ball_mph if shot else None, '7.1f')}"
                f"  {_fmt(rb, '5.2f')}"
                f"   {_fmt(tm.club_mph, '7.1f')}  {_fmt(shot.club_mph if shot else None, '7.1f')}"
                f"  {_fmt(rc, '5.2f')}"
                f"   {_fmt(tm.launch_deg, '9.1f')}  {_fmt(t.launch_deg if t else None, '9.1f')}"
            )

    print(f"TrackMan shots: {len(shots)}; with an OpenFlight shot: {len(ball_ratio)}; "
          f"with a trigger but no shot: {sum(1 for m in missed if m.trigger)}; "
          f"no trigger: {sum(1 for m in missed if not m.trigger)}")
    for label, lo, hi in (("ball < 150 mph", 0, 150), ("ball >= 150 mph", 150, 1e9)):
        values = [r for b, r in ball_ratio if lo <= b < hi]
        s = describe(values)
        print(f"  OF/TM ball speed, {label:16s} n={s['n']:<3} mean={_fmt(s['mean'], '.3f')}"
              f" stdev={_fmt(s['stdev'], '.3f')} min={_fmt(s['min'], '.2f')} max={_fmt(s['max'], '.2f')}")
    s = describe(club_ratio)
    print(f"  OF/TM club speed{'':18s} n={s['n']:<3} mean={_fmt(s['mean'], '.3f')}"
          f" stdev={_fmt(s['stdev'], '.3f')} min={_fmt(s['min'], '.2f')} max={_fmt(s['max'], '.2f')}")
    s = describe(launch_diff)
    print(f"  IWR LCMF - TM launch (deg){'':8s} n={s['n']:<3} mean={_fmt(s['mean'], '+.1f')}"
          f" stdev={_fmt(s['stdev'], '.1f')} min={_fmt(s['min'], '+.1f')} max={_fmt(s['max'], '+.1f')}")
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

    p_compare = sub.add_parser("compare", help="match TrackMan shots (SwingSync CSV) to OpenFlight")
    p_compare.add_argument("trackman", help="SwingSync TrackMan session export (CSV)")
    p_compare.add_argument("logs", nargs="+", help="kiosk logs from the same session")
    p_compare.add_argument("--utc-offset-h", type=float, default=1.0,
                           help="the logs' local offset from UTC (default: 1, CET)")
    p_compare.add_argument("--offset", type=float,
                           help="TrackMan minus OpenFlight clock, s (default: search +/-15 min)")
    p_compare.add_argument("--shots", action="store_true", help="also list every TrackMan shot")
    p_compare.set_defaults(func=compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
