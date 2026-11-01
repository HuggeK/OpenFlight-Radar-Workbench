"""Build the studio-session report page (artifact, with videos) and its print twin (PDF, with strips)."""

from pathlib import Path
import html
import re

HERE = Path(__file__).parent
CLIPS = HERE.parent / "clips"
PHOTOS = HERE.parent / "workbench/docs/reports/studio-session-2026-11-01/photos"
OUT = Path(r"C:\projects\setup openflight\test 2026-11-01\report")

CLIP_ROWS = [
    # tag, title, verdict class, caption
    ("113250_331_002", "Real shot, captured on time", "ok",
     "11:32:50 · OpenFlight 120.5 mph, TrackMan 116.4 mph · IWR launch 23.3°, TrackMan 21.3°"),
    ("120320_492_043", "Real shot, OPS reading ×1.49", "warn",
     "12:03:20 · OpenFlight 192.0 mph, TrackMan 123.3 mph · inside the 11:37:53-12:34 period"),
    ("124939_385_004", "Real shot after the restart", "ok",
     "12:49:39 · SNR 3.0 · OpenFlight 122.2 mph, TrackMan 118.8 mph"),
    ("120052_698_037", "Trigger on the takeaway", "bad",
     "12:00:52 · fired 0.79 s before TrackMan's impact · saved as 20.4 mph, the real 114.8 mph shot was lost"),
    ("124819_921_003", "Real shot, trigger 70 ms early", "bad",
     "12:48:19 · both the OPS and the camera window closed before impact · TrackMan 121.9 mph, OpenFlight nothing"),
    ("121510_021_056", "Address", "bad",
     "12:15:10 · club resting behind the ball · saved as false shot #36, 20.3 mph from 3 readings"),
    ("120240_461_042", "Practice swing", "bad",
     "12:02:40 · ball never moves · saved as false shot #26, 22.5 mph from 1 reading"),
    ("124801_522_002", "Practice swing at SNR 3.0", "bad",
     "12:48:01 · saved as false shot #2, a 74.0 mph “ball” from 29 readings"),
    ("120443_832_046", "Walking up to the screen", "bad",
     "12:04:43 · saved as false shot #30, 27.0 mph from 4 readings"),
    ("125322_568_011", "Placing a ball", "bad",
     "12:53:22 · OPS saw no ball, so no shot, but the IWR was blind for 7.7 s"),
]

VERDICT_LABEL = {"ok": "Captured", "warn": "Wrong speed", "bad": "Lost or false"}


def clip_cards(mode: str) -> str:
    cards = []
    for tag, title, verdict, caption in CLIP_ROWS:
        if mode == "web":
            media = (
                f'<video src="clips/{tag}.mp4" poster="clips/{tag}.jpg" muted loop playsinline '
                f'preload="metadata" controls aria-label="{html.escape(title)}"></video>'
            )
        else:
            media = f'<img src="{(CLIPS / (tag + "_strip.jpg")).as_uri()}" alt="{html.escape(title)}">'
        cards.append(
            f'<figure class="clip {verdict}">{media}<figcaption>'
            f'<span class="chip {verdict}">{VERDICT_LABEL[verdict]}</span>'
            f"<strong>{html.escape(title)}</strong><span>{html.escape(caption)}</span>"
            "</figcaption></figure>"
        )
    return "\n".join(cards)


CATEGORY_CLASS = {
    "real shot, captured": "ok",
    "real shot, speed x1.49": "warn",
    "real shot, wrong OPS speed": "warn",
    "early trigger, real shot lost": "bad",
    "real shot, OPS saw no ball": "bad",
    "false shot": "bad",
    "no-ball trigger": "bad",
}


def load_captures() -> list[dict]:
    import json

    return json.loads((HERE / "captures.json").read_text(encoding="utf-8"))


