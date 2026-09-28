#!/bin/bash
# Download the versioned desktop bundle; never write the ROCKNIX root image.
set -Eeuo pipefail

VERSION=development
REPOSITORY=kapdon/rocknix-xfce
ASSET=rocknix-xfce-rp6-arm64.tar.xz
BASE=/storage/.local/share/rocknix-xfce

fail() { printf 'Install failed: %s\n' "$*" >&2; exit 1; }

check_device() {
  [ "$(id -u)" = 0 ] || fail 'run as root on the ROCKNIX device'
  [ -r /etc/os-release ] || fail 'missing OS identification'
  . /etc/os-release
  [ "${OS_NAME:-}" = ROCKNIX ] || fail 'this installer requires ROCKNIX'
  [ "$(uname -m)" = aarch64 ] || fail 'only aarch64 is supported'
  local model
  model=$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)
  [ "$model" = 'Retroid Pocket 6' ] || fail "unsupported device: ${model:-unknown}"
  [ -d /storage ] && [ -w /storage ] || fail '/storage must be writable'
  for command in curl jq sha256sum tar xz df mktemp systemctl flock; do
    command -v "$command" >/dev/null || fail "missing command: $command"
  done
  [ ! -e "$BASE" ] || fail "$BASE already exists; updates are not supported"
  systemctl is-active --quiet xfce-desktop.service && fail 'Desktop Mode is active'
  [ "$(df -Pk /storage | awk 'END {print $4}')" -ge 4194304 ] ||
    fail 'at least 4 GiB free on /storage is required'
}

verify_bundle() {
  local directory=$1 expected actual
  expected=$(awk 'NR == 1 {print $1}' "$directory/$ASSET.sha256")
  [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || fail 'invalid SHA-256 checksum'
  actual=$(sha256sum "$directory/$ASSET")
  [ "${actual%% *}" = "$expected" ] || fail 'bundle checksum mismatch'
}

main() {
  case "${1:-}" in
    --help|-h)
      printf 'Usage: bash install.sh [--check]\nFresh RP6 ROCKNIX installs only.\n'
      return ;;
    ''|--check) ;;
    *) fail "unknown option: $1" ;;
  esac
  check_device
  if [ "${1:-}" = --check ]; then
    printf 'Device checks passed. No changes made.\n'
    return
  fi
  # Lock before downloading, and recheck after acquiring it.
  exec 9>/storage/.rocknix-xfce-install.lock
  flock -n 9 || fail 'another installation is running'
  check_device
  STAGING=$(mktemp -d /storage/.rocknix-xfce-install.XXXXXX)
  trap 'rc=$?; if [ "$rc" = 0 ]; then rm -rf -- "$STAGING"; else
    printf "Installation stopped. Diagnostics/staging retained at %s\n" "$STAGING" >&2; fi' EXIT
  local url="https://github.com/$REPOSITORY/releases/download/$VERSION"
  curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 \
    "$url/latest.json" -o "$STAGING/latest.json"
  local revision expected
  revision=$(jq -er '.commit' "$STAGING/latest.json")
  expected=$(jq -er '.sha256' "$STAGING/latest.json")
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]] || fail 'invalid build commit'
  [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || fail 'invalid build checksum'
  ASSET="rocknix-xfce-rp6-arm64-$revision.tar.xz"
  [ "$(jq -er '.asset' "$STAGING/latest.json")" = "$ASSET" ] || fail 'invalid build filename'
  printf 'Downloading ROCKNIX XFCE %s (%s)\n' "$VERSION" "$revision"
  curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 \
    "$url/$ASSET" -o "$STAGING/$ASSET"
  printf '%s  %s\n' "$expected" "$ASSET" >"$STAGING/$ASSET.sha256"
  verify_bundle "$STAGING"
  mkdir "$STAGING/bundle"
  tar -xJf "$STAGING/$ASSET" -C "$STAGING/bundle"
  grep -Fxq "commit=$revision" "$STAGING/bundle/build-info" || fail 'bundle provenance mismatch'
  bash "$STAGING/bundle/install-device.sh"
  printf '\nRefresh the EmulationStation game list, then open Tools > Desktop Mode.\n'
}

if [[ "${BASH_SOURCE[0]}" = "$0" ]]; then
  main "$@"
fi
