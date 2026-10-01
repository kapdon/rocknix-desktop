# Isolated Firefox FFmpeg build

Firefox's Linux V4L2 decoder requires DRM PRIME frames. Debian's stock FFmpeg
7.1.5 initializes the RP6 Iris H.264 decoder but returns ordinary mapped frames,
so Firefox rejects that path and falls back to software decoding.

The rootfs build compiles a minimal library set from RPi-Distro FFmpeg branch
`pios/trixie`, commit `2fe08f3bd52c6e795df8353d29deb89596b5099d`. The Dockerfile pins the source
archive SHA-256 and applies that revision's
`debian/patches/ffmpeg-7.1.5-rpi_29.patch`.

The result is installed under `/opt/ffmpeg-rpi-7.1.5`. Only
`/usr/local/bin/rocknix-firefox` adds this library directory to
`LD_LIBRARY_PATH`. MPV uses its own [codec correction](../mpv-ffmpeg/README.md);
the system FFmpeg remains package-managed. This Firefox build
includes only the codecs and helpers needed for H.264/AAC playback and is not
a system FFmpeg replacement.

Firefox ESR does not pass the V4L2 `num_capture_buffers` codec option in this
configuration, so the build retains the canonical 32-buffer default.

Source: <https://github.com/RPi-Distro/ffmpeg/tree/2fe08f3bd52c6e795df8353d29deb89596b5099d>
