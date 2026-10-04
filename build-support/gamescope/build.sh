#!/bin/sh
set -eu
cd /tmp/gamescope
# Apply Debian packaging patches before our cross-build and lifecycle fixes.
dpkg-source --before-build .
for correction in /tmp/gamescope-support/*.patch; do
    patch --batch --fuzz=0 -p1 <"${correction}"
done
# dpkg's cross dependency check needs the explicit tool architecture here.
sed -i "s/glslang-tools:native/glslang-tools:$(dpkg --print-architecture)/" debian/control
# Upstream used the build machine to name target Vulkan layer artifacts.
sed -i 's/build_machine.cpu_family()/host_machine.cpu_family()/g' layer/meson.build
# Give the patched package an identifiable version above the Debian backport.
cat >debian/changelog.new <<'EOF'
gamescope (3.16.22+ds-1~bpo13+1+rocknix1) trixie-backports; urgency=medium

  * Backport upstream SDL backend thread shutdown (16a44df7).
  * Bound reaper TERM-to-KILL cleanup and keep signal handlers minimal.
  * Correct Vulkan layer artifact names when cross-compiling.

 -- ROCKNIX Desktop <noreply@rocknix.org>  Sun, 04 Oct 2026 00:00:00 +0000

EOF
cat debian/changelog >>debian/changelog.new
mv debian/changelog.new debian/changelog
DEB_BUILD_OPTIONS="nocheck parallel=4" dpkg-buildpackage -aarm64 -b -us -uc
mkdir -p /opt/rocknix-gamescope/source
cp /tmp/gamescope_*.deb /opt/rocknix-gamescope/
cp /tmp/gamescope.orig.tar.xz /tmp/gamescope.debian.tar.xz \
    /tmp/gamescope-support/* /opt/rocknix-gamescope/source/
