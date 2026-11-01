#!/usr/bin/env bash
# Stamp what OpenFlight build a session ran, before the first shot.
#
#   session_tools/build_info.sh studio     # -> ~/openflight_sessions/studio-build-info.txt
#
# Also saves uncommitted changes as a patch next to it.

set -uo pipefail

name="${1:-session}"
repo="${OPENFLIGHT_DIR:-$HOME/openflight}"
out="$HOME/openflight_sessions"
mkdir -p "$out"
cd "$repo" || exit 1

{
    date -Is
    hostname
    git status --short --branch
    git rev-parse HEAD
    git log --oneline "@{upstream}..HEAD" 2>/dev/null
    command -v uv >/dev/null && uv --version
    .venv/bin/python --version
    uname -a
    cat /etc/os-release
    sha256sum config/*.cfg
    timedatectl | grep -E "Local time|synchronized"
} > "$out/$name-build-info.txt" 2>&1
git diff --binary HEAD > "$out/$name-local-changes.patch"

grep -E "synchronized|^##" "$out/$name-build-info.txt"
echo "wrote $out/$name-build-info.txt and $name-local-changes.patch"
