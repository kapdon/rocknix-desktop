#!/bin/sh
set -eu
mkdir /tmp/gamescope
tar -xJf /tmp/gamescope.orig.tar.xz -C /tmp/gamescope --strip-components=1
tar -xJf /tmp/gamescope.debian.tar.xz -C /tmp/gamescope
cd /tmp/gamescope
# These tools execute on the build host during shader generation.
sed -i 's/ glslang-tools,/ glslang-tools:native,/' debian/control
mk-build-deps --install --remove --build-dep --host-arch arm64 \
    --tool 'apt-get -y --no-install-recommends' debian/control
