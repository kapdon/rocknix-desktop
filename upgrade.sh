#!/bin/bash
# Explicit local-bundle upgrade. Home is never moved or restored by rollback.
set -Eeuo pipefail
BASE=/storage/.local/share/rocknix-xfce
UNIT=/storage/.config/system.d/xfce-desktop.service
HOOK=/storage/.config/autostart/999-rocknix-xfce
ENTRY='/storage/.config/modules/Desktop Mode.sh'
COMPONENTS=(rootfs bin input integration README.md uninstall.sh upgrade.sh build-info install-info)
fail() { printf 'Upgrade failed: %s\n' "$*" >&2; exit 1; }

check_idle() {
  ! systemctl is-active --quiet xfce-desktop.service || fail 'exit Desktop Mode first'
  systemctl is-active --quiet sway.service || fail 'Sway is not active'
  systemctl is-active --quiet essway.service || fail 'EmulationStation is not active'
  if awk -v base="$BASE" '$5 == base || index($5, base "/") == 1 {found=1} END {exit !found}' /proc/self/mountinfo; then
    fail 'runtime still has mounts'
  fi
}

finish_upgrade() {
  local rc=$? name path rollback_failed=0
  trap - EXIT INT TERM
  if [ "$MUTATING" = 1 ]; then
    set +e
    printf '%s\n' "$WORK" >"$BASE/.upgrade-in-progress"
    printf 'Activation failed; restoring old runtime. Recovery: %s\n' "$WORK" >&2
    # Each touched destination either has an old copy or was absent originally.
    for path in "${TOUCHED[@]}"; do
      name=${path##*/}
      if [ -e "$path" ] || [ -L "$path" ]; then
        mv -- "$path" "$WORK/failed/$name" || rollback_failed=1
      fi
      if [ -e "$WORK/old/$name" ] || [ -L "$WORK/old/$name" ]; then
        mv -- "$WORK/old/$name" "$path" || rollback_failed=1
      fi
    done
    systemctl daemon-reload || rollback_failed=1
    if [ "$rollback_failed" = 0 ]; then
      rm -f "$BASE/.upgrade-in-progress"
      printf 'rolled-back\n' >"$WORK/state"
    else
      printf 'Rollback incomplete; marker retained. Inspect %s\n' "$WORK" >&2
    fi
    sync
  elif [ "$MARKED" = 1 ]; then
    rm -f "$BASE/.upgrade-in-progress"
  fi
  [ -z "$WORK" ] || printf 'Upgrade staging/recovery retained at %s\n' "$WORK"
  exit "$rc"
}

main() {
  local bundle='' expected='' mode='' actual revision old_revision name path available required
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --bundle|--sha256)
        [ "$#" -ge 2 ] || fail "missing value for $1"
        if [ "$1" = --bundle ]; then bundle=$2; else expected=$2; fi
        shift 2 ;;
      --yes|--check) [ -z "$mode" ] || fail 'choose --check or --yes'; mode=$1; shift ;;
      --help|-h) printf 'Usage: bash upgrade.sh --bundle FILE --sha256 SHA256 --check|--yes\n'; return ;;
      *) fail "unknown option: $1" ;;
    esac
  done
  [ -n "$mode" ] && [ -f "$bundle" ] || fail 'provide a bundle and --check or --yes'
  [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || fail 'provide the trusted bundle SHA-256'
  [ "$(id -u)" = 0 ] || fail 'run on the RP6 as root'
  . /etc/os-release
  [ "${OS_NAME:-}" = ROCKNIX ] && [ "$(uname -m)" = aarch64 ] || fail 'requires ARM64 ROCKNIX'
  [ "$(tr -d '\000' </proc/device-tree/model)" = 'Retroid Pocket 6' ] || fail 'unsupported device'
  for name in flock realpath sha256sum tar xz systemctl systemd-analyze mktemp du df cmp; do
    command -v "$name" >/dev/null || fail "missing command: $name"
  done
  exec 9>/storage/.rocknix-xfce-install.lock
  flock -n 9 || fail 'another install, uninstall or upgrade is running'
  [ -d "$BASE" ] && [ "$(realpath "$BASE")" = "$BASE" ] || fail 'unrecognized installation path'
  [ ! -e "$BASE/.upgrade-in-progress" ] && [ ! -L "$BASE/.upgrade-in-progress" ] || fail 'unfinished upgrade requires recovery'
  [ ! -e "$BASE/.home-retained" ] || fail 'partial installation requires recovery'
  for name in home rootfs bin input integration; do
    [ -d "$BASE/$name" ] && [ ! -L "$BASE/$name" ] || fail "invalid installed $name"
  done
  [ -f "$BASE/rootfs/etc/rocknix-xfce-release" ] || fail 'runtime marker missing'
  for path in "$UNIT" "$HOOK" "$ENTRY"; do
    [ -f "$path" ] && [ "$(realpath "$path")" = "$path" ] || fail "invalid integration: $path"
  done
  grep -Fq "ExecStopPost=$BASE/bin/restore-emulationstation" "$UNIT" || fail 'unrecognized service'
  cmp -s "$HOOK" "$BASE/integration/999-rocknix-xfce" || fail 'modified boot hook'
  cmp -s "$ENTRY" "$BASE/integration/Desktop Mode.sh" || fail 'modified Tools launcher'
  check_idle
  actual=$(sha256sum "$bundle"); [ "${actual%% *}" = "$expected" ] || fail 'bundle checksum mismatch'
  old_revision=$(sed -n 's/^commit=//p' "$BASE/build-info")
  [[ "$old_revision" =~ ^[0-9a-f]{40}$ ]] || fail 'installed build metadata missing; explicit legacy migration needed'
  required=$((4194304 + $(du -sk "$BASE/home" | awk '{print $1}')))
  available=$(df -Pk /storage | awk 'END {print $4}')
  [ "$available" -ge "$required" ] || fail 'need 4 GiB plus space for a home backup'
  WORK=$(mktemp -d /storage/.local/share/rocknix-xfce-upgrade.XXXXXX)
  MUTATING=0 MARKED=0
  TOUCHED=()
  trap finish_upgrade EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  mkdir "$WORK/bundle" "$WORK/old" "$WORK/failed"
  # Bundles contain executable root code: checksums establish integrity, not trust.
  tar -xJf "$bundle" -C "$WORK/bundle"
  local incoming="$WORK/bundle"
  revision=$(sed -n 's/^commit=//p' "$incoming/build-info")
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]] || fail 'invalid candidate revision'
  cmp -s "$incoming/build-info" "$incoming/rootfs/etc/rocknix-xfce-build-info" || fail 'candidate provenance mismatch'
  grep -Fxq RUNTIME_ARCH=aarch64 "$incoming/rootfs/etc/rocknix-xfce-release" || fail 'invalid runtime marker'
  for name in Xorg xfce4-session xfwm4 xfce4-panel; do
    [ -x "$incoming/rootfs/usr/bin/$name" ] || fail "candidate missing $name"
  done
  for name in preflight launch-xfce restore-emulationstation; do
    [ -x "$incoming/payload/bin/$name" ] || fail "candidate missing $name"
  done
  for path in "$incoming/payload/systemd/xfce-desktop.service" "$incoming/payload/input/desktop.yaml" \
    "$incoming/payload/integration/Desktop Mode.sh" "$incoming/payload/integration/999-rocknix-xfce" \
    "$incoming/upgrade.sh" "$incoming/uninstall.sh" "$incoming/README.md"; do
    [ -f "$path" ] && [ ! -L "$path" ] || fail "candidate missing regular file: $path"
  done
  printf 'Installed: %s\nCandidate: %s\n' "$old_revision" "$revision"
  if [ "$old_revision" = "$revision" ]; then printf 'Already installed; no changes made.\n'; return; fi
  if [ "$mode" = --check ]; then printf 'Upgrade checks passed; installation unchanged.\n'; return; fi
  check_idle
  tar -cpf "$WORK/home-before.tar" -C "$BASE" home
  cp -a "$BASE/install-info" "$incoming/install-info"
  printf 'upgraded=%s\nprevious_commit=%s\n' "$(date -Is)" "$old_revision" >>"$incoming/install-info"
  printf '%s\n' "$WORK" >"$BASE/.upgrade-in-progress"
  MARKED=1
  check_idle
  printf 'activating\n' >"$WORK/state"
  sync
  MUTATING=1
  # Disable boot/Tools integration before swapping managed components.
  for path in "$HOOK" "$ENTRY" "$UNIT"; do
    name=${path##*/}
    mv -- "$path" "$WORK/old/$name"
    TOUCHED+=("$path")
  done
  for name in "${COMPONENTS[@]}"; do
    path="$BASE/$name"
    if [ -e "$path" ] || [ -L "$path" ]; then mv -- "$path" "$WORK/old/$name"; fi
    TOUCHED+=("$path")
    case "$name" in
      bin|input|integration) cp -a "$incoming/payload/$name" "$path" ;;
      rootfs) mv "$incoming/rootfs" "$path" ;;
      *) cp -a "$incoming/$name" "$path" ;;
    esac
  done
  cp "$incoming/payload/systemd/xfce-desktop.service" "$UNIT"
  cp "$BASE/integration/999-rocknix-xfce" "$HOOK"
  cp "$BASE/integration/Desktop Mode.sh" "$ENTRY"
  chmod 0755 "$BASE/bin/"* "$BASE/integration/"* "$HOOK" "$ENTRY"
  chmod 0644 "$UNIT" "$BASE/input/"*
  systemctl daemon-reload
  systemd-analyze verify "$UNIT"
  # Remove the launch guard for final preflight, while the shared lock stays held.
  rm "$BASE/.upgrade-in-progress"
  "$BASE/bin/preflight"
  printf 'complete\n' >"$WORK/state"
  sync
  MUTATING=0 MARKED=0
  printf 'Upgrade complete. Home unchanged; open Tools > Desktop Mode.\n'
}

if [[ "${BASH_SOURCE[0]}" = "$0" ]]; then main "$@"; fi
