"""Parse an OpenFlight kiosk terminal log into IWR self-triggers and shots.

One IWR self-trigger produces, in order: ``Trigger #N: reading track
samples``, the OPS verdict (``self-trigger accepted`` or ``rejected``), a
``[SHOT] #n`` line when accepted, the debug readback's LCMF result and
``Self-trigger impact -> S!``, then ``Radar restarted to rearm`` (or
``Rearmed after the capture``). The LCMF and impact lines can land after the
next trigger has started, so they are held until a line names their capture
(``IWR6843 capture #N carried ...`` or ``Camera capture #N matched``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re


LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d{3}) - \S+ - \w+ - (.*)$")
TRIGGER = re.compile(r"\[IWR6843\] Trigger #(\d+): ")
ACCEPTED = re.compile(r"self-trigger accepted .*?peak ([\d.]+) mph, (\d+) outbound readings")
REJECTED = re.compile(r"self-trigger rejected .*?\(peak=([\d.]+) mph, (\d+) readings\)")
SHOT = re.compile(r"\[SHOT\] #(\d+): ball=([\d.]+) mph, club=([\d.]+|N/A)")
REARM = re.compile(r"Radar restarted to rearm|Rearmed after the capture")
IMPACT = re.compile(r"Self-trigger impact -> S!: (-?[\d.]+) ms")
LAUNCH = re.compile(r"host LCMF-v1 launch: (-?[\d.]+)°")
WITHHELD = re.compile(r"host LCMF-v1 withheld angle: (\w+)")
CAPTURE_DONE = re.compile(r"IWR6843 capture #(\d+) carried|Camera capture #(\d+) matched")
CAPTURE_FAILED = re.compile(r"\[IWR6843\] Capture #(\d+) failed: (.*)")
SNR = re.compile(r"self-trigger 'triggerCfg (\d+) ([\d.]+) (\d+)'")
CLUB = re.compile(r"Club changed to (.+)$")

# A smash factor above this is physically impossible (USGA COR limit); the
# OpenFlight UI hides smash above it.
MAX_SMASH = 1.5


@dataclass
class Shot:
    """One ``[SHOT]`` line."""

    number: int
    time: datetime
    ball_mph: float
    club_mph: float | None
    club: str | None = None

    @property
    def smash(self) -> float | None:
        if not self.club_mph:
            return None
        return self.ball_mph / self.club_mph


@dataclass
class Trigger:
    """One IWR self-trigger and everything the log tied to it."""

    sequence: int
    time: datetime
    verdict: str | None = None  # "accepted" / "rejected"
    peak_mph: float | None = None
    readings: int | None = None
    shot: Shot | None = None
    rearm_time: datetime | None = None
    impact_to_s_ms: float | None = None
    launch_deg: float | None = None
    launch_status: str | None = None
    capture_error: str | None = None
    since_rearm_s: float | None = None  # gap from the previous rearm, if any

    @property
    def blind_s(self) -> float | None:
        """Seconds the radar could not trigger again after this one."""
        if self.rearm_time is None:
            return None
        return (self.rearm_time - self.time).total_seconds()


@dataclass
class KioskSession:
    """Everything parsed from one kiosk log."""

    path: Path
    triggers: list[Trigger] = field(default_factory=list)
    shots: list[Shot] = field(default_factory=list)
    self_trigger_snr: float | None = None
    self_trigger_bin: int | None = None

    def summary(self) -> dict[str, object]:
        accepted = [t for t in self.triggers if t.verdict == "accepted"]
        rejected = [t for t in self.triggers if t.verdict == "rejected"]
        blind = [t.blind_s for t in self.triggers if t.blind_s is not None]
        smash = [s.smash for s in self.shots if s.smash is not None]
        return {
            "log": self.path.name,
            "snr": self.self_trigger_snr,
            "bin": self.self_trigger_bin,
            "triggers": len(self.triggers),
            "accepted": len(accepted),
            "rejected_no_ball": len(rejected),
            "shots": len(self.shots),
            "shots_no_club_speed": sum(1 for s in self.shots if s.club_mph is None),
            "shots_few_readings": sum(
                1 for t in accepted if t.readings is not None and t.readings <= 3
            ),
            "smash_over_limit": sum(1 for x in smash if x > MAX_SMASH),
            "launch_measured": sum(1 for t in self.triggers if t.launch_deg is not None),
            "capture_failed": sum(1 for t in self.triggers if t.capture_error),
            "triggers_within_2s_of_rearm": sum(
                1 for t in self.triggers if t.since_rearm_s is not None and t.since_rearm_s < 2.0
            ),
            "median_blind_s": _median(blind),
        }


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def parse_kiosk_log(path: str | Path) -> KioskSession:
    """Parse one kiosk terminal log (``terminal_logs/kiosk_*.log``)."""
    path = Path(path)
    session = KioskSession(path=path)
    by_sequence: dict[int, Trigger] = {}
    pending: dict[str, object] = {}
    last_rearm: datetime | None = None
    club: str | None = None

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = LINE.match(raw)
        if not match:
            continue
        stamp = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(
            microsecond=int(match.group(2)) * 1000
        )
        message = match.group(3)

        if found := SNR.search(message):
            session.self_trigger_bin = int(found.group(1))
            session.self_trigger_snr = float(found.group(2))
        if found := CLUB.search(message):
            club = found.group(1).strip()
        if found := TRIGGER.search(message):
            trigger = Trigger(sequence=int(found.group(1)), time=stamp)
            if last_rearm is not None:
                trigger.since_rearm_s = (stamp - last_rearm).total_seconds()
            session.triggers.append(trigger)
            by_sequence[trigger.sequence] = trigger
            continue
        if (found := ACCEPTED.search(message)) or (found := REJECTED.search(message)):
            trigger = _latest(session.triggers, lambda t: t.verdict is None)
            if trigger is not None:
                trigger.verdict = "accepted" if "accepted" in message else "rejected"
                trigger.peak_mph = float(found.group(1))
                trigger.readings = int(found.group(2))
            continue
        if found := SHOT.search(message):
            club_mph = None if found.group(3) == "N/A" else float(found.group(3))
            shot = Shot(int(found.group(1)), stamp, float(found.group(2)), club_mph, club)
            session.shots.append(shot)
            trigger = _latest(
                session.triggers, lambda t: t.verdict == "accepted" and t.shot is None
            )
            if trigger is not None:
                trigger.shot = shot
            continue
        if REARM.search(message):
            last_rearm = stamp
            trigger = _latest(session.triggers, lambda t: t.rearm_time is None)
            if trigger is not None:
                trigger.rearm_time = stamp
            continue
        if found := IMPACT.search(message):
            pending["impact_to_s_ms"] = float(found.group(1))
        elif found := LAUNCH.search(message):
            pending["launch_deg"] = float(found.group(1))
            pending["launch_status"] = "measured"
        elif found := WITHHELD.search(message):
            pending["launch_status"] = found.group(1)
        elif found := CAPTURE_FAILED.search(message):
            trigger = by_sequence.get(int(found.group(1)))
            if trigger is not None:
                trigger.capture_error = found.group(2).strip()
        elif (found := CAPTURE_DONE.search(message)) and pending:
            trigger = by_sequence.get(int(found.group(1) or found.group(2)))
            if trigger is not None:
                for name, value in pending.items():
                    setattr(trigger, name, value)
            pending = {}
    return session


def _latest(triggers: list[Trigger], wanted) -> Trigger | None:
    for trigger in reversed(triggers):
        if wanted(trigger):
            return trigger
    return None
