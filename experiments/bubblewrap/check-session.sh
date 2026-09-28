#!/bin/bash
# Run as the desktop user, not through a root maintenance chroot.
set -Eeuo pipefail
mkdir -p "${HOME}/.cache"
exec >"${HOME}/.cache/bubblewrap-validation.txt" 2>&1
test "$(id -u)" = 62000
id
grep -E 'Uid:|Gid:|CapEff:|CapBnd:|NoNewPrivs:|Seccomp:' /proc/self/status
test -z "${SWAYSOCK:-}"
test ! -e /run/0-runtime-dir
test ! -e /run/dbus/system_bus_socket
test ! -e /dev/input
test ! -e /dev/dri/card0
test ! -w /usr/bin/bash
test ! -w /run/rocknix-xfce
test -w /run/rocknix-xfce/host-control
test -w /run/rocknix-xfce/control
test ! -e /run/rocknix-xfce/wvkbd.pid
test -w /storage/roms
test ! -w /storage/scripts
unshare -Ur /bin/true
printf 'PASS: identity, host exclusion, readonly controls and nested userns\n'
shared_test=$(mktemp /storage/Desktop/.bubblewrap-parity.XXXXXX)
printf 'bubblewrap shared write\n' >"${shared_test}"
mv "${shared_test}" "${shared_test}.renamed"
test "$(cat "${shared_test}.renamed")" = 'bubblewrap shared write'
printf 'SHARED_TEST_FILE=%s\n' "${shared_test}.renamed"
printf 'PASS: shared Desktop create, edit, rename and read\n'
wayland-info >/tmp/bubblewrap-wayland.txt
pactl info
printf 'PASS: Wayland and Pulse connection\n'
timeout 15 glmark2-wayland --off-screen --size 320x240 --benchmark build:duration=1
printf 'PASS: GPU rendering benchmark\n'
if [ -c /dev/video0 ] && [ -r /storage/Desktop/rp6-sway-h264-60s.mp4 ]; then
  test ! -e /dev/video1
  timeout 30 /opt/ffmpeg-rpi-7.1.5/bin/ffmpeg -hide_banner -loglevel info \
    -c:v h264_v4l2m2m -i /storage/Desktop/rp6-sway-h264-60s.mp4 \
    -an -frames:v 30 -f null -
  printf 'PASS: non-root Iris H.264 decode; encoder not exposed\n'
fi
