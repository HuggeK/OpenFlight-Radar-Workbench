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


def build(mode: str) -> str:
    page = (HERE / "report.template.html").read_text(encoding="utf-8")
    page = page.replace("{{CLIPS}}", clip_cards(mode))
    page = page.replace("{{PHOTO_BASE}}", "photos/" if mode == "web" else PHOTOS.as_uri() + "/")
    if mode == "web":
        page = re.sub(r"<!--PRINT-ONLY-->.*?<!--/PRINT-ONLY-->", "", page, flags=re.S)
        page = page.replace("{{CLIP_NOTE}}",
                            "Each clip is 91 frames at 431 fps, slowed about 15×. "
                            "The red bar appears at the trigger frame (150 ms in).")
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
        for suffix in (".mp4", ".jpg"):
            shutil.copy2(CLIPS / (tag + suffix), OUT / "clips" / (tag + suffix))
    for name in ("IMG_2821.webp", "IMG_2823.webp"):
        shutil.copy2(PHOTOS / name, OUT / "photos" / name)
    (OUT / "studio-report.html").write_text(build("web"), encoding="utf-8")
    (HERE / "studio-report.print.html").write_text(build("print"), encoding="utf-8")
    print("built", OUT)
