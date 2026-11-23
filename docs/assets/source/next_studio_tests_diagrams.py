"""Generate the SVG diagrams in docs/NEXT_STUDIO_TESTS.md.

    python3 docs/assets/source/next_studio_tests_diagrams.py docs/assets
"""
import sys
from pathlib import Path
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
SEG = 128 / 30000 * 1000  # 4.267 ms
TRIG = 8.0               # ms after impact
INK, MUTED, GRID = "#1f2328", "#59636e", "#d0d7de"
CLUB, BALL, CAM = "#8250df", "#1a7f37", "#0969da"
FONT = 'font-family="Helvetica, Arial, sans-serif"'

def text(x, y, s, size=13, fill=INK, anchor="start", weight="normal", extra=""):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" {extra}>{s}</text>'

# ---------- 1. buffer split timeline ----------
W, H = 860, 400
L, R = 170, 830
t0, t1 = -160.0, 115.0
X = lambda t: L + (t - t0) / (t1 - t0) * (R - L)
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" {FONT}>',
     f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
     text(20, 30, "What each recorder keeps around one shot (30 kS/s, trigger ~8 ms after impact)", 16, weight="bold")]
for t in range(-150, 111, 25):
    o.append(f'<line x1="{X(t):.1f}" y1="55" x2="{X(t):.1f}" y2="330" stroke="{GRID}" stroke-width="1"/>')
    o.append(text(X(t), 348, f"{t:+d}" if t else "0", 11, MUTED, "middle"))
o.append(text((L + R) / 2, 368, "ms from impact", 12, MUTED, "middle"))
rows = []
for s, label in ((24, "OPS S#24 (branch default)"), (16, "OPS S#16"), (10, "OPS S#10 (next session)")):
    rows.append((label, TRIG - s * SEG, TRIG + (32 - s) * SEG, s == 10))
y = 70
for label, a, b, bold in rows:
    o.append(text(L - 10, y + 17, label, 13, INK, "end", "bold" if bold else "normal"))
    o.append(f'<rect x="{X(a):.1f}" y="{y}" width="{X(0)-X(a):.1f}" height="24" fill="{CLUB}" opacity="0.85"/>')
    o.append(f'<rect x="{X(0):.1f}" y="{y}" width="{X(b)-X(0):.1f}" height="24" fill="{BALL}" opacity="0.85"/>')
    o.append(text((X(a) + X(0)) / 2, y + 17, f"club {-a:.0f} ms", 12, "#ffffff", "middle", "bold"))
    o.append(text((X(0) + X(b)) / 2, y + 17, f"ball {b:.0f} ms", 12, "#ffffff", "middle", "bold"))
    y += 44
# camera
o.append(text(L - 10, y + 17, "Camera 150 / 50 ms", 13, INK, "end"))
o.append(f'<rect x="{X(TRIG-150):.1f}" y="{y}" width="{X(TRIG+50)-X(TRIG-150):.1f}" height="24" fill="{CAM}" opacity="0.85"/>')
o.append(text((X(TRIG - 150) + X(0)) / 2, y + 17, "camera clip (2026-11-01 settings)", 12, "#ffffff", "middle", "bold"))
y += 44
o.append(text(L - 10, y + 17, "Camera 150 / 100 ms", 13, INK, "end", "bold"))
o.append(f'<rect x="{X(TRIG-150):.1f}" y="{y}" width="{X(TRIG+50)-X(TRIG-150):.1f}" height="24" fill="{CAM}" opacity="0.85"/>')
o.append(f'<rect x="{X(TRIG+50):.1f}" y="{y}" width="{X(TRIG+100)-X(TRIG+50):.1f}" height="24" fill="{CAM}" opacity="0.45" stroke="{CAM}" stroke-dasharray="4 3"/>')
o.append(text(X(TRIG + 75), y + 17, "+50 ms", 12, INK, "middle", "bold"))
o.append(text((X(TRIG - 150) + X(0)) / 2, y + 17, "proposed: early triggers still show impact", 12, "#ffffff", "middle", "bold"))
# impact / trigger lines
o.append(f'<line x1="{X(0):.1f}" y1="55" x2="{X(0):.1f}" y2="330" stroke="{INK}" stroke-width="2"/>')
o.append(text(X(0) - 4, 52, "impact", 12, INK, "end", "bold"))
o.append(f'<line x1="{X(TRIG):.1f}" y1="55" x2="{X(TRIG):.1f}" y2="330" stroke="#cf222e" stroke-width="2" stroke-dasharray="5 3"/>')
o.append(text(X(TRIG) + 4, 52, "trigger (S!, camera freeze)", 12, "#cf222e", "start", "bold"))
# net arrival marks
for t, lab in ((43, "driver hits net"), (86, "wedge hits net")):
    o.append(f'<path d="M{X(t):.1f} 316 l-5 10 h10 z" fill="{MUTED}"/>')
    o.append(text(X(t), 312, lab, 10, MUTED, "middle"))
