#!/bin/bash
# Real shell download/extraction/dispatch, with filesystem and network fixtures.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source ./install.sh
read_confirmation() { read -r "$1"; }
scratch=$(mktemp -d)
WORKSPACE="$scratch/workspace"
trap 'rm -rf -- "$scratch"' EXIT
export FLOW_LOG="$scratch/actions"
candidate=1111111111111111111111111111111111111111
previous=2222222222222222222222222222222222222222
mkdir -p "$scratch/bundle/payload/systemd" "$scratch/bundle/payload/bin" "$scratch/bundle/rootfs/etc"
printf 'print("fixture device profile")\n' >"$scratch/bundle/payload/bin/rocknix-device-profile"
printf 'canonical service\n' >"$scratch/bundle/payload/systemd/rocknix-desktop.service"
printf 'ROCKNIX_LXC_RUNTIME=1\n' >"$scratch/bundle/rootfs/etc/rocknix-desktop-release"
printf 'commit=%s\n' "$candidate" >"$scratch/bundle/build-info"
printf '{"commit":"%s","built_at":"2026-10-04T00:00:00Z"}\n' "$candidate" >"$scratch/bundle/release-info.json"
printf 'echo install >>"$FLOW_LOG"\n' >"$scratch/bundle/install-device.sh"
printf 'flock -n 8 || exit 77\necho update >>"$FLOW_LOG"\n' >"$scratch/bundle/upgrade.sh"
tar -cJf "$scratch/$ASSET" -C "$scratch/bundle" .
(cd "$scratch" && sha256sum "$ASSET" >"$ASSET.sha256")
check_device() { :; }
check_power() { :; }
detect_installation() {
  INSTALLED_REVISION=${fixture_revision:-}
  INSTALL_STATUS=${fixture_status:-absent}
  INSTALL_REASON='fixture health result'
}
acquire_install_lock() {
  exec 9>"$scratch/lock"; flock -n 9
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
    */rocknix-desktop-rp6-arm64.tar.xz|*/rocknix-desktop-rp6-arm64.tar.xz.sha256)
      cp "$scratch/${url##*/}" "$destination" ;;
    *) return 1 ;;
  esac
}
fixture_status=absent
output=$(main --dev --yes)
test "$(cat "$FLOW_LOG")" = install
test "$(wc -l <"$scratch/downloads")" = 2
! grep -qE 'api.github|latest.json|\.py$' "$scratch/downloads"
grep -q '/download/development/' "$scratch/downloads"
fixture_status=healthy; fixture_revision=$previous
output=$(main --release v0.2.0 --yes)
test "$(tail -n 1 "$FLOW_LOG")" = update
grep -q '/download/v0.2.0/' "$scratch/downloads"
fixture_revision=$candidate
output=$(main --yes)
grep -q 'Already up to date' <<<"$output"
grep -q '/releases/latest/download/' "$scratch/downloads"
fixture_revision=$previous
: >"$FLOW_LOG"
output=$(main --dev <<<n)
grep -q Cancelled <<<"$output"
test ! -s "$FLOW_LOG"
if (main --dev --release v0.2.0 --check) >/dev/null 2>&1; then exit 1; fi
if (main --release '../escape' --check) >/dev/null 2>&1; then exit 1; fi
printf 'corruption' >>"$scratch/$ASSET"
if (main --dev --yes) >"$scratch/failure" 2>&1; then exit 1; fi
grep -q 'bundle checksum mismatch' "$scratch/failure"
test ! -s "$FLOW_LOG"
printf 'PASS: fixed release URLs, only tar/checksum downloads, CI metadata, install/update/no-op/consent and corrupt archive rejection\n'
