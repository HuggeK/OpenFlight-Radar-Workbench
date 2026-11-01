# Studio session, 2026-11-01: IWR self-trigger next to a TrackMan 4

An indoor studio session with OpenFlight on the IWR6843 self-trigger (no sound
sensor), hitting into a net beside a TrackMan 4. Goals: focus the camera, tune
the self-trigger, and benchmark trigger latency with and without real-time
scheduling. All numbers below come from the logs in [`data/`](data/), through
`python -m openflight_bench.session` (see [session tools](../../../session_tools/README.md)).

## Lessons learned

1. **`--iwr6843-net-m` is unit → net, not ball → net.** The net was 3.0 m past
   the ball but entered as 3.0. The tracker searches from 2.25 m and stops
   0.25 m short of the net, so it had 0.5 m (~10 ms) of flight and rejected
   every track. Replaying the same dumps with 4.6 m gave 24-41 ms tracks on
   every real shot. Measured unit → net was 5.30 m.
2. **False triggers are the main problem, and SNR does not fix them.** The IWR
   fired on addresses, waggles, backswings, practice swings, placing a ball,
   and people walking up to the screen. At SNR 3.0 a practice swing still
   triggered and real shots started to go missing.
3. **Every trigger, real or false, blinds the IWR for ~7.7 s** with `--debug`
   (7.1 s readback plus a radar restart). A false trigger on the address or
   backswing therefore costs the real shot that follows it.
4. **The OPS cannot reject a practice swing either.** With no ball, it accepted
   the club head as a 58-74 mph "ball" from 27-29 readings. A single OPS
   reading over 15 mph was also enough to save a shot.
5. **The UI banner "TI radar capture failed" is misleading.** It appears on
   every shot because the firmware never has an onboard result ready
   (`triggerLog result` → `ready=0`), not because a capture failed. Data is
   still saved. Only 3 captures really failed (18-byte dumps), all on
   triggers where the OPS saw no ball: one 0.5 s after a rearm, one 6.9 s
   after, one the first trigger after a start.
6. **Real-time scheduling buys nothing.** S! reached the OPS 0.17 ± 0.01 ms
   after the host acted, with and without `chrt -f 50`. The OPS window jitter
   that looked halved under real-time was the same in later normal-priority
   runs.
7. **Fast shots read high.** Smash was above the 1.50 limit on 18 of 24 shots
   with ball speed ≥ 150 mph (median 1.57), before and after the unit was
   moved next to the TrackMan. The UI hides smash above 1.50, so most drivers
   showed none.
8. **The debug readback can measure launch.** With the right net distance, the
   host LCMF gave launch on many iron shots (e.g. 21.5° ± 0.6°), but that
   value is only logged: the shot keeps the estimated angle, because the shot
   path uses the firmware's onboard result.
9. **Launch OpenFlight from the desktop icon.** Started over SSH with
   `nohup … &`, the server ignored SIGINT and had to be stopped with SIGTERM,
   which skips the OPS idle step.

## Setup

| Item | Value |
| --- | --- |
| OpenFlight | `feat/iwr-self-trigger` + 2 local commits (OPS idle, backlight), see [`trackman-build-info.txt`](data/trackman-build-info.txt) |
| IWR6843 firmware | 1.0.3 (git 4e4e9c5d94b7, hybrid-cadence, built 2026-10-09) |
| OPS243-A | firmware 1.3.3, GPIO UART `/dev/ttyAMA0` at 230400 baud, rolling buffer S#24, 30 kS/s |
| Trigger | IWR self-trigger (`triggerCfg 36 <snr> 1`), no SEN-14262 |
| Geometry | ball 1.57 m, net 5.30 m (from 11:32), IWR board centre 0.04 m above the floor, tilt 10.1° (inclinometer ~9.9°) |
| Camera | OV9281, 320×200 at 450 fps (430.9 delivered, 0 gaps on 127 captures), 150 ms pre / 50 ms post |
| Extra wiring | OPS J3 pin 1 → Pi pin 12 (GPIO18), logged with `gpiomon` |
| Flags | `--debug` (full IWR readback), `--session-location trackman` |

![OpenFlight unit at the hitting area, seen from behind the radar](photos/IMG_2821.webp)

![Same position through the swing](photos/IMG_2822.webp)

![OpenFlight beside the TrackMan 4, where it stood from about 11:52](photos/IMG_2823.webp)

![The hitting area with OpenFlight beside the TrackMan](photos/IMG_2819.jpg)