o.append(text(20, 390, "OPS: 32 segments of 4.27 ms, S#n of them before the trigger. Camera: 320×200 at 450 fps. Net 5.3 m from the unit.", 11, MUTED))
o.append("</svg>")
(OUT / "ops-buffer-split.svg").write_text("\n".join(o) + "\n")

# ---------- 2. placement top view ----------
W, H = 830, 560
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" {FONT}>',
     f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
     text(20, 30, "Studio, seen from above (not to scale)", 16, weight="bold")]
# room
o.append(f'<rect x="60" y="70" width="560" height="430" fill="#f6f8fa" stroke="{INK}" stroke-width="2"/>')
# net
o.append(f'<line x1="70" y1="90" x2="610" y2="90" stroke="{MUTED}" stroke-width="6" stroke-dasharray="2 4"/>')
o.append(text(340, 82, "net / screen (5.3 m from the unit)", 12, MUTED, "middle"))
# TrackMan hit zone (ball + club data)
o.append(f'<rect x="170" y="235" width="270" height="140" fill="#fff1e5" stroke="#bc4c00" stroke-dasharray="5 4"/>')
o.append(text(432, 253, "TrackMan hit zone:", 12, "#bc4c00", "end"))
o.append(text(432, 269, "ball + club data", 12, "#bc4c00", "end"))
# back wall with the TrackMan alcove
o.append(f'<rect x="275" y="490" width="120" height="30" fill="#ffffff" stroke="{INK}" stroke-width="2"/>')
o.append(f'<rect x="290" y="478" width="90" height="22" fill="#fb8f44" stroke="#bc4c00"/>')
o.append(text(335, 493, "TrackMan", 11, "#ffffff", "middle", "bold"))
o.append(text(335, 540, "wall alcove", 11, MUTED, "middle"))
o.append(text(540, 540, "back wall", 11, MUTED, "middle"))

def unit(x, y, lab):
    o.append(f'<rect x="{x-18}" y="{y-12}" width="36" height="24" rx="3" fill="{INK}"/>')
    o.append(text(x, y + 5, lab, 12, "#ffffff", "middle", "bold"))

def ball_and_line(bx, by, ux, uy, name, col):
    o.append(f'<line x1="{ux}" y1="{uy-12}" x2="{bx}" y2="100" stroke="{col}" stroke-width="2" stroke-dasharray="7 5"/>')
    o.append(f'<path d="M{bx} 100 l-6 12 h12 z" fill="{col}"/>')
    o.append(f'<circle cx="{bx}" cy="{by}" r="7" fill="#ffffff" stroke="{INK}" stroke-width="1.5"/>')
    o.append(f'<line x1="{ux-30}" y1="{uy}" x2="{bx-30}" y2="{by}" stroke="{MUTED}" stroke-width="1"/>')
    for yy in (uy, by):
        o.append(f'<line x1="{ux-35}" y1="{yy}" x2="{ux-25}" y2="{yy}" stroke="{MUTED}" stroke-width="1"/>')
    o.append(text(ux - 38, (uy + by) / 2 + 4, "~1.6 m", 11, MUTED, "end"))
    o.append(text(bx + 12, by + 4, f"ball {name}", 12, INK, "start", "bold"))

