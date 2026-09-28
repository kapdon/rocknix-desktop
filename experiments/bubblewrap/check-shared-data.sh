#!/bin/bash
# Launch through Apps. Creates only unique test directories in shared data.
# Host companion verifies UID mapping and removes these exact fixtures.
set -Eeuo pipefail
exec >"${HOME}/.cache/rocknix-shared-check.log" 2>&1
test "$(id -u)" = 62000
manifest=${HOME}/.cache/rocknix-shared-check.paths
test ! -e "$manifest" || test ! -s "$manifest"
: >"$manifest"
for name in Desktop Steam backup games-external games-internal roms; do
  parent=/storage/$name
  test -d "$parent"
  work=$(mktemp -d "$parent/.rocknix-bwrap-check.XXXXXX")
  printf '%s\n' "$work" >>"$manifest"
  printf 'non-root create\n' >"$work/created"
  printf 'non-root edit\n' >>"$work/created"
  mv "$work/created" "$work/renamed"
  cp "$work/renamed" "$work/copied"
  cmp "$work/renamed" "$work/copied"
  rm "$work/copied"
  test ! -e "$work/copied"
  test "$(stat -c %u "$work/renamed")" = 62000
  printf 'PASS: %s create/edit/rename/copy/delete; user UID 62000\n' "$parent"
done
test ! -w /storage/scripts
printf 'PASS: scripts remains read-only pending privileged-editing decision\n'
