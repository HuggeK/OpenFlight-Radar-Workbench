# Next studio tests

What to run on the next studio visit, from the
[2026-11-01 session](reports/studio-session-2026-11-01/README.md). Change one
thing per block, about 15 shots each, and note every false shot and every
real shot that did not register, with its time or shot number.

## At home, before the session

### OPS: clean saved settings (keep rolling-buffer mode saved, for now)

The sound trigger is gone, so the HOST_INT reason for saving rolling-buffer
mode to the OPS's flash is gone too. **But do not remove it yet:** with
`--iwr6843-self-trigger` the OPS still starts the sound-trigger way
(`prepare_persisted_rolling_buffer()` in `feat/iwr-self-trigger`), which
never sends `GC` and expects the OPS to *boot* in rolling-buffer mode. Without
the saved mode the OPS boots in normal mode and the IWR's `S!` gives no dump.

What to do instead:

- [ ] Reset the OPS's saved settings to factory defaults (the reset command
      is in OmniPreSense's API document AN-010; check it there first), then
      re-run the one-time setup and power-cycle:

      ```bash
      uv run python scripts/hardware-test/test_rolling_buffer_persist.py --setup
      # unplug the OPS for 3 s, plug it back in
      uv run python scripts/hardware-test/test_rolling_buffer_persist.py --test
      ```

      The setup saves `GC` and `S#16` but never clears the speed trigger, so
      a speed trigger left over from an `--trigger hardware` run can be saved
      with it. That is the likely cause of Robinante's "OPS fires on its own
      before the IWR's S!" (2026-11-22).
- [ ] Self-fire check: OpenFlight running with `--iwr6843-self-trigger`,
      nobody moving, 10 minutes. Any OPS dump in the OPS tail without an
      `S!` just before it is the OPS firing on its own. On 1.3.3 its UART
      trigger message says it was the speed trigger; without that message,
      check that HOST_INT (J3 pin 3) is not floating now the mic is gone
      (10 kΩ pull-down to GND).
- Follow-up for `feat/iwr-self-trigger`, not for this session: send `GC`,
  `S#` and "speed trigger off" at startup on the `S!` path, like
  `--trigger hardware` does. Then the saved rolling-buffer mode and its
  setup script can go.

### Pi: logs that survive a reboot

- [ ] Keep the system journal on disk permanently (not only for this
      session), with a size cap so it cannot fill the card:

      ```bash
      sudo mkdir -p /var/log/journal
      sudo sed -i 's/^#\?Storage=.*/Storage=persistent/; s/^#\?SystemMaxUse=.*/SystemMaxUse=500M/' /etc/systemd/journald.conf
      sudo systemctl restart systemd-journald
      journalctl --disk-usage            # check it took
      journalctl --list-boots | tail -3  # older boots should now be kept
      ```

### Pi: room for recordings

Each `--debug --iwr6843-full-capture` shot saves a ~0.7 MB IWR dump, plus the
OPS capture and the camera clip; a session can reach several GB.

- [ ] See what is free and what is using it:

      ```bash
      df -h /
      du -sh ~/openflight_sessions ~/openflight_sessions/* | sort -h | tail
      ```

- [ ] Copy older sessions to the PC or a USB stick, check the copy, then
      delete them on the Pi:

      ```bash
      rsync -a --info=progress2 ~/openflight_sessions/ <pc-or-usb>:/openflight_sessions/
      ```

- [ ] Free system space: `sudo apt clean`,
      `sudo journalctl --vacuum-size=200M` (before turning on the cap above),
      and old `~/.cache/uv` builds if space is still short.
