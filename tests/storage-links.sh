#!/bin/bash
set -Eeuo pipefail
source rootfs-overlay/usr/local/bin/rocknix-home-integration
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
mkdir "$scratch/home"
ln -s /storage/roms "$scratch/home/ROCKNIX ROMs"
refresh_storage_links "$scratch/home"
test "$(readlink "$scratch/home/ROCKNIX ROMs")" = /storage/roms
test "$(readlink "$scratch/home/ROCKNIX Desktop")" = /storage/Desktop
test "$(readlink "$scratch/home/ROCKNIX Games")" = /storage/games-internal
test "$(readlink "$scratch/home/ROCKNIX External Games")" = /storage/games-external
refresh_storage_links "$scratch/home"
rm "$scratch/home/ROCKNIX ROMs"
ln -s /personal/roms "$scratch/home/ROCKNIX ROMs"
refresh_storage_links "$scratch/home"
test "$(readlink "$scratch/home/ROCKNIX ROMs")" = /personal/roms
rm "$scratch/home/ROCKNIX ROMs"
mkdir "$scratch/home/ROCKNIX ROMs"
refresh_storage_links "$scratch/home"
test -d "$scratch/home/ROCKNIX ROMs"
ln -s "$scratch/home" "$scratch/redirect"
rm "$scratch/home/ROCKNIX External Games"
refresh_storage_links "$scratch/redirect"
test ! -L "$scratch/home/ROCKNIX External Games"
printf 'PASS: shared Desktop/game shortcuts created; existing personal paths preserved\n'
