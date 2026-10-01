#!/bin/bash

set -Eeuo pipefail

PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)
BUILD_DIR="${PROJECT_DIR}/build"
DIST_DIR="${PROJECT_DIR}/dist"
IMAGE=rocknix-desktop-rootfs:trixie-arm64
OUTPUT="${DIST_DIR}/rocknix-desktop-rp6-arm64.tar.xz"
TEMP_DIR=""
CONTAINER_ID=""
HOST_CONTAINER_ID=""
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
  if [ -n "${HOST_CONTAINER_ID}" ]; then
    docker rm -f "${HOST_CONTAINER_ID}" >/dev/null 2>&1 || true
  fi
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

# Native ARM64 compilation retains Debian's complete test suites. Local
# cross-host builds may supply artifacts from a verified native build instead.
TRASH_PACKAGES_DIR=${ROCKNIX_TRASH_PACKAGES_DIR:-${TEMP_DIR}/trash-packages}
if [ -z "${ROCKNIX_TRASH_PACKAGES_DIR:-}" ]; then
  docker buildx build --platform linux/arm64 --target artifact \
    --output "type=local,dest=${TRASH_PACKAGES_DIR}" \
    --file "${PROJECT_DIR}/build-support/trash/Dockerfile.packages" \
    "${PROJECT_DIR}/build-support/trash"
fi
[ -d "${TRASH_PACKAGES_DIR}" ] || { printf 'Trash package artifacts missing\n' >&2; exit 1; }

docker buildx build --platform linux/arm64 --target artifact \
  --output "type=local,dest=${TEMP_DIR}/fuzzel" \
  --file "${PROJECT_DIR}/build-support/fuzzel/Dockerfile" "${PROJECT_DIR}"

docker buildx build \
  --platform linux/arm64 \
  --build-context "trash-packages=${TRASH_PACKAGES_DIR}" \
  --build-context "fuzzel-artifacts=${TEMP_DIR}/fuzzel" \
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
docker buildx build --platform linux/arm64 --load \
  --tag rocknix-lxc-host-tools:arm64 --iidfile "${TEMP_DIR}/host-tools-image-id" \
  --file "${PROJECT_DIR}/build-support/lxc/Dockerfile.host-tools" "${PROJECT_DIR}"
HOST_IMAGE_ID=$(cat "${TEMP_DIR}/host-tools-image-id")
[[ ${HOST_IMAGE_ID} =~ ^sha256:[0-9a-f]{64}$ ]] || { printf 'Invalid host-tools image ID\n' >&2; exit 1; }
HOST_CONTAINER_ID=$(docker create --platform linux/arm64 "${HOST_IMAGE_ID}" /bin/true)
"${PACKAGER[@]}" "${PROJECT_DIR}/scripts/package-rootfs.sh" \
  "${CONTAINER_ID}" "${PROJECT_DIR}" "${TEMP_DIR}" "${IMAGE_ID}" "${REVISION}" "${OUTPUT}" \
  "${HOST_CONTAINER_ID}" "${TRASH_PACKAGES_DIR}"
docker rm "${CONTAINER_ID}" >/dev/null
CONTAINER_ID=""
docker rm "${HOST_CONTAINER_ID}" >/dev/null
HOST_CONTAINER_ID=""

(
  cd "${DIST_DIR}"
  sha256sum "$(basename "${OUTPUT}")" >"$(basename "${OUTPUT}").sha256"
)

printf 'Built %s\n' "${OUTPUT}"
cat "${OUTPUT}.sha256"
