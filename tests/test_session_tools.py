"""Field-session tools: kiosk log triage and J3 latency matching.

The log lines are copied from a real 2026-11-01 studio session, trimmed to the
ones the parser reads, so the expected values are the ones in the log.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from openflight_bench.session import (  # noqa: E402
    Edge, LatencyWindow, load_camera_triggers, load_edges, match_triggers,
    parse_kiosk_log, summarize,
)
from openflight_bench.session.latency import CameraTrigger  # noqa: E402
from openflight_bench.session.trackman import (  # noqa: E402
    find_offset, load_swingsync_csv, match_shots,
)

LOG = """\
2026-11-01 12:45:53,066 - openflight.iwr6843.monitor - INFO - [IWR6843] Configured on BCM17 using /dev/ttyUSB0 (cfg, self-trigger 'triggerCfg 36 3.0 1')
2026-11-01 12:47:40,451 - openflight.iwr6843.monitor - INFO - [IWR6843] Trigger #1: reading track samples
2026-11-01 12:47:43,200 - openflight.rolling_buffer.trigger - INFO - [TRIGGER] IWR6843 self-trigger accepted — peak 57.0 mph, 27 outbound readings
2026-11-01 12:47:43,315 - openflight.rolling_buffer.monitor - INFO - [SHOT] #1: ball=31.0 mph, club=21.3, carry=42 yds | trigger=16669ms
2026-11-01 12:47:47,000 - openflight.server - INFO - [SERVER] Self-trigger impact -> S!: 2.6 ms (OPS pre-trigger 102.4 ms)
2026-11-01 12:47:47,001 - openflight.server - INFO - [SERVER] IWR6843 host LCMF-v1 withheld angle: rejected_by_ball_tracker
2026-11-01 12:47:47,002 - openflight.server - WARNING - [SERVER] IWR6843 capture #1 carried no onboard result; preserving OPS shot
2026-11-01 12:47:48,151 - openflight.iwr6843.monitor - WARNING - [IWR6843] Radar restarted to rearm it after a capture
2026-11-01 12:48:01,539 - openflight.iwr6843.monitor - INFO - [IWR6843] Trigger #2: reading track samples
2026-11-01 12:48:04,328 - openflight.rolling_buffer.trigger - INFO - [TRIGGER] IWR6843 self-trigger rejected — no outbound speed >= 15 mph (peak=0.0 mph, 0 readings)
2026-11-01 12:48:06,000 - openflight.iwr6843.monitor - WARNING - [IWR6843] Capture #2 failed: short IWR6843 dump: 18 bytes
2026-11-01 12:48:06,030 - openflight.iwr6843.monitor - INFO - [IWR6843] Rearmed after the capture (l3release)
2026-11-01 12:48:06,500 - openflight.server - INFO - [SERVER] Club changed to 7-iron
2026-11-01 12:48:07,000 - openflight.iwr6843.monitor - INFO - [IWR6843] Trigger #3: reading track samples
2026-11-01 12:48:09,800 - openflight.rolling_buffer.trigger - INFO - [TRIGGER] IWR6843 self-trigger accepted — peak 200.3 mph, 33 outbound readings
2026-11-01 12:48:09,900 - openflight.rolling_buffer.monitor - INFO - [SHOT] #2: ball=200.3 mph, club=130.6, carry=375 yds | trigger=28867ms
2026-11-01 12:48:14,000 - openflight.iwr6843.monitor - INFO - [IWR6843] Trigger #4: reading track samples
2026-11-01 12:48:14,100 - openflight.server - INFO - [SERVER] Self-trigger impact -> S!: -3.3 ms (OPS pre-trigger 102.4 ms)
2026-11-01 12:48:14,101 - openflight.server - INFO - [SERVER] IWR6843 host LCMF-v1 launch: 25.91° (24 snapshots/9 frames, component std 5.68°)
2026-11-01 12:48:14,102 - openflight.server - INFO - [SERVER] Camera capture #3 matched -> /home/openfl/camera_003
"""


@pytest.fixture()
def session(tmp_path):
    path = tmp_path / "kiosk_test.log"
    path.write_text(LOG, encoding="utf-8")
    return parse_kiosk_log(path)


def test_config_and_counts(session):
    assert session.self_trigger_snr == 3.0
    assert session.self_trigger_bin == 36
    assert [t.sequence for t in session.triggers] == [1, 2, 3, 4]
    assert [t.verdict for t in session.triggers] == ["accepted", "rejected", "accepted", None]
    assert [s.number for s in session.shots] == [1, 2]


def test_shot_and_readback_pairing(session):
    first, second, third, fourth = session.triggers
    assert first.shot.ball_mph == 31.0 and first.shot.club_mph == 21.3
    assert first.readings == 27
    assert first.impact_to_s_ms == 2.6
    assert first.launch_status == "rejected_by_ball_tracker"
    assert first.blind_s == pytest.approx(7.7)
    # The readback for capture #3 is logged after trigger #4 began; it still
    # lands on #3 because the "Camera capture #3 matched" line names it.
    assert third.launch_deg == pytest.approx(25.91)
    assert third.impact_to_s_ms == -3.3
    assert fourth.launch_deg is None
    assert second.capture_error == "short IWR6843 dump: 18 bytes"
    assert second.since_rearm_s == pytest.approx(13.388)
    assert third.since_rearm_s == pytest.approx(0.97)
    assert third.shot.club == "7-iron"


def test_summary_flags(session):
    summary = session.summary()
    assert summary["triggers"] == 4
    assert summary["accepted"] == 2
    assert summary["rejected_no_ball"] == 1
    assert summary["smash_over_limit"] == 1  # 200.3 / 130.6
    assert summary["capture_failed"] == 1
    assert summary["triggers_within_2s_of_rearm"] == 1
    assert summary["launch_measured"] == 1


SWINGSYNC = """\
Shot number,Date,Classification,Club type,Club name,Carry,Total,Club speed,Ball speed,Smash factor,Vertical Launch angle
,,,,,[m],[m],[kph],[kph],,[°]
1,2026-11-01T11:54:46.351Z,Baby Draw,,,146.490,149.040,132.980,186.618,1.403,21.070
2,2026-11-01T11:55:12.900Z,Huge Push,,,134.310,136.170,134.880,182.716,1.355,23.330
3,2026-11-01T11:55:19.900Z,Fade,,,140.000,142.000,130.000,180.000,1.385,20.000
4,2026-11-01T11:58:00.000Z,Pull,,,120.000,122.000,125.000,170.000,1.360,18.000
"""


def test_trackman_offset_and_match(session, tmp_path):
    path = tmp_path / "swingsync.csv"
    path.write_text(SWINGSYNC, encoding="utf-8")
    shots = load_swingsync_csv(path)
    assert [s.number for s in shots] == [1, 2, 3, 4]
    assert shots[0].ball_mph == pytest.approx(186.618 / 1.609344)
    assert shots[0].launch_deg == 21.07

    # Shots 1-3 are triggers #1, #3 and #4 seen on a TrackMan clock 425.9 s
    # fast; shot 4 has no trigger.
    offset, hits = find_offset(shots, session.triggers, utc_offset_s=3600)
    assert hits == 3
    assert offset == pytest.approx(425.9, abs=0.5)
    matches = match_shots(shots, session.triggers, offset_s=offset, utc_offset_s=3600)
    assert [m.trigger.sequence if m.trigger else None for m in matches] == [1, 3, 4, None]


def test_gpio_edges_skip_noise(tmp_path):
    path = tmp_path / "ops_j3.log"
    path.write_text("100.000100 rising\nnot an edge\n100.034100 falling\n", encoding="utf-8")
    assert load_edges(path) == [Edge(100.0001, "rising"), Edge(100.0341, "falling")]


def test_latency_match_and_windows(tmp_path):
    csv_path = tmp_path / "camera.csv"
    csv_path.write_text(
        "capture,sequence,trigger_epoch_s,trigger_monotonic_ns,frames,fps,gaps\n"
        "a,1,1000.0,100000000000,91,430.9,0\n"
        "b,2,2000.0,200000000000,91,430.9,0\n",
        encoding="utf-8",
    )
    triggers = load_camera_triggers(csv_path)
    assert triggers[0] == CameraTrigger(sequence=1, epoch_s=1000.0, monotonic_s=100.0)
    edges = [Edge(100.00017, "rising"), Edge(100.03417, "falling"), Edge(250.0, "rising")]
    rows = match_triggers(triggers, edges)
    assert rows[0].rise_ms == pytest.approx(0.17)
    assert rows[0].window_ms == pytest.approx(34.0)
    assert rows[1].rise_ms is None and rows[1].window_ms is None

    epoch = lambda s: datetime.fromtimestamp(s, tz=timezone.utc)  # noqa: E731
    stats = summarize(rows, [LatencyWindow("first", epoch(999), epoch(1500))])
    assert stats["first"]["triggers"] == 1
    assert stats["first"]["rise_ms"]["n"] == 1
    assert stats["first"]["window_ms"]["mean"] == pytest.approx(34.0)
