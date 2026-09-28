#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source ./install.sh
source ./uninstall.sh
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
BASE="$scratch/desktop"
check_install_target
mkdir -p "$BASE/home/.config" "$BASE/rootfs" "$BASE/logs" "$BASE/bin"
printf 'personal file\n' >"$BASE/home/document"
printf 'custom setting\n' >"$BASE/home/.config/settings"
printf 'shm\n' >"$BASE/graphics-mode"
printf 'runtime\n' >"$BASE/rootfs/test"
before=$(stat -c '%d:%i' "$BASE/home")
if (check_install_target) >/dev/null 2>&1; then
  printf 'FAIL: active installation accepted\n' >&2; exit 1
fi
mkdir "$scratch/recovery"
archive_runtime "$scratch/recovery"
test "$(stat -c '%d:%i' "$BASE/home")" = "$before"
test "$(cat "$BASE/home/document")" = 'personal file'
test "$(cat "$BASE/home/.config/settings")" = 'custom setting'
test "$(cat "$BASE/graphics-mode")" = shm
test -f "$scratch/recovery/installation/rootfs/test"
test ! -e "$scratch/recovery/installation/home"
check_install_target
touch "$BASE/unknown"
if (check_install_target) >/dev/null 2>&1; then
  printf 'FAIL: unknown content accepted\n' >&2; exit 1
fi
rm "$BASE/unknown"
mv "$BASE/home" "$scratch/personal-home"
ln -s "$scratch/personal-home" "$BASE/home"
if (check_install_target) >/dev/null 2>&1; then
  printf 'FAIL: symlinked home accepted\n' >&2; exit 1
fi
printf 'PASS: home stays in place; retained reinstall and unsafe targets checked\n'

source rootfs-overlay/usr/local/bin/rocknix-home-integration
mkdir -p "$scratch/defaults/Desktop"
cp rootfs-overlay/usr/share/applications/rocknix-{return,keyboard,about}.desktop "$scratch/defaults/Desktop/"
personal="$scratch/personal-home"
refresh_home_integration "$scratch/defaults" "$personal"
printf '\n# old customization\n' >>"$personal/Desktop/rocknix-return.desktop"
refresh_home_integration "$scratch/defaults" "$personal"
cmp "$scratch/defaults/Desktop/rocknix-return.desktop" "$personal/Desktop/rocknix-return.desktop"
backups=("$personal/Desktop/rocknix-return.desktop.before-refresh."*)
test "${#backups[@]}" = 1
grep -q 'old customization' "${backups[0]}"
refresh_home_integration "$scratch/defaults" "$personal"
backups=("$personal/Desktop/rocknix-return.desktop.before-refresh."*)
test "${#backups[@]}" = 1
printf 'personal collision\n' >"$personal/Desktop/rocknix-return.desktop"
refresh_home_integration "$scratch/defaults" "$personal"
test "$(cat "$personal/Desktop/rocknix-return.desktop")" = 'personal collision'
rm "$personal/Desktop/rocknix-return.desktop"
ln -s "$personal/document" "$personal/Desktop/rocknix-return.desktop"
refresh_home_integration "$scratch/defaults" "$personal"
test "$(cat "$personal/document")" = 'personal file'
test -L "$personal/Desktop/rocknix-return.desktop"
printf 'PASS: managed refresh, backup, idempotency and personal collisions\n'
