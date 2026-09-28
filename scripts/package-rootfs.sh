#!/bin/bash
# Run as root or under one fakeroot session. Keep extraction, modifications and
# repacking in that same session so image UID/GID and setuid metadata survive.
set -Eeuo pipefail
[ "$(id -u)" = 0 ] || { printf 'Packaging requires root or fakeroot\n' >&2; exit 1; }
CONTAINER_ID=$1
PROJECT_DIR=$2
TEMP_DIR=$3
IMAGE_ID=$4
REVISION=$5
OUTPUT=$6

docker export "${CONTAINER_ID}" | tar --numeric-owner --same-owner -x -C "${TEMP_DIR}/rootfs"
rm -f "${TEMP_DIR}/rootfs/etc/resolv.conf" "${TEMP_DIR}/rootfs/.dockerenv"
: >"${TEMP_DIR}/rootfs/etc/resolv.conf"
printf 'rocknix-sway\n' >"${TEMP_DIR}/rootfs/etc/hostname"
printf '127.0.0.1 localhost\n::1 localhost ip6-localhost ip6-loopback\n' >"${TEMP_DIR}/rootfs/etc/hosts"
for directory in dev proc run sys tmp; do
  find "${TEMP_DIR}/rootfs/${directory}" -mindepth 1 -delete
done
chmod 1777 "${TEMP_DIR}/rootfs/tmp"

for required in \
  usr/bin/bwrap usr/bin/setfacl usr/bin/mount usr/bin/dbus-run-session usr/bin/xdg-dbus-proxy \
  usr/bin/firefox-esr usr/bin/foot usr/bin/fuzzel usr/bin/glmark2-wayland usr/bin/waybar \
  usr/local/bin/wvkbd-rocknix usr/local/bin/rocknix-launcher usr/local/bin/rocknix-status \
  usr/local/bin/rocknix-window-switcher usr/local/bin/rocknix-sway-session \
  opt/ffmpeg-rpi-7.1.5/bin/ffmpeg; do
  [ -x "${TEMP_DIR}/rootfs/${required}" ] || {
    printf 'Built rootfs is missing %s\n' "${required}" >&2; exit 1;
  }
done
[ ! -e "${TEMP_DIR}/rootfs/usr/bin/Xorg" ]
[ ! -e "${TEMP_DIR}/rootfs/usr/bin/xfce4-session" ]
grep -qx 'ROCKNIX_SWAY_RUNTIME=1' "${TEMP_DIR}/rootfs/etc/rocknix-xfce-release"

cp -a "${PROJECT_DIR}/payload" "${TEMP_DIR}/payload"
for file in install-device.sh install.sh README.md uninstall.sh upgrade.sh LICENSE; do
  cp -a "${PROJECT_DIR}/${file}" "${TEMP_DIR}/${file}"
  chown 0:0 "${TEMP_DIR}/${file}"
done
# These are project-managed host executables/config, not service-owned Debian
# files. Normalize only this payload, never blanket-chown the exported rootfs.
chown -R 0:0 "${TEMP_DIR}/payload"
chmod 0755 "${TEMP_DIR}/install-device.sh"
printf 'built=%s\nbase_image=%s\nrootfs_image=%s\narchitecture=arm64\ncommit=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  'debian@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a' \
  "${IMAGE_ID}" "${REVISION}" >"${TEMP_DIR}/build-info"
cp "${TEMP_DIR}/build-info" "${TEMP_DIR}/rootfs/etc/rocknix-xfce-build-info"
chown 0:0 "${TEMP_DIR}/build-info" "${TEMP_DIR}/rootfs/etc/rocknix-xfce-build-info"
tar --numeric-owner -cJf "${OUTPUT}" -C "${TEMP_DIR}" .
