# Next studio tests

What to run on the next studio visit, from the
[2026-11-01 session](reports/studio-session-2026-11-01/README.md). Change one
thing per block, about 15 shots each, and note every false shot and every
real shot that did not register, with its time or shot number.

## Before the first shot

- [ ] Start OpenFlight from the desktop icon, not over SSH (Ctrl+C must work).
- [ ] Measure ball and net **from the front of the unit**: `--iwr6843-tee-m`, `--iwr6843-net-m`.
- [ ] Measure both heights **from the floor the unit stands on** (lay a level
      across if the mat is higher):
      `--iwr6843-radar-height-m` = centre of the IWR antenna group (TX + RX
      patches, not the board centre or the enclosure bottom);
      `--iwr6843-ball-height-m` = centre of the ball = mat height + 0.021 m
      (4 cm mat → 0.061 m; 2026-11-01 ran 0.04 by mistake).
- [ ] Photograph the IWR front square-on with a ruler beside it, so the
      antenna centre of the experimental mount can be documented.
- [ ] Try the validated height: antenna centre ~0.15 m above the floor, ~10° tilt.
- [ ] `session_tools/build_info.sh studio` and `session_tools/gpio_j3_logger.sh`.
- [ ] Clock synced (`timedatectl`), battery charged above 0 °C.
- [ ] Turn on persistent OS logs before the session, so kernel UART errors,
      NTP and RTC events around a sample-rate change survive a reboot:
      `sudo mkdir -p /var/log/journal && sudo sed -i 's/^#\?Storage=.*/Storage=persistent/' /etc/systemd/journald.conf && sudo systemctl restart systemd-journald`
- [ ] Log the IWR's GPIO17 trigger edge next to J3 (GPIO18):
      `session_tools/gpio_j3_logger.sh 17`
- [ ] Keep the unit in **one position per block** and note any move with the
      time; on 2026-11-01 the IWR was much better on the right side than beside
      the TrackMan.
- [ ] Use `--session-location studio`, not a name that reads like TrackMan data.
- [ ] **Run Robinante's log tails** in two extra SSH terminals for the whole
      session (forgotten on 2026-11-01):

      session_tools/log_tails.sh iwr | tee ~/openflight_sessions/studio-iwr-tail.log
      session_tools/log_tails.sh ops | tee ~/openflight_sessions/studio-ops-tail.log

      Timeouts are normal. Check that it captures on a valid swing, stays
      quiet when nothing moves, and rearms (also after a timeout).

## Block 0: sweep the self-trigger without the kiosk

[`scripts/iwr6843/swing_trigger.py`](https://github.com/open-flight/openflight/blob/feat/iwr-self-trigger/scripts/iwr6843/swing_trigger.py)
in the OpenFlight checkout arms the IWR self-trigger on its own: it samples
the empty lane for 2 s (prints the floor p95 and the threshold), arms
`triggerCfg` at `--snr`, and for every fire prints the club track and
**PASS** when the club track's range impact fired. No OPS, no readback, so no
7.7 s blind window: a fast way to count what fires the trigger.

Stop the kiosk first (it owns the UART). Then, per SNR:

```bash
cd ~/openflight
uv run --no-sync python scripts/iwr6843/swing_trigger.py \
  --port /dev/serial/by-id/usb-Silicon_Labs_CP2105_Dual_USB_to_UART_Bridge_Controller_01310F8D-if00-port0 \
  --tee-m 1.57 --snr 1.5
```

| SNR | Real swings (10) | Addresses (5) | Waggles (5) | Takeaways stopped at hip (5) | Practice swings beside the ball (5) | Walking past (1 min) |
| --- | --- | --- | --- | --- | --- | --- |
| 1.5 | | | | | | |
| 2.0 | | | | | | |
| 3.0 | | | | | | |

Note the floor p95 for each run (it says how noisy the bay is), and whether a
fire is PASS (club track) or FAIL (something else). Ctrl+C prints
`passed/swings`. Pick the SNR for the kiosk blocks from this table.

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

On 2026-11-01 the large speed errors were not interference: the OPS read
1.49 × TrackMan from 11:37:53 until a restart, in both positions (see below).
Export TrackMan through SwingSync again and run
`python -m openflight_bench.session compare` to size what is left.

## OPS sampling change (×1.49 speeds)

- [ ] Keep `gpio_j3_logger.sh` running and watch the J3 window: ~34 ms is
      normal for S#24 at 30 kS/s; ~48-51 ms means the OPS slowed down.
- [ ] When it happens, stop OpenFlight and query the OPS before any restart:
      sample rate and module settings (`S?`, `??`; confirm the query commands
      in OmniPreSense's API document AN-010 first), and save the replies.
- [ ] Note what happened just before (here: a normal rearm at 11:37:26, the
      shot before had 83.5 mph and 1.34 % clipped samples).
- [ ] Check whether a restart alone fixes it (it did on 2026-11-01).
- [ ] Check without J3 too: every `rolling_buffer_capture` in the session
      JSONL carries the OPS's `trigger_offset_ms`, 102.0 at 30 kS/s and 154.0
      at 20 kS/s.
- [ ] Read the OPS's UART error counters (`query_uart_baud()` in
      `openflight.ops243`) before and after the session.
- [ ] Note the time of the "cue" games (poking the ball to set off the
      trigger): the camera only records around a trigger, so only the log
      shows what happened between triggers.

## Other checks

- A block **without `--debug`**: the blind window should drop from 7.7 s to
  about 1 s, and `l3release refused` should disappear. No LCMF launch then.
- Quick double shots: is the IWR ready again within 2 s of the previous one?
- Practice swings away from the radar's beam, to confirm they are the cause.
- `--debug` UI request: show shot times (HH:MM:SS) in the history tab.
