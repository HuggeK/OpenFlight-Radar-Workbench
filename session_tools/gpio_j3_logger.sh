#!/usr/bin/env bash
# Log OPS243 J3 pin 1 (alert output) edges with kernel timestamps.
#
# Wiring used on 2026-11-01: OPS243-A J3 pin 1 -> Pi physical pin 12 (GPIO18).
# In rolling-buffer mode the line rises ~0.17 ms after the OPS receives S! and
# falls when its post-trigger capture closes (S#24 at 30 kS/s: ~34 ms).
# Timestamps are CLOCK_MONOTONIC, the clock OpenFlight's camera metadata uses
# for trigger_host_timestamp_ns, so the two can be paired afterwards.
#
#   session_tools/gpio_j3_logger.sh          # background, prints the log path
#   session_tools/gpio_j3_logger.sh 17       # another GPIO line
#   pkill -x gpiomon                         # stop

set -euo pipefail

line="${1:-18}"
out="$HOME/openflight_sessions/ops_j3_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$out")"
setsid nohup gpiomon -c gpiochip0 -e both -F "%S %E" "$line" > "$out" 2>&1 < /dev/null &
sleep 1
pgrep -x gpiomon >/dev/null || { echo "gpiomon did not start; see $out" >&2; exit 1; }
echo "$out"
