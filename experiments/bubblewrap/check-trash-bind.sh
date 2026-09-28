#!/bin/bash
# Host-side reproduction of dev's separate home/shared bind-mount topology.
# Requires bubblewrap and gio. Does not touch the RP6 or existing user data.
set -Eeuo pipefail
work=$(mktemp -d /tmp/rocknix-trash-bind.XXXXXX)
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/home" "$work/shared"
touch "$work/shared/fixture"
bwrap --unshare-user --uid 0 --gid 0 --unshare-pid --unshare-ipc \
  --ro-bind / / --proc /proc --dev /dev --tmpfs /tmp \
  --bind "$work/home" /tmp/home --bind "$work/shared" /tmp/shared \
  --setenv HOME /tmp/home --setenv XDG_DATA_HOME /tmp/home/.local/share \
  --unsetenv DBUS_SESSION_BUS_ADDRESS --setenv GIO_USE_VFS local \
  -- /bin/sh -eu -c '
    test "$(id -u)" = 0
    test "$(stat -c %d /tmp/home)" = "$(stat -c %d /tmp/shared)"
    if gio trash /tmp/shared/fixture 2>/tmp/trash-error; then
      echo "Trash succeeded: this GLib handles separate bind mounts"
    else
      cat /tmp/trash-error
      test -f /tmp/shared/fixture
      grep -q "across filesystem boundaries" /tmp/trash-error
      echo "REPRODUCED: root identity, no idmap, separate bind mounts"
    fi
  '
