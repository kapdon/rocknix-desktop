#!/bin/bash
# Download the versioned desktop bundle; never write the ROCKNIX root image.
set -Eeuo pipefail

VERSION=development
REPOSITORY=kapdon/rocknix-desktop
ASSET=rocknix-sway-rp6-arm64.tar.xz
BASE=/storage/.local/share/rocknix-xfce

fail() { printf 'Install failed: %s\n' "$*" >&2; exit 1; }

check_install_target() {
  [ ! -L "$BASE" ] || fail 'installation path must not be a symlink'
  [ ! -e "$BASE" ] || {
    [ -d "$BASE" ] && [ "$(realpath "$BASE")" = "$BASE" ] || fail 'invalid installation path'
    [ -f "$BASE/.home-retained" ] && [ ! -L "$BASE/.home-retained" ] ||
      fail 'existing installation or unknown directory; uninstall first'
    local path name
    while IFS= read -r -d '' path; do
      name=${path##*/}
      case "$name" in
        home|logs) [ -d "$path" ] && [ ! -L "$path" ] || fail "invalid retained directory: $path" ;;
        graphics-mode|.home-retained) [ -f "$path" ] && [ ! -L "$path" ] || fail "invalid retained file: $path" ;;
        *) fail "unexpected retained content: $path" ;;
      esac
    done < <(find "$BASE" -mindepth 1 -maxdepth 1 -print0)
  }
}

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
  for command in curl jq sha256sum tar xz df mktemp systemctl flock realpath find; do
    command -v "$command" >/dev/null || fail "missing command: $command"
  done
  check_install_target
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
  local check=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --help|-h)
        printf 'Usage: bash install.sh [--release TAG] [--check]\nDefault channel: development. Fresh install or retained-home reinstall; no in-place upgrades.\n'
        return ;;
      --check) check=1; shift ;;
      --release)
        [ "$#" -ge 2 ] || fail 'missing release tag'
        [[ "$2" = development || "$2" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-alpha\.[0-9]+$ ]] || fail 'invalid release tag'
        VERSION=$2
        shift 2 ;;
      *) fail "unknown option: $1" ;;
    esac
  done
  check_device
  if [ "$check" = 1 ]; then
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
  ASSET="rocknix-sway-rp6-arm64-$revision.tar.xz"
  [ "$(jq -er '.asset' "$STAGING/latest.json")" = "$ASSET" ] || fail 'invalid build filename'
  printf 'Downloading ROCKNIX Desktop (Sway) %s (%s)\n' "$VERSION" "$revision"
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