# L: unit entirely to the left of the TrackMan alcove, ball inside its hit zone
ball_and_line(235, 300, 235, 462, "L", "#bc4c00")
unit(235, 462, "L")
# R: open right side, ball outside the hit zone
ball_and_line(530, 300, 530, 462, "R", "#0969da")
unit(530, 462, "R")
o.append(text(385, 150, "target line = alignment stick,", 12, INK, "middle"))
o.append(text(385, 166, "the same target TrackMan uses", 12, INK, "middle"))
# legend
lx = 635
o.append(text(lx, 110, "L", 13, "#bc4c00", weight="bold"))
for i, s in enumerate(("left of TrackMan's alcove,", "ball in its hit zone", "TrackMan: ball + club", "→ Test 1, club path", "2026-11-01: 2.00° MAE,", "5 of 13 tracks wrong", "try 30-50 cm further left", "if the ball stays in the zone")):
    o.append(text(lx, 128 + 16 * i, s, 11, INK))
o.append(text(lx, 285, "R", 13, "#0969da", weight="bold"))
for i, s in enumerate(("open right side,", "ball outside the hit zone", "TrackMan: ball only", "→ Block 0, tuning,", "IWR launch, OPS", "2026-11-01: 0.90° MAE,", "1 of 10 tracks wrong")):
    o.append(text(lx, 303 + 16 * i, s, 11, INK))
o.append(text(lx, 435, "1 cm off the line", 11, MUTED))
o.append(text(lx, 451, "≈ 0.36° launch bias", 11, MUTED))
o.append(text(lx, 467, "at 1.6 m", 11, MUTED))
o.append(text(340, 62, "downrange ↑", 12, MUTED, "middle"))
o.append("</svg>")
(OUT / "studio-placement.svg").write_text("\n".join(o) + "\n")

# ---------- 3. can re-measure, top view ----------
W, H = 860, 650
SX, SY = 560.0, 300.0           # px per metre sideways / forward (stretched sideways)
CX, Y0 = 430.0, 545.0           # 0 mark x; enclosure front y
LINE = 1.285
YL = Y0 - LINE * SY
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" {FONT}>',
     f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
     text(20, 30, "Can re-measure: what changes from the 2026-11-18 trial", 16, weight="bold"),
     text(20, 50, "Top view, sideways stretched about 2x. Same line distance (1.285 m) and marks.", 12, MUTED)]
# unit
o.append(f'<rect x="{CX-60}" y="{Y0}" width="120" height="34" rx="4" fill="{INK}"/>')
o.append(text(CX, Y0 + 22, "OpenFlight", 12, "#ffffff", "middle", "bold"))
o.append(f'<circle cx="{CX}" cy="{Y0}" r="4" fill="#cf222e"/>')
# boresight laser
o.append(f'<line x1="{CX}" y1="{Y0}" x2="{CX}" y2="{YL-40}" stroke="#cf222e" stroke-width="2"/>')
o.append(text(CX - 10, Y0 - 44, "1  laser / chalk line", 12, "#cf222e", "end", "bold"))
o.append(text(CX - 10, Y0 - 29, "from the antenna centre", 11, "#cf222e", "end"))
o.append(text(CX - 10, Y0 - 14, "(trial: floor crease)", 11, MUTED, "end"))
# check tapes from +-30 cm on the front face
for sgn in (-1, 1):
    x0 = CX + sgn * 0.30 * SX
    o.append(f'<line x1="{x0}" y1="{Y0}" x2="{CX}" y2="{YL}" stroke="#bf8700" stroke-width="1.5" stroke-dasharray="6 4"/>')
    o.append(f'<circle cx="{x0}" cy="{Y0}" r="3.5" fill="#bf8700"/>')
