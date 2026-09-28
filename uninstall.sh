#!/bin/bash
# Remove active integration, keeping a recoverable copy outside the install path.
set -Eeuo pipefail
BASE=/storage/.local/share/rocknix-xfce
UNIT=/storage/.config/system.d/xfce-desktop.service
HOOK=/storage/.config/autostart/999-rocknix-xfce
ENTRY='/storage/.config/modules/Desktop Mode.sh'
fail() { printf 'Uninstall failed: %s\n' "$*" >&2; exit 1; }

archive_runtime() {
  local backup=$1 name
  mkdir "$backup/installation"
  # Only managed components move. Personal data never leaves its original path.
  for name in rootfs bin input integration README.md uninstall.sh build-info install-info; do
    if [ -e "$BASE/$name" ] || [ -L "$BASE/$name" ]; then
      mv -- "$BASE/$name" "$backup/installation/$name"
    fi
  done
  [ ! -e "$BASE/.home-retained" ] && [ ! -L "$BASE/.home-retained" ] ||
    fail 'retained-home marker already exists; investigate partial installation'
  printf 'home retained after uninstall\n' >"$BASE/.home-retained"
}

validate() {
  [ "$(id -u)" = 0 ] || fail 'run as root on ROCKNIX'
  . /etc/os-release
  [ "${OS_NAME:-}" = ROCKNIX ] || fail 'this uninstaller requires ROCKNIX'
  for command in realpath flock systemctl mktemp; do
    command -v "$command" >/dev/null || fail "missing command: $command"
  done
  [ -d "$BASE" ] || fail 'no installation found'
  [ "$(realpath "$BASE")" = "$BASE" ] || fail 'refusing a symlinked installation path'
  [ -f "$BASE/rootfs/etc/rocknix-xfce-release" ] || fail 'runtime marker is missing'
  [ ! -e "$BASE/.home-retained" ] && [ ! -L "$BASE/.home-retained" ] ||
    fail 'retained-home marker exists with runtime; investigate partial installation'
  local path
  for path in "$UNIT" "$HOOK" "$ENTRY"; do
    [ -f "$path" ] || fail "integration missing: $path"
    [ "$(realpath "$path")" = "$path" ] || fail "refusing symlink: $path"
  done
  grep -Fq "ExecStopPost=$BASE/bin/restore-emulationstation" "$UNIT" ||
    fail 'unit is not recognized as this project'
  cmp -s "$HOOK" "$BASE/integration/999-rocknix-xfce" || fail 'boot hook was modified'
  # Early test installs can have a newer Tools entry than their stored template.
  # Both files are archived; recognize ownership without discarding modifications.
  grep -Fxq "BASE=$BASE" "$ENTRY" || fail 'Tools entry is not recognized'
  grep -Fq 'systemctl start --no-block xfce-desktop.service' "$ENTRY" ||
    fail 'Tools entry does not launch this project'
}

main() {
  case "${1:-}" in
    --check|--yes) ;;
    ''|--help|-h)
      printf 'Usage: bash uninstall.sh --check | --yes\n'
      printf 'Archives runtime/integration; leaves home, logs and display preference in place.\n'
      return ;;
    *) fail "unknown option: $1" ;;
  esac
  validate
  [ "$1" != --check ] || { printf 'Uninstall checks passed; no changes made.\n'; return; }
  exec 9>/storage/.rocknix-xfce-install.lock
  flock -n 9 || fail 'another installer/uninstaller is running'
  validate
  systemctl stop xfce-desktop.service
  if systemctl is-active --quiet xfce-desktop.service; then
    fail 'desktop did not stop'
  fi
  # Never traverse a live chroot mount into host storage or devices.
  if awk -v base="$BASE" \
      '$5 == base || index($5, base "/") == 1 {found=1} END {exit !found}' /proc/self/mountinfo; then
    fail 'installation still has mounts; leave it intact and investigate'
  fi
  systemctl start sway.service essway.service
  systemctl is-active --quiet sway.service || fail 'Sway did not recover'
  systemctl is-active --quiet essway.service || fail 'frontend did not recover'
  local backup
  backup=$(mktemp -d /storage/.local/share/rocknix-xfce-backup.XXXXXX)
  printf 'Recovery directory: %s\n' "$backup"
  # Move the boot hook first so it cannot recreate the Tools entry on reboot.
  mv "$HOOK" "$backup/999-rocknix-xfce"
  mv "$ENTRY" "$backup/Desktop Mode.sh"
  mv "$UNIT" "$backup/xfce-desktop.service"
  archive_runtime "$backup"
  systemctl daemon-reload
  systemctl reset-failed xfce-desktop.service 2>/dev/null || true
  sync
  printf 'Desktop Mode uninstalled. Runtime recovery copy: %s\n' "$backup"
  printf 'Your home remains at %s/home and will be reused on reinstall.\n' "$BASE"
  printf 'Refresh the EmulationStation game list to remove a cached Tools entry.\n'
}

if [[ "${BASH_SOURCE[0]}" = "$0" ]]; then
  main "$@"
fi
