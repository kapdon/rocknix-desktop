#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$scratch/personal-home"
printf 'personal file\n' >"$scratch/personal-home/document"
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
