# Session tools

Scripts for a range or studio session with an OpenFlight unit running the
IWR6843 self-trigger. They run on the Pi, beside a normal kiosk launch, and
only read what OpenFlight already writes. The analysis runs anywhere with
`python -m openflight_bench.session`.

| When | Script | What it does |
| --- | --- | --- |
| Before the first shot | `build_info.sh NAME` | Stamps branch, commit, local patch, Python, OS, cfg hashes and clock sync |
| Before the first shot | `gpio_j3_logger.sh [LINE]` | Logs OPS243 J3 pin 1 edges (S! receipt, capture close) on GPIO18 |
| During the session | `log_tails.sh ops\|iwr` | Robinante's filtered tails of the kiosk log: capture on a swing, quiet otherwise, rearm |
| A shot looks wrong | `camera_strip.py CAPTURE... -o FILE` | Frames around the trigger: real shot or false trigger |
| After the session | `export_camera_triggers.py CAMERA_DIR` | Trigger timestamps as CSV for the latency analysis |
| After the session | `iwr_net_replay.py DUMP... --net ...` | Re-runs the IWR ball tracker with other net distances |

## Run a session

```bash
cd ~/OpenFlight-Radar-Workbench
session_tools/build_info.sh studio
session_tools/gpio_j3_logger.sh            # prints the log path
# start OpenFlight from the desktop icon (not over SSH, see below)
session_tools/log_tails.sh iwr | tee ~/openflight_sessions/studio-iwr-tail.log   # second terminal
session_tools/log_tails.sh ops                                                    # third terminal
```

Write down, with the time or the shot number, every real shot that did not
register and every false shot in the history tab. The log already records
each "impact detected" without metrics.

Start OpenFlight from the desktop icon. A launch over SSH with `nohup ... &`
inherits an ignored SIGINT, so Ctrl+C and `kill -INT` no longer reach the
server, and stopping it with SIGTERM skips the OPS idle step (run
`scripts/setup/ops_idle.py --port /dev/ttyAMA0` from the OpenFlight checkout
afterwards).

## Analyze it

```bash
python -m openflight_bench.session triage --triggers terminal_logs/kiosk_*.log
python -m openflight_bench.session latency --camera camera_triggers.csv --gpio ops_j3_*.log \
    --window before 2026-11-01T11:32:21+01:00 2026-11-01T12:13:44+01:00 \
    --window after  2026-11-01T12:13:44+01:00 2026-11-01T12:35:14+01:00
```

With a TrackMan beside the unit, export the session from SwingSync (Shot
Table → Export Session) and match it shot by shot; the clock offset between
the two is found automatically:

```bash
python -m openflight_bench.session compare --shots swingsync.csv terminal_logs/kiosk_*.log
```

`triage` pairs each IWR self-trigger with the OPS verdict, the shot, the
debug readback's launch angle and the rearm. It flags smash above 1.50,
shots from three or fewer OPS readings, and triggers within 2 s of a rearm.

The [2026-11-01 studio report](../docs/reports/studio-session-2026-11-01/README.md)
was produced with these tools.
