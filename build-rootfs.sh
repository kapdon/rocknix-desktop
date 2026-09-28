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
if [ "$(id -u)" = 0 ]; then
  PACKAGER=(bash)
else
  command -v fakeroot >/dev/null || { printf 'Install fakeroot to preserve archive ownership\n' >&2; exit 1; }
  PACKAGER=(fakeroot -- bash)
fi
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
"${PACKAGER[@]}" "${PROJECT_DIR}/scripts/package-rootfs.sh" \
  "${CONTAINER_ID}" "${PROJECT_DIR}" "${TEMP_DIR}" "${IMAGE_ID}" "${REVISION}" "${OUTPUT}"
docker rm "${CONTAINER_ID}" >/dev/null
CONTAINER_ID=""

(
  cd "${DIST_DIR}"
  sha256sum "$(basename "${OUTPUT}")" >"$(basename "${OUTPUT}").sha256"
)

printf 'Built %s\n' "${OUTPUT}"
cat "${OUTPUT}.sha256"
