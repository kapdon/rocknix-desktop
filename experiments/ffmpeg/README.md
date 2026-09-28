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
The stock 20-buffer pool decoded 720p60 YouTube normally through 40 seconds and
then failed, while local 720p30 playback succeeded. This isolated build raises
the decoder default to 32 buffers to prevent capture-buffer starvation. Mozilla
independently identified the same cause and sustained 1080p60 playback with a
32-buffer pool in [bug 1612995 comment 26][buffer-fix]. The longer streaming,
seek, pause/resume, audio, and decoder-log checks still gate integration.

Source: <https://github.com/RPi-Distro/ffmpeg/tree/2fe08f3bd52c6e795df8353d29deb89596b5099d>

[buffer-fix]: https://bugzilla.mozilla.org/show_bug.cgi?id=1612995#c26