o.append(text(CX - 0.30 * SX, Y0 + 18, "-30 cm", 11, "#bf8700", "middle"))
o.append(text(CX + 0.30 * SX, Y0 + 18, "+30 cm", 11, "#bf8700", "middle"))
o.append(text(CX - 0.30 * SX - 10, Y0 - 60, "3  left / right check:", 12, "#bf8700", "end", "bold"))
o.append(text(CX - 0.30 * SX - 10, Y0 - 45, "both tapes read the same;", 11, "#bf8700", "end"))
o.append(text(CX - 0.30 * SX - 10, Y0 - 30, "0-mark error ≈ 2.2 × difference", 11, "#bf8700", "end"))
# tape line
o.append(f'<line x1="{CX-0.56*SX}" y1="{YL}" x2="{CX+0.56*SX}" y2="{YL}" stroke="{INK}" stroke-width="3"/>')
o.append(text(CX - 0.56 * SX, YL - 8, "tape line, 1.285 m from the enclosure front", 11, MUTED))
# 3-4-5 triangle at the 0 mark (30 / 40 / 50 cm)
tx, ty = CX + 0.40 * SX * 0.6, YL      # 40 cm sideways (drawn shorter sideways)
by_ = YL + 0.30 * SY
o.append(f'<path d="M{CX} {by_} L{tx} {YL}" stroke="{CAM}" stroke-width="1.5" fill="none" stroke-dasharray="3 3"/>')
o.append(f'<path d="M{CX+10} {YL} v10 h-10" stroke="{CAM}" fill="none"/>')
o.append(text(tx + 6, YL + 40, "2  square the tape: 30 cm along the", 12, CAM, weight="bold"))
o.append(text(tx + 6, YL + 55, "laser, 40 cm along the tape, 50 cm across", 11, CAM))
o.append(text(tx + 6, YL + 70, "(3-4-5); tape zero pinned ON the 0 cross", 11, CAM))
# marks
for mm in (61, 122, 183, 245, 308, 372, 438, 506):
    for sgn in (-1, 1):
        x = CX + sgn * mm / 1000 * SX
        core = mm <= 245
        col = INK if core else ("#cf222e" if sgn > 0 else MUTED)
        o.append(f'<path d="M{x-5} {YL-5} l10 10 M{x+5} {YL-5} l-10 10" stroke="{col}" stroke-width="2"/>')
        if mm in (61, 245, 506):
            o.append(text(x, YL + 20, f"{'r' if sgn>0 else 'l'}{mm}", 10, col, "middle"))
# can on zero
o.append(f'<circle cx="{CX}" cy="{YL}" r="9" fill="#d0d7de" stroke="{INK}" stroke-width="1.5"/>')
o.append(text(CX, YL - 50, "can on the 0 cross", 11, INK, "middle"))
# right-side reflector zone
rx0 = CX + 0.29 * SX
o.append(f'<rect x="{rx0}" y="{YL-22}" width="{CX+0.54*SX-rx0}" height="50" fill="#cf222e" opacity="0.08" stroke="#cf222e" stroke-dasharray="4 3"/>')
o.append(text(W - 20, YL - 75, "4  clear the bag, stand and bin on the right;", 12, "#cf222e", "end", "bold"))
o.append(text(W - 20, YL - 60, "until then fit the right side only out to r245", 11, "#cf222e", "end"))
o.append(text(W - 20, YL - 45, "(r372-r506 read 12-17° where 16-21° was taped)", 11, "#cf222e", "end"))
# legend
o.append(text(20, 618, "5  warm-up: one e1 round or ~10 min of RF before the first capture (b1→b3 drifted 0.4° as the RX warmed 54→62 °C).", 11, INK))
o.append(text(20, 636, "Then run_session.sh --line-m 1.285, check, --save, and verify on l122 · b · r122 without --save.", 11, INK))
o.append("</svg>")
(OUT / "can-remeasure.svg").write_text("\n".join(o) + "\n")
