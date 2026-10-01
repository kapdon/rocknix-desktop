#!/bin/bash
# Exercise the real selection/prompt/dispatch path with an isolated fake device.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source ./install.sh
read_confirmation() { read -r "$1"; } # Dispatch fixtures; real TTY behavior is tested separately.
scratch=$(mktemp -d)
WORKSPACE="$scratch/workspace"
trap 'rm -rf -- "$scratch"' EXIT
export FLOW_LOG="$scratch/actions"
candidate=1111111111111111111111111111111111111111
previous=2222222222222222222222222222222222222222
mkdir -p "$scratch/bundle/payload/systemd" "$scratch/bundle/payload/bin" "$scratch/bundle/rootfs/etc"
printf 'print("fixture device profile")\n' >"$scratch/bundle/payload/bin/rocknix-device-profile"
printf 'canonical service\n' >"$scratch/bundle/payload/systemd/rocknix-desktop.service"
printf 'ROCKNIX_DESKTOP_RUNTIME=1\nROCKNIX_LXC_RUNTIME=1\n' >"$scratch/bundle/rootfs/etc/rocknix-desktop-release"
printf 'commit=%s\n' "$candidate" >"$scratch/bundle/build-info"
printf 'echo install >>"$FLOW_LOG"\n' >"$scratch/bundle/install-device.sh"
printf 'flock -n 8 || exit 77\necho update >>"$FLOW_LOG"\n' >"$scratch/bundle/upgrade.sh"
tar -cJf "$scratch/payload.tar.xz" -C "$scratch/bundle" .
hash=$(sha256sum "$scratch/payload.tar.xz"); hash=${hash%% *}
printf '{"commit":"%s","sha256":"%s","asset":"rocknix-desktop-rp6-arm64-%s.tar.xz"}\n' \
  "$candidate" "$hash" "$candidate" >"$scratch/latest.json"
check_device() { :; }
detect_installation() {
  INSTALLED_REVISION=${fixture_revision:-}
  INSTALL_STATUS=${fixture_status:-healthy}
  [ -n "$INSTALLED_REVISION" ] || INSTALL_STATUS=${fixture_status:-absent}
  INSTALL_REASON='fixture health result'
}
check_power() { return 0; }
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
    */rocknix-desktop-rp6-arm64-"$candidate"*.tar.xz) cp "$scratch/payload.tar.xz" "$destination" ;;
    *) return 1 ;;
  esac
}
fixture_revision=$candidate
mkdir -p "$WORKSPACE/managed/host"
cp "$scratch/latest.json" "$WORKSPACE/managed/host/release-info.json"
output=$(main --release v0.2.0-alpha.1)
grep -q 'Already up to date' <<<"$output"
test ! -e "$FLOW_LOG"
test "$(wc -l <"$scratch/downloads")" = 2
output=$(main --release v0.2.0-alpha.1 --install --yes)
test "$(cat "$FLOW_LOG")" = install
rm "$FLOW_LOG"
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

fixture_status=invalid
if (main --update --yes) >/dev/null 2>&1; then exit 1; fi
output=$(main <<<n)
grep -q 'Installed state: invalid' <<<"$output"
grep -q 'Install Desktop Mode?' <<<"$output"
grep -q 'replaces Desktop apps, home' <<<"$output"
output=$(main --install --yes)
test "$(tail -n 1 "$FLOW_LOG")" = install
if (main --install --update) >/dev/null 2>&1; then exit 1; fi
printf 'PASS: invalid installs cannot Update; explicit Install accepts same-version replacement\n'

# A manually rebuilt commit is a new rolling build when its checksum changes.
fixture_status=healthy
fixture_revision=$candidate
printf '{"commit":"%s","sha256":"%064d"}\n' "$candidate" 0 >"$WORKSPACE/managed/host/release-info.json"
jq --arg asset "rocknix-desktop-rp6-arm64-$candidate-r123a2.tar.xz" \
  '.asset = $asset' "$scratch/latest.json" >"$scratch/rebuild.json"
mv "$scratch/rebuild.json" "$scratch/latest.json"
output=$(main --yes)
test "$(tail -n 1 "$FLOW_LOG")" = update
grep -q -- '-r123a2.tar.xz' "$scratch/downloads"
for asset in "../escape.tar.xz" "rocknix-desktop-rp6-arm64-$candidate-r123a2.tar.xz/extra"; do
  jq --arg asset "$asset" '.asset = $asset' "$scratch/latest.json" >"$scratch/bad.json"
  mv "$scratch/bad.json" "$scratch/latest.json"
  downloads_before=$(wc -l <"$scratch/downloads")
  actions_before=$(cat "$FLOW_LOG")
  if (main --yes) >"$scratch/bad-result" 2>&1; then exit 1; fi
  grep -q 'invalid build filename' "$scratch/bad-result"
  test "$(wc -l <"$scratch/downloads")" = "$((downloads_before + 1))"
  test "$(cat "$FLOW_LOG")" = "$actions_before"
done
printf 'PASS: rebuilt rolling artifacts update; unsafe/unsupported filenames refused before bundle download\n'
