# MPV hardware decoder corrections

The rootfs build uses Debian FFmpeg `7:7.1.5-0+deb13u1` with focused V4L2
decoder patches. Seeking resets queued frames and end-of-stream state. Empty
recoverable error buffers are recycled without creating an invalid image;
nonempty error frames and genuine end-of-stream handling are preserved.
Iris source changes resume after their final capture buffer is consumed, before
recycling an empty notification. Other drivers retain their event handling.

`build.sh` cross-compiles the shared codec library using the unchanged Debian
standard configuration, including its codecs and hardening. The stock version
string and exported version-array size are retained. Only
`libavcodec.so.61.19.101` and its `.61` alias are installed under
`/opt/rocknix-mpv/lib`; MPV's other FFmpeg libraries remain Debian packages.
The `mpv` wrapper selects this codec library. Firefox keeps its separate
minimal FFmpeg build.

Docker runs `build.sh prepare` for cached dependencies, then `build.sh` to compile.

The exact upstream and Debian source archives, patches and build script are
retained in `/opt/rocknix-mpv/share/source`. Debian copyright and the upstream
GPL/LGPL notices are in `/opt/rocknix-mpv/share/licenses/ffmpeg`. The standard
configuration is GPLv2 or later. This build does not run upstream test suites.
