#!/usr/bin/env bash
# Follow the running OpenFlight kiosk log, filtered to OPS or IWR trigger lines.
# Run in a second SSH terminal while the kiosk runs (Robinante's checks):
#
#   session_tools/log_tails.sh ops        # OPS243 trigger / capture / rearm
#   session_tools/log_tails.sh iwr        # IWR6843 self-trigger / l3dump / rearm
#   session_tools/log_tails.sh iwr FILE   # a specific log instead of the newest
#
# Timeouts are normal. What matters: it captures on a valid swing, stays quiet
# when nothing moves in front of the radars, and rearms (also after a timeout).
# Add "| tee FILE" to keep the filtered stream.

set -euo pipefail

mode="${1:-}"
log="${2:-$(ls -t "$HOME"/openflight_sessions/terminal_logs/kiosk_*.log 2>/dev/null | head -1)}"

case "$mode" in
    ops) pattern='\[TRIGGER\]|\[MONITOR\]|OPS243|rolling.buffer|S!|capture|timeout|rearm|error' ;;
    iwr) pattern='\[IWR6843\]|self.trigger|triggerCfg|l3dump|l3release|rearm|firmware|timeout|error' ;;
    *) echo "usage: $0 ops|iwr [LOG]" >&2; exit 2 ;;
esac

if [ -z "$log" ] || [ ! -f "$log" ]; then
    echo "no kiosk log found; start OpenFlight first or pass LOG" >&2
    exit 1
fi

echo "following $log ($mode)" >&2
tail -n 50 -F "$log" | grep --line-buffered -Ei "$pattern"
