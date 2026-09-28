#!/bin/bash

set -Eeuo pipefail

PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD_DIR="${PROJECT_DIR}/build"
DIST_DIR="${PROJECT_DIR}/dist"
IMAGE=rocknix-sway-rootfs:trixie-arm64
OUTPUT="${DIST_DIR}/rocknix-sway-rp6-arm64.tar.xz"
TEMP_DIR=""
CONTAINER_ID=""
IMAGE_ID=""
REVISION=$(git -C "$PROJECT_DIR" rev-parse HEAD)
[ -z "$(git -C "$PROJECT_DIR" status --porcelain)" ] || {
  printf 'Commit source changes before building a release.\n' >&2
  exit 1
}

cleanup() {
  if [ -n "${CONTAINER_ID}" ]; then
    docker rm -f "${CONTAINER_ID}" >/dev/null 2>&1 || true
  fi

  case "${TEMP_DIR}" in
    "${BUILD_DIR}"/.rootfs.*)
      rm -rf -- "${TEMP_DIR}"
      ;;
  esac
}
trap cleanup EXIT

mkdir -p "${BUILD_DIR}" "${DIST_DIR}"
TEMP_DIR=$(mktemp -d "${BUILD_DIR}/.rootfs.XXXXXX")
mkdir -p "${TEMP_DIR}/rootfs"

docker buildx build \
  --platform linux/arm64 \
  --load \
  --tag "${IMAGE}" \
  --iidfile "${TEMP_DIR}/image-id" \
  --file "${PROJECT_DIR}/Dockerfile.rootfs" \
  "${PROJECT_DIR}"

IMAGE_ID=$(cat "${TEMP_DIR}/image-id")
case "${IMAGE_ID}" in
  sha256:[0-9a-f][0-9a-f]*) ;;
  *) printf 'Build did not return an immutable image ID\n' >&2; exit 1 ;;
esac

# Export the immutable image ID so another checkout cannot race this build by
# reusing a mutable Docker tag.
CONTAINER_ID=$(docker create --platform linux/arm64 "${IMAGE_ID}" /bin/true)
docker export "${CONTAINER_ID}" | tar --numeric-owner -x -C "${TEMP_DIR}/rootfs"
docker rm "${CONTAINER_ID}" >/dev/null
CONTAINER_ID=""

# Docker injects this file as a runtime mount. Normalize it into a regular
# bind-mount target for the device-side session wrapper.
rm -f "${TEMP_DIR}/rootfs/etc/resolv.conf"
: >"${TEMP_DIR}/rootfs/etc/resolv.conf"
printf 'rocknix-sway\n' >"${TEMP_DIR}/rootfs/etc/hostname"
printf '127.0.0.1 localhost\n::1 localhost ip6-localhost ip6-loopback\n' \
  >"${TEMP_DIR}/rootfs/etc/hosts"
rm -f "${TEMP_DIR}/rootfs/.dockerenv"
find "${TEMP_DIR}/rootfs/dev" -mindepth 1 -delete
find "${TEMP_DIR}/rootfs/proc" -mindepth 1 -delete
find "${TEMP_DIR}/rootfs/run" -mindepth 1 -delete
find "${TEMP_DIR}/rootfs/sys" -mindepth 1 -delete
find "${TEMP_DIR}/rootfs/tmp" -mindepth 1 -delete
chmod 1777 "${TEMP_DIR}/rootfs/tmp"

for required in \
  usr/bin/firefox-esr \
  usr/bin/foot \
  usr/bin/fuzzel \
  usr/bin/glmark2-wayland \
  usr/bin/waybar \
  usr/local/bin/wvkbd-rocknix \
  usr/local/bin/rocknix-launcher \
  usr/local/bin/rocknix-status \
  usr/local/bin/rocknix-window-switcher \
  usr/local/bin/rocknix-sway-session \
  opt/ffmpeg-rpi-7.1.5/bin/ffmpeg; do
  [ -x "${TEMP_DIR}/rootfs/${required}" ] || {
    printf 'Built rootfs is missing %s\n' "${required}" >&2
    exit 1
  }
done
[ ! -e "${TEMP_DIR}/rootfs/usr/bin/Xorg" ] || {
  printf 'Built rootfs unexpectedly contains Xorg\n' >&2
  exit 1
}
[ ! -e "${TEMP_DIR}/rootfs/usr/bin/xfce4-session" ] || {
  printf 'Built rootfs unexpectedly contains xfce4-session\n' >&2
  exit 1
}
grep -qx 'ROCKNIX_SWAY_RUNTIME=1' \
  "${TEMP_DIR}/rootfs/etc/rocknix-xfce-release"

cp -a "${PROJECT_DIR}/payload" "${TEMP_DIR}/payload"
cp -a "${PROJECT_DIR}/install-device.sh" "${TEMP_DIR}/install-device.sh"
cp -a "${PROJECT_DIR}/install.sh" "${TEMP_DIR}/install.sh"
cp -a "${PROJECT_DIR}/README.md" "${TEMP_DIR}/README.md"
cp -a "${PROJECT_DIR}/uninstall.sh" "${TEMP_DIR}/uninstall.sh"
cp -a "${PROJECT_DIR}/upgrade.sh" "${TEMP_DIR}/upgrade.sh"
cp -a "${PROJECT_DIR}/LICENSE" "${TEMP_DIR}/LICENSE"
chmod 0755 "${TEMP_DIR}/install-device.sh"

printf 'built=%s\nbase_image=%s\nrootfs_image=%s\narchitecture=arm64\ncommit=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  'debian@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a' \
  "${IMAGE_ID}" \
  "$REVISION" \
  >"${TEMP_DIR}/build-info"
cp "${TEMP_DIR}/build-info" "${TEMP_DIR}/rootfs/etc/rocknix-xfce-build-info"

tar --numeric-owner -cJf "${OUTPUT}" -C "${TEMP_DIR}" .
(
  cd "${DIST_DIR}"
  sha256sum "$(basename "${OUTPUT}")" >"$(basename "${OUTPUT}").sha256"
)

printf 'Built %s\n' "${OUTPUT}"
cat "${OUTPUT}.sha256"
