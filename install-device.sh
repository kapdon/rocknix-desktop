#!/bin/bash

set -Eeuo pipefail

. /etc/os-release

SELF_DIR=$(cd "$(dirname "$0")" && pwd)
BASE=/storage/.local/share/rocknix-xfce
ROOTFS_TARGET="${BASE}/rootfs"
MODEL=$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)

fail() {
  printf 'Install failed: %s\n' "$*" >&2
  exit 1
}

[ "$(id -u)" = 0 ] || fail "must run as root"
[ "${OS_NAME:-}" = ROCKNIX ] || fail "this installer requires ROCKNIX"
[ "$(uname -m)" = aarch64 ] || fail "device is not aarch64"
[ "${MODEL}" = "Retroid Pocket 6" ] || fail "unsupported device: ${MODEL:-unknown}"
mount | grep -q ' on /storage .*rw' || fail "/storage is not writable"
[ -d "${SELF_DIR}/rootfs" ] || fail "bundle rootfs is missing"
[ -f "${SELF_DIR}/rootfs/etc/rocknix-xfce-release" ] || fail "runtime marker is missing"
[ -d "${SELF_DIR}/payload" ] || fail "integration payload is missing"
# Share the standalone installer's retained-home safety checks without running it.
source "${SELF_DIR}/install.sh"
check_install_target
for target in /storage/.config/system.d/xfce-desktop.service \
  /storage/.config/autostart/999-rocknix-xfce '/storage/.config/modules/Desktop Mode.sh'; do
  [ ! -e "$target" ] || fail "existing integration would be overwritten: $target"
done
for command in inputplumber swaymsg unshare chroot jq systemd-analyze python3; do
  command -v "$command" >/dev/null || fail "missing host command: $command"
done
systemctl is-active --quiet sway.service || fail "start installation from EmulationStation"
systemctl is-active --quiet xfce-desktop.service && fail "Desktop Mode is currently active"

mkdir -p \
  "${BASE}/bin" \
  "${BASE}/home" \
  "${BASE}/input" \
  "${BASE}/integration" \
  "${BASE}/logs" \
  /storage/.config/autostart \
  /storage/.config/modules \
  /storage/.config/system.d

mv "${SELF_DIR}/rootfs" "${ROOTFS_TARGET}"
cp -a "${SELF_DIR}/payload/bin/." "${BASE}/bin/"
cp -a "${SELF_DIR}/payload/input/." "${BASE}/input/"
cp -a "${SELF_DIR}/payload/integration/." "${BASE}/integration/"
cp -a "${SELF_DIR}/README.md" "${BASE}/README.md"
cp -a "${SELF_DIR}/uninstall.sh" "${BASE}/uninstall.sh"
cp -a "${SELF_DIR}/upgrade.sh" "${BASE}/upgrade.sh"
cp -a "${SELF_DIR}/build-info" "${BASE}/build-info"

chmod 0755 "${BASE}/bin/"* "${BASE}/integration/"*
chmod 0644 "${BASE}/input/"*

cp "${SELF_DIR}/payload/systemd/xfce-desktop.service" /storage/.config/system.d/xfce-desktop.service
chmod 0644 /storage/.config/system.d/xfce-desktop.service

cp "${BASE}/integration/999-rocknix-xfce" /storage/.config/autostart/999-rocknix-xfce
chmod 0755 /storage/.config/autostart/999-rocknix-xfce
/storage/.config/autostart/999-rocknix-xfce

cat >"${BASE}/install-info" <<EOF
installed=$(date -Is)
rocknix_version=${OS_VERSION:-unknown}
rocknix_build=${BUILD_ID:-unknown}
device=${MODEL}
EOF

systemctl daemon-reload
systemd-analyze verify /storage/.config/system.d/xfce-desktop.service
"${BASE}/bin/preflight"
rm -f "${BASE}/.home-retained"
sync

printf 'Desktop Mode installed. It has not been started automatically.\n'
