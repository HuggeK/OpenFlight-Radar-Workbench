# Next studio tests

What to run on the next studio visit, from the
[2026-11-01 session](reports/studio-session-2026-11-01/README.md). Change one
thing per block, about 15 shots each, and note every false shot and every
real shot that did not register, with its time or shot number.

## Before the first shot

- [ ] Start OpenFlight from the desktop icon, not over SSH (Ctrl+C must work).
- [ ] Measure ball and net **from the front of the unit**: `--iwr6843-tee-m`, `--iwr6843-net-m`.
- [ ] `session_tools/build_info.sh studio` and `session_tools/gpio_j3_logger.sh`.
- [ ] Clock synced (`timedatectl`), battery charged above 0 °C.
- [ ] **Run Robinante's log tails** in two extra SSH terminals for the whole
      session (forgotten on 2026-11-01):

      session_tools/log_tails.sh iwr | tee ~/openflight_sessions/studio-iwr-tail.log
      session_tools/log_tails.sh ops | tee ~/openflight_sessions/studio-ops-tail.log

      Timeouts are normal. Check that it captures on a valid swing, stays
      quiet when nothing moves, and rearms (also after a timeout).

## Self-trigger tuning

All need `--iwr6843-self-trigger`. Baseline for every block: SNR 1.5, no other
tuning flag.

| Block | Flag | Default | Try | What to look for |
| --- | --- | --- | --- | --- |
| 1 | `--iwr6843-self-trigger-offset-m` | 0.2 (whole bins) | 0.4, then 0.6 | Moves the watched bin past the ball so a swing's line must carry beyond it. 0.2 (bin 36) did not stop backswings and waggles on 2026-11-01. Does a larger offset stop address/backswing triggers without missing shots? |
| 2 | `--iwr6843-ball-detector` | off | on, then follow | `on` locks the placed ball for the onboard shot machine and drives the kiosk's "ball placed" banner; `follow` also aims the self-trigger at the locked ball. Does the banner track ball placement, and does `follow` reduce false triggers? The banner's poll holds the IWR serial port about once a second. |
| 3 | `--iwr6843-veto-no-ball` | off | on | Skips the readback and rearms at once when the firmware sees no ball flight (waggle, raking a ball over). Shortens the 7.7 s blind window after a false trigger; off by default because the firmware's ball tracker still misses real balls. Count real shots it vetoes. |
| 4 | `--iwr6843-self-trigger-bin` | from `--iwr6843-tee-m` | 36 ± 2 | Sets the watched range bin directly (not with `offset-m`). Only if blocks 1-2 leave false triggers. |
| 5 | `--iwr6843-self-trigger-snr` | 1 | 1.5 vs 2.0, same block length | 2.0 caught real shots and 3.0 missed them on 2026-11-01, but neither stopped false triggers. Confirm with the tails running. |
| 6 | `--iwr6843-ball-snr` | firmware's, 1 | 2 | Ball tracker threshold, separate from the trigger SNR. Only with block 2 or 3. |

For each block, at the end:

```bash
python -m openflight_bench.session triage --triggers terminal_logs/kiosk_*.log
```

and walk a few minutes around the unit without swinging, then address and
waggle without hitting, to count movement triggers.

## OPS and TrackMan interference (Robinante's offset theory)

The OPS243 and TrackMan both radiate in the same room; shifting the OPS
carrier away from TrackMan's might remove interference. With OpenFlight
**stopped** (the OPS port free), on `/dev/ttyAMA0` at 230400 baud:

1. `?F` and note the frequency.
2. `T=-2` (frequency offset), wait 15 s, `?F` again.
3. Start OpenFlight, hit 10 shots at both positions (beside TrackMan and
   away from it) and compare ball and club speed with TrackMan's numbers.

Untested so far: try it at home first and note how to undo it (`T=0`), and
whether the setting survives a power cycle.

The 2026-11-01 data says fast shots (ball ≥ 150 mph) read high in **both**
positions, so also log TrackMan ball and club speed for every driver/wood
shot to size the OPS error directly.

## Other checks

- A block **without `--debug`**: the blind window should drop from 7.7 s to
  about 1 s, and `l3release refused` should disappear. No LCMF launch then.
- Quick double shots: is the IWR ready again within 2 s of the previous one?
- Practice swings away from the radar's beam, to confirm they are the cause.
- `--debug` UI request: show shot times (HH:MM:SS) in the history tab.
