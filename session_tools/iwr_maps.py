"""Range-time maps of every IWR6843 capture from the 2026-11-01 studio session.

Moving-target power (OpenFlight's own MTI) summed over chirps, TX and RX, per
frame and range bin, drawn at each frame's real range window. Run with the
OpenFlight source on PYTHONPATH:

    PYTHONPATH=<openflight>/src python iwr_maps.py DUMP_DIR CAPTURES_JSON OUT_DIR
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from openflight.iwr6843.shot import prepare_shot_dump  # noqa: E402

TEE_M = 1.57 + 0.030  # enclosure face to ball, plus the array depth
NET_M = 5.30 + 0.030


def draw(dump: Path, label: str, out: Path) -> None:
    prep = prepare_shot_dump(dump.read_bytes())
    geo = prep.geometry
    mti = prep.mti()
    power = (np.abs(mti) ** 2).sum(axis=(1, 2, 3))  # frames x range bins
    db = 10 * np.log10(power + 1e-12)
    vmax = np.percentile(db, 99.5)
    vmin = vmax - 35
    fig, ax = plt.subplots(figsize=(6.4, 3.0), dpi=100)
    times = np.array(geo.frame_time_offsets_s) * 1000
    width = geo.frame_period_s * 1000
    mesh = None
    for f, start in enumerate(geo.range_bin_starts):
        ranges = (start + np.arange(geo.range_bin_counts[f] + 1) - 0.5) * geo.range_res_m
        mesh = ax.pcolormesh([times[f], times[f] + width], ranges, db[f][:, None],
                             vmin=vmin, vmax=vmax, cmap="magma", shading="flat")
    ax.axhline(TEE_M, color="#5fd1d9", lw=1, ls="--")
    ax.axhline(NET_M, color="#9ad36a", lw=1, ls="--")
    ax.text(times[-1] + width, TEE_M, " ball", color="#5fd1d9", va="center", fontsize=8)
    ax.text(times[-1] + width, NET_M, " net", color="#9ad36a", va="center", fontsize=8)
    ax.set_xlim(times[0], times[-1] + width)
    ax.set_ylim(0.8, 5.6)
    ax.set_xlabel("ms after the IWR trigger")
    ax.set_ylabel("range from antennas, m")
    ax.set_title(label, fontsize=9, loc="left")
    fig.colorbar(mesh, ax=ax, pad=0.08, label="MTI power, dB")
    fig.tight_layout()
    fig.savefig(out, format="png")
    plt.close(fig)


def main() -> int:
    dump_dir, captures_json, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)
    captures = {c["tag"]: c for c in json.loads(captures_json.read_text(encoding="utf-8"))}
    done = 0
    for dump in sorted(dump_dir.glob("iwr6843_20261101_*.l3dump")):
        tag = dump.stem.split("_", 2)[2]
        c = captures.get(tag)
        label = (f"{c['time'][:8]}  {c['category']}  ·  OPS "
                 f"{(str(c['ball']) + ' mph') if c['shot'] else 'no ball'}"
                 f"  ·  TrackMan {(str(c['tm_ball']) + ' mph, ' + str(c['tm_launch']) + '°') if c['tm'] else '-'}"
                 if c else dump.stem)
        try:
            draw(dump, label, out_dir / f"{tag}.png")
            done += 1
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print("skip", dump.name, type(exc).__name__, exc)
    print(done, "maps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