def _seconds(clock: str) -> float:
    h, m, s = clock.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def j3_chart(captures: list[dict]) -> str:
    """SVG: OPS capture window per trigger against time of day, with the 30 and 20 kS/s lines."""
    pts = [(_seconds(c["time"]), c["window_ms"], CATEGORY_CLASS[c["category"]])
           for c in captures if c["window_ms"] is not None]
    x0, x1 = _seconds("11:15:00"), _seconds("13:00:00")
    y0, y1 = 24.0, 56.0
    W, H, L, R, T, B = 900, 300, 56, 16, 16, 40
    X = lambda t: L + (t - x0) / (x1 - x0) * (W - L - R)  # noqa: E731
    Y = lambda v: T + (y1 - v) / (y1 - y0) * (H - T - B)  # noqa: E731
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="OPS capture window per trigger" class="chart">']
    for v in (25, 30, 35, 40, 45, 50, 55):
        parts.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>'
                     f'<text x="{L-8}" y="{Y(v)+4:.1f}" class="tick" text-anchor="end">{v}</text>')
    for hhmm in ("11:15", "11:30", "11:45", "12:00", "12:15", "12:30", "12:45", "13:00"):
        x = X(_seconds(hhmm + ":00"))
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T}" y2="{H-B}" class="grid"/>'
                     f'<text x="{x:.1f}" y="{H-B+18}" class="tick" text-anchor="middle">{hhmm}</text>')
    for v, label in ((34.13, "S#24 at 30 kS/s: 34.1 ms"), (51.2, "S#24 at 20 kS/s: 51.2 ms")):
        parts.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="ref"/>'
                     f'<text x="{W-R-4}" y="{Y(v)-6:.1f}" class="reflabel" text-anchor="end">{label}</text>')
    for event, label in (("11:37:53", "11:37:53 OPS at 20 kS/s"), ("12:35:14", "12:35 restart")):
        x = X(_seconds(event))
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T}" y2="{H-B}" class="event"/>'
                     f'<text x="{x+5:.1f}" y="{T+12}" class="reflabel">{label}</text>')
    for t, v, cls in pts:
        parts.append(f'<circle cx="{X(t):.1f}" cy="{Y(v):.1f}" r="3.6" class="dot {cls}"/>')
    parts.append(f'<text x="14" y="{(T+H-B)/2:.0f}" class="tick" transform="rotate(-90 14 {(T+H-B)/2:.0f})" '
                 'text-anchor="middle">J3 window, ms</text></svg>')
    return "".join(parts)


def capture_rows(captures: list[dict]) -> str:
    rows = []
    for c in captures:
        cls = CATEGORY_CLASS[c["category"]]
        ops = f"#{c['shot']} {c['ball']}/{c['club'] or '–'}" if c["shot"] else f"no ball ({c['readings']})"
        tm = f"#{c['tm']} {c['tm_ball']}/{c['tm_club']}" if c["tm"] else "–"
        rows.append(
            f'<tr data-cat="{cls}" data-tag="{c["tag"]}" tabindex="0">'
            f'<td class="num">{c["time"][:8]}</td><td class="num r">{c["snr"]}</td>'
            f'<td><span class="chip {cls}">{html.escape(c["category"])}</span></td>'
            f'<td class="num">{ops}</td><td class="num">{tm}</td>'
            f'<td class="num r">{"" if c["window_ms"] is None else c["window_ms"]}</td></tr>'
        )
    return "\n".join(rows)


def build(mode: str) -> str:
    page = (HERE / "report.template.html").read_text(encoding="utf-8")
    captures = load_captures()
    page = page.replace("{{CLIPS}}", clip_cards(mode))
    page = page.replace("{{J3_CHART}}", j3_chart(captures))
    page = page.replace("{{CAPTURE_ROWS}}", capture_rows(captures))
    page = page.replace("{{J3_LOG}}", html.escape((HERE / "ops_j3_20261101_111438.log").read_text()))
    page = page.replace("{{PHOTO_BASE}}", "photos/" if mode == "web" else PHOTOS.as_uri() + "/")
    if mode == "web":
        page = re.sub(r"<!--PRINT-ONLY-->.*?<!--/PRINT-ONLY-->", "", page, flags=re.S)
        page = page.replace("{{CLIP_NOTE}}",
                            "Each clip is 91 frames at 431 fps, slowed about 29×. Burned in: time from "
                            "the IWR trigger, a red bar from the trigger frame (S! sent), a yellow bar "
                            "while the OPS captures (J3 pin 1 high), and the outcome.")
    else:
        page = re.sub(r"<!--WEB-ONLY-->.*?<!--/WEB-ONLY-->", "", page, flags=re.S)
        page = page.replace("{{CLIP_NOTE}}",
                            "Each strip shows four frames: 89 ms and 22 ms before the trigger, "
                            "the trigger frame, and 44 ms after.")
        page = page.replace("</style>", "@page{size:A4;margin:14mm 13mm}</style>", 1)
        page = "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">" + page + "</body></html>"
    return page


if __name__ == "__main__":
    import shutil

    (OUT / "clips").mkdir(parents=True, exist_ok=True)
    (OUT / "photos").mkdir(exist_ok=True)
    for tag, *_ in CLIP_ROWS:
        # The annotated version from captures/ replaces the plain clip; the poster stays.
        shutil.copy2(OUT / "captures" / (tag + ".mp4"), OUT / "clips" / (tag + ".mp4"))
        shutil.copy2(CLIPS / (tag + ".jpg"), OUT / "clips" / (tag + ".jpg"))
    for c in load_captures():
        assert (OUT / "captures" / f"{c['tag']}.mp4").exists(), c["tag"]
    for name in ("IMG_2821.webp", "IMG_2823.webp"):
        shutil.copy2(PHOTOS / name, OUT / "photos" / name)
    (OUT / "studio-report.html").write_text(build("web"), encoding="utf-8")
    (HERE / "studio-report.print.html").write_text(build("print"), encoding="utf-8")
    print("built", OUT)