- [ ] Aim for at least ~10 GB free before the session.

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
- [ ] Persistent OS logs are on (`journalctl --disk-usage`; see
      [At home](#pi-logs-that-survive-a-reboot)), so kernel UART errors, NTP
      and RTC events around a sample-rate change survive a reboot.
- [ ] At least ~10 GB free (`df -h /`).
- [ ] Log the IWR's GPIO17 trigger edge next to J3 (GPIO18):
      `session_tools/gpio_j3_logger.sh 17`
- [ ] Keep the unit in **one position per block** and note any move with the
      time; on 2026-11-01 the IWR was much better on the right side than beside
      the TrackMan. Which block goes where: [Placement](#placement).
- [ ] Use `--session-location studio`, not a name that reads like TrackMan data.
- [ ] **Set the OPS buffer split to S#10:** add `--sound-pre-trigger 10` to the
      start command. Without it, `feat/iwr-self-trigger` uses S#24 whenever
      `--iwr6843-self-trigger` is on, which kept only ~42 ms of ball on
      2026-11-01 (see [OPS buffer split](#ops-buffer-split-s10-instead-of-s24)).
      Check the first capture: `trigger_offset_ms` should read **42.67**.
- [ ] **Run Robinante's log tails** in two extra SSH terminals for the whole
      session (forgotten on 2026-11-01):

      session_tools/log_tails.sh iwr | tee ~/openflight_sessions/studio-iwr-tail.log
      session_tools/log_tails.sh ops | tee ~/openflight_sessions/studio-ops-tail.log

      Timeouts are normal. Check that it captures on a valid swing, stays
      quiet when nothing moves, and rearms (also after a timeout).

## Placement

Two positions, as on 2026-11-01. The distance between OpenFlight and the
TrackMan does not bias the numbers: both measure the same ball from where
they stand. What matters is that each knows its own geometry (distances,
heights, tilt) and that both aim at the **same target line**, or horizontal
launch and club path carry a constant offset.

| Position | Where | TrackMan gives | 2026-11-01 |
| --- | --- | --- | --- |
| **R** | right side of the hitting area, looking downrange, open floor | ball data only | IWR launch 0.90° MAE vs TrackMan, 1 of 10 tracks wrong |
| **L** | left side, ball in TrackMan's hitting area beside its wall alcove | ball **and club** data | 2.00° MAE, 5 of 13 tracks wrong (wall reflections and aim suspected) |

Set-up at each position, and again after every move:

- [ ] Lay an alignment stick on the target line through the ball, the same
      target TrackMan uses. Put the unit behind the ball, centred on the
      stick, pointing along it. Each 1 cm sideways off the line biases
      horizontal launch by ~0.36° at 1.6 m.
- [ ] Ball ~1.6 m from the unit (the branch's ideal band is 1.45-1.75 m;
      closer gives a stronger ball echo and a longer IWR track, below 1.45 m
      the club's approach starts to leave the IWR window). Measure tee, net and
      heights as in [Before the first shot](#before-the-first-shot).
- [ ] Ball detector (block 2) first: the banner should read **ideal** with a
      range matching `--iwr6843-tee-m`, and a ball azimuth near 0° (it is the
      unit's aim error).
- [ ] At **L**: move the unit 30-50 cm out from the alcove wall if TrackMan
      still reports club data there, and confirm it does before the block.
- [ ] Note the position letter and time in the notes for every block. Never
      compare R and L shots in one table.

| Block | Position | Why |
| --- | --- | --- |
| Block 0 (`swing_trigger.py` sweep) | R (or at home) | trigger only, no reference needed |
| Self-trigger tuning 1-6 | R | IWR and trigger, ball data is enough |
| IWR launch vs TrackMan | R | best IWR results, no wall |
| OPS ball speed and spin | R | ball data |
| S#10 blocks for club speed and smash | **L** | needs TrackMan club data |
| S#16 comparison block | **L**, same clubs | compared with the S#10 blocks at L |
| IWR club path vs TrackMan | **L** | needs TrackMan club data |
| OPS `T=-2` interference test | R and L | the test is the position difference |
| Block without `--debug` | R | trigger and rearm timing |

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

## OPS buffer split (S#10 instead of S#24)

The OPS keeps 4096 samples (136.5 ms at 30 kS/s) in 32 segments of ~4.27 ms;
`S#n` is how many segments it keeps *before* the trigger. The IWR fires ~2
frames after launch and `S!` reaches the OPS in 0.17 ms, so the trigger lands
about 8 ms after impact (including the wait for the OPS's next segment). The
flag is still called `--sound-pre-trigger`, but it sets the OPS split for any
trigger that reaches the OPS as `S!`.

| S#n | Before trigger | Club before impact | Ball after impact | `trigger_offset_ms` | J3 window (post-trigger) |
| --- | --- | --- | --- | --- | --- |
| 24 (branch default, 2026-11-01) | 102.4 ms | ~94 ms | ~42 ms | 102.00 | ~34 ms |
| 16 | 68.3 ms | ~60 ms | ~76 ms | 68.27 | ~68 ms |
| **10 (next session)** | 42.7 ms | ~35 ms | ~102 ms | 42.67 | ~94 ms |

Why 10: ~35 ms of club (a driver head covers ~1.5 m in that time) is enough
for club speed and the club-to-ball impact estimate, while the ball window
grows from ~42 to ~102 ms for spin and speed-curve launch estimates
([issue #355](https://github.com/open-flight/openflight/issues/355)). It also
keeps shots whose trigger fires 60-70 ms *early* (3 on 2026-11-01): their
impact still lands inside the buffer, where S#24 lost them. Indoors the ball
hits the net after ~43 ms (driver) to ~86 ms (wedge), so the gain shows most
on wedges and chips, and outdoors.

- [ ] Run every block at S#10.
- [ ] One extra block of 15 shots at `--sound-pre-trigger 16`, same clubs,
      at position **L** (TrackMan club data, see [Placement](#placement)):
      compare **club speed and smash** against TrackMan with an S#10 block
      at L. If they hold at S#10, propose S#10 as the self-trigger
      default in `feat/iwr-self-trigger`.
- [ ] Note any shot where the OPS `impact_offset_from_trigger_ms` is missing
      or the club phase looks cut short.

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

- [ ] Keep `gpio_j3_logger.sh` running and watch the J3 window: at S#10 and
      30 kS/s it should be ~94 ms; ~140 ms means the OPS slowed to 20 kS/s
      (×1.5, as on 2026-11-01, when S#24 went from ~34 to ~48-51 ms). The
      `S#24` → `S2` theory below means any `S#` re-arm can do this, so keep
      the check whatever the split.
- [ ] When it happens, stop OpenFlight and query the OPS before any restart:
      sample rate and module settings (`S?`, `??`; confirm the query commands
      in OmniPreSense's API document AN-010 first), and save the replies.
- [ ] Note what happened just before (here: a normal rearm at 11:37:26, the
      shot before had 83.5 mph and 1.34 % clipped samples).
- [ ] Check whether a restart alone fixes it (it did on 2026-11-01).
- [ ] Check without J3 too: every `rolling_buffer_capture` in the session
      JSONL carries the OPS's `trigger_offset_ms`. At S#10 that is 42.67 at
      30 kS/s and 64.0 at 20 kS/s (S#24 on 2026-11-01: 102.0 and 154.0).
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
