#!/bin/sh
set -eu

SOURCE=/tmp/ffmpeg-stock
PREFIX=/opt/rocknix-mpv
SUPPORT=/tmp/mpv-ffmpeg

if [ "${1:-}" = prepare ]; then
  mkdir "${SOURCE}"
  tar -xJf /tmp/ffmpeg_7.1.5.orig.tar.xz -C "${SOURCE}" --strip-components=1
  tar -xJf /tmp/ffmpeg_7.1.5-0+deb13u1.debian.tar.xz -C "${SOURCE}"
  cd "${SOURCE}"
  # Clang is a build tool; run it on the builder, not the target architecture.
  sed -i 's/^ clang / clang:native /' debian/control
  mk-build-deps --install --remove --build-dep --host-arch arm64 \
    --build-profiles pkg.ffmpeg.noextra \
    --tool 'apt-get -y --no-install-recommends' debian/control
  exit 0
fi
cd "${SOURCE}"
patch --batch --fuzz=0 -p1 <"${SUPPORT}/0001-reset-decoder-on-seek.patch"

# Keep Debian's standard codecs, hardening and exported version-array ABI.
# The explicit shared-library target omits static libraries, programs and docs.
export DEB_BUILD_PROFILES=pkg.ffmpeg.noextra
export PKG_CONFIG_LIBDIR=/usr/lib/aarch64-linux-gnu/pkgconfig:/usr/share/pkgconfig
dpkg-architecture -aarm64 -c 'eval "$(dpkg-buildflags --export=sh)"; make -f debian/rules configure_standard'
make -C debian/standard -j"$(nproc)" libavcodec/libavcodec.so

install -Dm0644 debian/standard/libavcodec/libavcodec.so.61 \
  "${PREFIX}/lib/libavcodec.so.61.19.101"
aarch64-linux-gnu-strip --strip-unneeded "${PREFIX}/lib/libavcodec.so.61.19.101"
ln -s libavcodec.so.61.19.101 "${PREFIX}/lib/libavcodec.so.61"

mkdir -p "${PREFIX}/share/source" "${PREFIX}/share/licenses/ffmpeg"
install -m0644 /tmp/ffmpeg_7.1.5.orig.tar.xz \
  /tmp/ffmpeg_7.1.5-0+deb13u1.debian.tar.xz \
  "${SUPPORT}/0001-reset-decoder-on-seek.patch" "${SUPPORT}/build.sh" \
  "${PREFIX}/share/source/"
for license in COPYING.GPLv2 COPYING.GPLv3 COPYING.LGPLv2.1 COPYING.LGPLv3; do
  install -m0644 "${license}" "${PREFIX}/share/licenses/ffmpeg/${license}"
done
install -m0644 debian/copyright "${PREFIX}/share/licenses/ffmpeg/debian-copyright"
