#!/usr/bin/env bash
# Can azimuth session, automatic: you are only asked when the can has to move.
#
#   bash run_session.sh --line-m 1.285
#   bash run_session.sh --line-m 1.285 --marks "61 122 183 245 308 372 438 506"
#
# Each position: you place the can (or clear the hallway) and press Enter. The
# script then runs l3dump with one warm-up freeze plus five, SETTLE_S apart,
# sets the warm-up aside, checks that every kept capture is full size and redoes
# the position by itself if not. Finished positions are skipped, so a dropped
# SSH session can just rerun the same command. At the end it runs the analysis.
# Kiosk stopped. DRY_RUN=1 writes fake captures to test the flow without a radar.
set -u

LINE_M=""
HEIGHT_M="0.0525"
MARKS="61 122 183 245 308 372 438 506"
DIR="$HOME/bench/can_az_$(date +%Y%m%d)"
FREEZES=5
SETTLE_S=7
FULL_BYTES=732824
TRIES=2

while [ $# -gt 0 ]; do
  case "$1" in
    --line-m) LINE_M=$2; shift 2 ;;
    --height-m) HEIGHT_M=$2; shift 2 ;;
    --marks) MARKS=$2; shift 2 ;;
    --dir) DIR=$2; shift 2 ;;
    *) echo "unknown option: $1"; exit 2 ;;
  esac
done
[ -n "$LINE_M" ] || { echo "--line-m is required: enclosure front to the tape line, in metres"; exit 2; }

OF="$HOME/openflight/.venv/bin/python"
L3DUMP="$HOME/openflight/scripts/iwr6843/l3dump.py"
CFG="$HOME/openflight/config/iwr6843_l3dump_wide_24f2ms_53bin_iq16_window_hann.cfg"
CHECK="$HOME/openflight/scripts/iwr6843/azimuth_check.py"
TOOLS="https://raw.githubusercontent.com/HuggeK/OpenFlight-Radar-Workbench/assets/issue-2-diagrams/tools/can-azimuth"

mkdir -p "$DIR" && cd "$DIR" || exit 1
LOG="$DIR/session.log"
log() { echo "$(date '+%F %T') $*" | tee -a "$LOG"; }

# Capture order: empties and boresights at start, middle and end; marks
# alternate right and left from small to wide, split in two halves.
set -- $MARKS
half=$(( ($# + 1) / 2 ))
first="" second=""
i=0
for m in "$@"; do
  i=$((i + 1))
  if [ $i -le $half ]; then first="$first r$m l$m"; else second="$second r$m l$m"; fi
done
ORDER="e1 b1$first e2 b2$second b3 e3"
TOTAL=$(echo $ORDER | wc -w)

describe() {
  case "$1" in
    e*) echo "take the can OUT of the hallway; nobody in front of the radar" ;;
    b*) echo "can on the 0 mark (boresight)" ;;
    r*) echo "can ${1#r} mm RIGHT of the 0 mark (seen from behind the radar)" ;;
    l*) echo "can ${1#l} mm LEFT of the 0 mark (seen from behind the radar)" ;;
  esac
}
full_count() { find "$1" -maxdepth 1 -name '*.l3dump' -size "${FULL_BYTES}c" 2>/dev/null | wc -l; }

capture() {
  local pos=$1
  mkdir -p "$pos/_warmup"
  if [ "${DRY_RUN:-0}" = 1 ]; then
    for k in $(seq 1 $((FREEZES + 1))); do
      truncate -s "$FULL_BYTES" "$pos/iwr6843_dry_$(date +%H%M%S)_00$k.l3dump"
    done
  else
    "$OF" "$L3DUMP" --config "$CFG" --count $((FREEZES + 1)) --settle-s "$SETTLE_S" --out "$pos/" 2>&1 | tee -a "$LOG"
  fi
  local warm
  warm=$(find "$pos" -maxdepth 1 -name '*.l3dump' | sort | head -1)
  [ -n "$warm" ] && mv "$warm" "$pos/_warmup/"
  # Anything short of a full ring is set aside.
  find "$pos" -maxdepth 1 -name '*.l3dump' ! -size "${FULL_BYTES}c" -exec sh -c 'mkdir -p _excluded/short && mv "$1" _excluded/short/' _ {} \;
}

log "session start: dir=$DIR line_m=$LINE_M height_m=$HEIGHT_M marks='$MARKS' freezes=$FREEZES settle_s=$SETTLE_S"
if [ ! -f setup.txt ]; then
  read -r -p "Room temperature in °C (Enter to skip): " ambient
  read -r -p "Tape check: front face 30 cm LEFT of the antenna mark -> 0 mark, mm (Enter to skip): " tape_l
  read -r -p "Tape check: front face 30 cm RIGHT of the antenna mark -> 0 mark, mm (Enter to skip): " tape_r
  printf 'ambient_c=%s\ntape_check_left_mm=%s\ntape_check_right_mm=%s\nline_m=%s\nheight_m=%s\nmarks=%s\n' \
    "$ambient" "$tape_l" "$tape_r" "$LINE_M" "$HEIGHT_M" "$MARKS" > setup.txt
  log "setup: $(tr '\n' ' ' < setup.txt)"
fi

n=0
for pos in $ORDER; do
  n=$((n + 1))
  if [ "$(full_count "$pos")" -ge "$FREEZES" ]; then
    log "[$n/$TOTAL] $pos already has $FREEZES captures, skipping"
    continue
  fi
  printf '\a\n=== [%s/%s] %s: %s\n' "$n" "$TOTAL" "$pos" "$(describe "$pos")"
  read -r -p "Place it, step behind the radar, then press Enter " _
  ok=0
  for try in $(seq 1 $TRIES); do
    if find "$pos" -maxdepth 1 -name '*.l3dump' 2>/dev/null | grep -q .; then
      mkdir -p "_excluded/$pos.try$try"
      find "$pos" -maxdepth 1 -name '*.l3dump' -exec mv {} "_excluded/$pos.try$try/" \;
    fi
    log "[$n/$TOTAL] $pos: capturing (try $try), about $(( (FREEZES + 1) * (SETTLE_S + 7) )) s; stay still"
    capture "$pos"
    got=$(full_count "$pos")
    if [ "$got" -ge "$FREEZES" ]; then ok=1; log "[$n/$TOTAL] $pos: $got full captures"; break; fi
    log "[$n/$TOTAL] $pos: only $got full captures, trying again"
  done
  if [ $ok -ne 1 ]; then
    log "[$n/$TOTAL] $pos: still short after $TRIES tries. Check the radar, then rerun this command to continue."
    exit 1
  fi
done

printf '\a\n'
log "all $TOTAL positions captured; analysing"
for f in build_manifest.py summarise.py; do [ -f "$f" ] || curl -fsSLO "$TOOLS/$f"; done
if [ "${DRY_RUN:-0}" = 1 ]; then
  log "dry run: skipping the analysis"
  exit 0
fi
"$OF" build_manifest.py --line-m "$LINE_M" --height-m "$HEIGHT_M" 2>&1 | tee -a "$LOG"
for e in e1 e2 e3; do
  "$OF" "$CHECK" "manifest_$e.json" --report "report_$e.json" > "check_$e.txt" 2>&1
  sed -n '1,2p' "check_$e.txt" | tee -a "$LOG"
done
for e in e2 e1 e3; do "$OF" summarise.py "$e" 2>&1 | tee "summary_$e.txt" | tee -a "$LOG"; done
log "done. Send the three summaries. Don't run --save until the results pass."
