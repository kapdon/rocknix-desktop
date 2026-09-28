#!/bin/sh

set -eu

SOURCE=/tmp/ffmpeg-rpi
PREFIX=/opt/ffmpeg-rpi-7.1.5

mkdir -p "${SOURCE}"
tar -xzf /tmp/ffmpeg-rpi.tar.gz -C "${SOURCE}" --strip-components=1
cd "${SOURCE}"

# RPi-Distro carries the V4L2 DRM PRIME export path Firefox requires. The
# source archive and this patch are both pinned by the Dockerfile checksum/SHA.
patch -p1 <debian/patches/ffmpeg-7.1.5-rpi_29.patch

export PKG_CONFIG_LIBDIR=/usr/lib/aarch64-linux-gnu/pkgconfig:/usr/share/pkgconfig
./configure \
  --prefix="${PREFIX}" \
  --enable-cross-compile \
  --cross-prefix=aarch64-linux-gnu- \
  --pkg-config=pkg-config \
  --arch=aarch64 \
  --target-os=linux \
  --enable-shared \
  --disable-static \
  --disable-debug \
  --disable-doc \
  --disable-autodetect \
  --enable-libdrm \
  --enable-libudev \
  --enable-v4l2-m2m \
  --disable-everything \
  --enable-decoder=h264,h264_v4l2m2m,aac \
  --enable-parser=h264,aac \
  --enable-demuxer=mov,h264 \
  --enable-protocol=file \
  --enable-muxer=null,rawvideo \
  --enable-encoder=wrapped_avframe,rawvideo \
  --enable-filter=buffer,buffersink,format,hwdownload,null \
  --enable-ffmpeg \
  --enable-ffprobe

make -j"$(nproc)"
make install
install -Dm0644 COPYING.LGPLv2.1 "${PREFIX}/share/licenses/ffmpeg/COPYING.LGPLv2.1"
