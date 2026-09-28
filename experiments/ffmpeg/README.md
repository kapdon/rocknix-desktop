# Isolated Firefox FFmpeg build

Firefox's Linux V4L2 decoder requires DRM PRIME frames. Debian's stock FFmpeg
7.1.5 initializes the RP6 Iris H.264 decoder but returns ordinary mapped frames,
so Firefox rejects that path and falls back to software decoding.

The rootfs build compiles a minimal library set from RPi-Distro FFmpeg branch
`pios/trixie`, commit `2fe08f3bd52c6e795df8353d29deb89596b5099d`. The Dockerfile pins the source
archive SHA-256 and applies that revision's
`debian/patches/ffmpeg-7.1.5-rpi_29.patch`.

The result is installed under `/opt/ffmpeg-rpi-7.1.5`. Only
`/usr/local/bin/rocknix-firefox` adds its library directory to
`LD_LIBRARY_PATH`; stock FFmpeg and MPV remain unchanged. This build includes
only the codecs and helpers needed for the H.264/AAC validation path and is not
a system FFmpeg replacement.

Firefox ESR does not currently pass the V4L2 `num_capture_buffers` codec option.
This isolated build uses a 32-buffer default. The earlier inference that a
40-second YouTube stall proved capture-buffer starvation was incorrect: the
automated session also stalled with confirmed software decoding, with YouTube
UMP/SPS rejection errors. Normal Firefox without Marionette completed a 5:13
720p60 video using Iris, with 18,808 decoded frames and normal EOF. Keep this
tested configuration; it is not evidence that more buffers fix the automated
stream rejection. [Mozilla's buffer discussion][buffer-fix] is background, not
a diagnosis of this device's failure.

Source: <https://github.com/RPi-Distro/ffmpeg/tree/2fe08f3bd52c6e795df8353d29deb89596b5099d>

[buffer-fix]: https://bugzilla.mozilla.org/show_bug.cgi?id=1612995#c26