![TrackMan's view of a 9-iron, for comparison](photos/IMG_2825.webp)

## Runs

| Log | Time | SNR | Net | Triggers | Shots | No-ball triggers | Smash > 1.5 | Launch measured |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [`kiosk_20261101_111546`](data/kiosk_20261101_111546.log) | 11:15-11:31 | 1.5 | 3.0 m ✗ | 20 | 10 | 10 | 1 | 1 |
| [`kiosk_20261101_113221`](data/kiosk_20261101_113221.log) | 11:32-12:34 | 1.5 | 5.30 m | 76 | 49 | 27 | 19 | 20 |
| [`kiosk_20261101_123514`](data/kiosk_20261101_123514.log) | 12:35-12:45 | 2.0 | 5.30 m | 17 | 11 | 6 | 0 | 3 |
| [`kiosk_20261101_124549`](data/kiosk_20261101_124549.log) | 12:45-12:55 | 3.0 | 5.30 m | 14 | 12 | 2 | 3 | 2 |

"No-ball triggers" are the UI's "impact detected" without metrics: the IWR
fired but the OPS saw no outbound speed. Real-time scheduling was on from
12:13:44 to 12:34 inside the second run.

### What the player saw, by SNR

From the [session notes](data/trackman-notes.txt), checked against the
camera clips:

| SNR | False shots saved | Real shots missed |
| --- | --- | --- |
| 1.5 | practice swing (#26), walking up to the screen (#30), address (#36), backswing (#43); likely also #17, #19, #22, #23 (~20 mph, 1-3 readings) | 3-wood at ~12:13 (no trigger); the shot after #43 (blind window); the second of two quick shots (spurious trigger 0.44 s after rearm) |
| 2.0 | moving around (#1), practice swing with no ball (#8, 27 readings), backswing (#9), address (#10) | the swings after #9 and #10 (blind window) |
| 3.0 | practice swing (#2, 29 readings); likely #7 (1 reading) | two real shots at ~12:48 (one after a false trigger, one with no trigger) |

Movement alone at SNR 2.0 gave 4 triggers in ~45 s. Placing a ball triggered
at SNR 3.0.

## Net distance

Shots from 11:18 to 11:27 ran with `--iwr6843-net-m 3.0`. Offline replay
([`iwr_net_replay.py`](../../../session_tools/iwr_net_replay.py)) on the same
dumps:

| Dump | net 3.0 | net 4.6 | no net |
| --- | --- | --- | --- |
| 111824_001 | reject, 9 ms | ok, 27 ms | ok, 27 ms |
| 111911_003 | reject, 9 ms | ok, 41 ms | ok, 43 ms |
| 112540_015 | reject, 13 ms | ok, 41 ms | ok, 41 ms |
| 112630_017 | ok, 16 ms | ok, 27 ms | ok, 27 ms |

The tracks reach past 3 m from the unit, which is how the mistake showed up.

## Trigger latency and the real-time A/B

`gpiomon` logged J3 pin 1 on GPIO18; each camera capture records the host's
trigger time on the same monotonic clock
([`camera_triggers_20261101.csv`](data/camera_triggers_20261101.csv),
[`ops_j3_20261101_111438.log`](data/ops_j3_20261101_111438.log)).

```
python -m openflight_bench.session latency --camera data/camera_triggers_20261101.csv \
  --gpio data/ops_j3_20261101_111438.log \
  --window normal   2026-11-01T11:32:21+01:00 2026-11-01T12:13:44+01:00 \
  --window realtime 2026-11-01T12:13:44+01:00 2026-11-01T12:35:14+01:00 \
  --window snr2     2026-11-01T12:35:14+01:00 2026-11-01T12:45:49+01:00 \
  --window snr3     2026-11-01T12:45:49+01:00 2026-11-01T13:00:00+01:00
```

| Window | Scheduling | Triggers | S! → OPS (J3 rise) | OPS window (J3 rise → fall) |
| --- | --- | --- | --- | --- |
| 11:32-12:13 | normal | 54 | 0.17 ± 0.01 ms | 44.8 ± 6.1 ms (30-51) |
| 12:13-12:35 | `chrt -a -f 50` | 22 | 0.17 ± 0.01 ms | 47.5 ± 2.5 ms (41-51) |
| 12:35-12:45 | normal, new process | 17 | 0.16 ± 0.01 ms | 31.7 ± 1.8 ms (27-34) |
| 12:45-12:55 | normal, new process | 14 | 0.17 ± 0.01 ms | 32.1 ± 1.1 ms (31-34) |

The fresh processes match S#24's post-trigger length (1024 samples at
30 kS/s = 34 ms); why the long-running process saw 30-51 ms is open.
Impact → S! from the server log was 0.3 ± 3.6 ms (n=44) normal and
−0.4 ± 2.9 ms (n=12) real-time: dominated by the impact estimate, not by
scheduling. **Verdict: do not make real-time priority a default.**

## Speeds against the smash limit

| Shots | Before the move (11:15-11:52) | After the move |
| --- | --- | --- |
| Ball < 150 mph | 1 of 15 over 1.50, median 1.38 | 4 of 16, median 1.49 |
| Ball ≥ 150 mph | 4 of 5, median 1.63 | 14 of 19, median 1.57 |

Fast shots read high in both positions, so TrackMan proximity is not the main
cause; the slower shots got somewhat worse after the move. Shot #11 (194 mph
ball, 85 mph club, 7-iron) is a clear OPS misread. Compare against TrackMan
ball and club speed next time (see [next tests](../../NEXT_STUDIO_TESTS.md)).

## Other observations

- Camera: the alignment preview script always flips 180°; this unit's camera
  sits upright, so `--camera-capture-rotate-180` was removed before the
  session and the lens refocused at 1280×800.
- `l3release refused … self-trigger freeze timed out` after every `--debug`
  capture, then a radar restart. Fixed in firmware source by
  open-flight/openflight `cb8fbffb`; no binary yet.
- One driver got an IWR launch (9.9°, std 6°); drivers otherwise withheld
  (`insufficient_channel_snapshots`, `rejected_track_quality`).
- Request: in `--debug`, show each shot's time (HH:MM:SS) in the history tab,
  so notes can be matched to the log.

## Files

| File | Content |
| --- | --- |
| `data/kiosk_*.log` | Kiosk terminal logs, one per OpenFlight start |
| `data/session_*_trackman.jsonl` | OpenFlight session logs (shots, IWR results) |
| `data/trackman-notes.txt` | Notes taken during the session, with the player's observations |
| `data/ops_j3_20261101_111438.log` | GPIO18 edges (monotonic seconds) |
| `data/camera_triggers_20261101.csv` | Camera trigger timestamps, 127 captures |
| `data/trackman-build-info.txt`, `data/trackman-local-changes.patch` | Build stamp |

The IWR dumps (~730 kB each) and camera clips (~6 MB each) stay on the Pi.
