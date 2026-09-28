#!/bin/bash
# Exercise the real selection/prompt/dispatch path with an isolated fake device.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source ./install.sh
scratch=$(mktemp -d)
WORKSPACE="$scratch/workspace"
trap 'rm -rf -- "$scratch"' EXIT
export FLOW_LOG="$scratch/actions"
candidate=1111111111111111111111111111111111111111
previous=2222222222222222222222222222222222222222
mkdir -p "$scratch/bundle"
printf 'commit=%s\n' "$candidate" >"$scratch/bundle/build-info"
printf 'echo install >>"$FLOW_LOG"\n' >"$scratch/bundle/install-device.sh"
printf 'flock -n 8 || exit 77\necho update >>"$FLOW_LOG"\n' >"$scratch/bundle/upgrade.sh"
tar -cJf "$scratch/payload.tar.xz" -C "$scratch/bundle" .
hash=$(sha256sum "$scratch/payload.tar.xz"); hash=${hash%% *}
printf '{"commit":"%s","sha256":"%s","asset":"rocknix-sway-rp6-arm64-%s.tar.xz"}\n' \
  "$candidate" "$hash" "$candidate" >"$scratch/latest.json"
check_device() { INSTALLED_REVISION=${fixture_revision:-}; }
acquire_install_lock() {
  exec 9>"$scratch/lock"
  flock -n 9
  # A separately opened descriptor must be able to lock in the update child.
  exec 8>"$scratch/lock"
}
mktemp() { command mktemp -d "$scratch/staging.XXXXXX"; }
curl() {
  local url='' destination=''
  while [ "$#" -gt 0 ]; do
    case "$1" in
      https://*) url=$1; shift ;;
      -o) destination=$2; shift 2 ;;
      *) shift ;;
    esac
  done
  printf '%s\n' "$url" >>"$scratch/downloads"
  case "$url" in
    */latest.json) cp "$scratch/latest.json" "$destination" ;;
    */rocknix-sway-rp6-arm64-"$candidate".tar.xz) cp "$scratch/payload.tar.xz" "$destination" ;;
    *) return 1 ;;
  esac
}
fixture_revision=$candidate
output=$(main --release v0.2.0-alpha.1)
grep -q 'Already up to date' <<<"$output"
test ! -e "$FLOW_LOG"
test "$(wc -l <"$scratch/downloads")" = 1
fixture_revision=''
output=$(main --release v0.2.0-alpha.1 <<<n)
grep -q 'Install Desktop Mode?' <<<"$output"
grep -q Cancelled <<<"$output"
test ! -e "$FLOW_LOG"
output=$(main --release v0.2.0-alpha.1 </dev/null)
grep -q Cancelled <<<"$output"
test ! -e "$FLOW_LOG"
output=$(main --release v0.2.0-alpha.1 <<<y)
grep -Fxq install "$FLOW_LOG"
fixture_revision=$previous
output=$(main --release v0.2.0-alpha.1 <<<n)
grep -q 'Update Desktop Mode?' <<<"$output"
test "$(wc -l <"$FLOW_LOG")" = 1
output=$(main --release v0.2.0-alpha.1 <<<yes)
grep -Fxq update "$FLOW_LOG"
output=$(main --release v0.2.0-alpha.1 --yes </dev/null)
test "$(wc -l <"$FLOW_LOG")" = 3
if (main --check --yes) >/dev/null 2>&1; then exit 1; fi
printf 'PASS: install/update prompts, cancellation, EOF, same revision, automation and lock handoff\n'

# Real target recognition still rejects unsafe or incomplete installations.
BASE="$scratch/installed"
mkdir -p "$BASE"/{home,rootfs/etc,bin,input,integration}
printf 'ROCKNIX_XFCE_RUNTIME=1\n' >"$BASE/rootfs/etc/rocknix-xfce-release"
printf 'commit=%s\n' "$previous" >"$BASE/build-info"
detect_installation
test "$INSTALLED_REVISION" = "$previous"
touch "$BASE/.upgrade-in-progress"
if (detect_installation) >/dev/null 2>&1; then exit 1; fi
rm "$BASE/.upgrade-in-progress"
mv "$BASE/home" "$scratch/home"
ln -s "$scratch/home" "$BASE/home"
if (detect_installation) >/dev/null 2>&1; then exit 1; fi
printf 'PASS: installed version detection and unsafe-target rejection\n'
