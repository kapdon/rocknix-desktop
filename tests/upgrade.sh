#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
bash upgrade.sh --help >/dev/null
if bash upgrade.sh --bundle >/dev/null 2>&1; then exit 1; fi
if bash upgrade.sh --unknown >/dev/null 2>&1; then exit 1; fi
source ./upgrade.sh
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
BASE="$scratch/base"
WORK="$scratch/recovery"
mkdir -p "$BASE/home" "$WORK/old" "$WORK/failed"
printf 'personal\n' >"$BASE/home/document"
printf 'old runtime\n' >"$WORK/old/rootfs"
printf 'failed runtime\n' >"$BASE/rootfs"
printf 'new file\n' >"$BASE/upgrade.sh"
MUTATING=1 MARKED=1
TOUCHED=("$BASE/rootfs" "$BASE/upgrade.sh")
systemctl() { return 0; }
sync() { return 0; }
if (trap finish_upgrade EXIT; exit 1); then exit 1; fi
test "$(cat "$BASE/rootfs")" = 'old runtime'
test "$(cat "$BASE/home/document")" = personal
test "$(cat "$WORK/failed/rootfs")" = 'failed runtime'
test ! -e "$BASE/upgrade.sh"
test ! -e "$BASE/.upgrade-in-progress"
test "$(cat "$WORK/state")" = rolled-back
printf 'PASS: failed activation restores runtime without replacing home\n'
