# ROCKNIX Sway Desktop

A native-Wayland desktop mode for ROCKNIX on the Retroid Pocket 6. It keeps
ROCKNIX's existing Sway compositor running, replaces EmulationStation with a
handheld-sized Waybar/Fuzzel shell, and restores the exact frontend and input
state when the desktop exits. The read-only ROCKNIX image stays unchanged.

This branch is a device-validation candidate, not a published release. It is
feature-complete only after every gate in `tests/rp6-sway-validation.md` passes
on the connected RP6, including sustained Firefox/YouTube hardware decoding.

## Device support

| Device | Status | Target ROCKNIX build |
| --- | --- | --- |
| Retroid Pocket 6 | Experimental; validation in progress | Nightly 20260927, SM8550 |

No other device is supported. A matching architecture is not enough; the
session checks the device model, display transform, compositor, and host tools
before changing frontend or input state.

## Development install

Back up saves and settings first. Build on a Docker host with ARM64 execution
support:

```sh
bash tests/check.sh
./build-rootfs.sh
sha256sum -c dist/rocknix-sway-rp6-arm64.tar.xz.sha256
```

The result is `dist/rocknix-sway-rp6-arm64.tar.xz`. Copy it to the RP6 while
EmulationStation is running, verify the checksum again on-device, extract it
under a new staging directory on `/storage`, and run its `install-device.sh`.
The installer refuses an existing installation or integration file rather than
overwriting it.

If the older XFCE alpha is installed, use this checkout's recoverable
`uninstall.sh` first:

```sh
bash uninstall.sh --check
bash uninstall.sh --yes
```

The future download installer is prepared for `v0.2.0-alpha.1`, but no release
or assets are published by this branch. Do not use `install.sh` without a
matching immutable release.

After installation, refresh EmulationStation's game list and choose
**Tools -> Desktop Mode**. Installing does not launch the desktop or change the
normal boot target.

## Desktop shell

- Waybar provides large Apps, Firefox, Keyboard, audio, network, battery, clock,
  and Return to Gaming controls.
- Fuzzel is the native-Wayland application launcher; the D-pad selects and the
  bottom face button opens the selected application.
- Thunar opens `/storage` when the desktop starts.
- Foot is the terminal. Firefox ESR and MPV run natively on Wayland.
- L3 and the Waybar Keyboard button toggle the host `wvkbd-mobintl` keyboard.

## Controls

| Control | Desktop action |
| --- | --- |
| Right stick | Mouse pointer |
| L2 / R2 | Left / right click |
| L1 / R1 | Scroll down / up |
| L3 | Show or hide the on-screen keyboard |
| D-pad | Arrow keys |
| Start / Select | Escape / Tab |
| Left stick | W / A / S / D |
| Bottom face button | Space / launcher activation |
| Top face button | R |
| Left face button | F |
| Right face button | E |

Face-button names describe physical positions regardless of printed labels.
The mapping is loaded only during Desktop Mode. Guide and Quick Access keep
their InputPlumber UI events, and the previously active profile and target set
are restored on return.

## Architecture

The Debian 13 ARM64 runtime lives at
`/storage/.local/share/rocknix-xfce/rootfs`; the persistent home is stored beside
it. That legacy base path and the `xfce-desktop.service` unit name are retained
so the existing recoverable uninstaller can safely recognize both generations.
The runtime itself is marked `ROCKNIX_SWAY_RUNTIME=1`.

Desktop Mode:

1. verifies RP6 identity, Sway IPC, DSI-1's 1920x1080 landscape transform, and
   required host/runtime binaries;
2. records the focused workspace, touchscreen-keyboard state, InputPlumber
   profile, and every active target;
3. stops only `essway.service`, leaving `sway.service` and the Wayland display
   alive;
4. bind-mounts host devices, services, and selected storage into a private
   chroot mount namespace;
5. launches native-Wayland clients on workspace `98:Desktop`; and
6. unbinds temporary keys, restores captured state, and restarts
   EmulationStation on normal return, failure, or compositor loss.

There is no Xorg or XFCE session in the rootfs. Transitive client libraries may
include X11 compatibility files, but the session exports no `DISPLAY` and
launches no X server.

## Graphics and media

- Mesa Freedreno/Turnip use the RP6 host DRM devices for Wayland OpenGL and
  Vulkan.
- MPV prefers `h264_v4l2m2m` on Qualcomm Iris, with normal decoder fallback,
  and uses the Wayland `gpu-next` output path.
- Firefox alone receives an isolated FFmpeg 7.1.5 build from the pinned
  Raspberry Pi `pios/trixie` source. Its DRM-PRIME/V4L2 patch is never placed in
  the global loader path and does not alter MPV or system libraries.
- That isolated build uses 32 V4L2 capture buffers instead of the stock 20 to
  prevent the Iris buffer starvation reproduced during 720p60 streaming.
- Firefox disables AV1 and WebM in the dedicated profile so the current H.264
  hardware-validation path is selected on YouTube.

Capability flags alone do not prove acceleration. Completion requires renderer,
decoder, process-map, interrupt-counter, playback-quality, picture, audio, and
sustained-playback evidence recorded in the RP6 validation report.

The desktop runs as root and shares host devices, storage, audio, and D-Bus. It
is not a security sandbox; do not run untrusted applications.

## Recovery and uninstall

From SSH, return a stuck session to gaming with:

```sh
systemctl stop xfce-desktop.service
systemctl start sway.service essway.service
journalctl -u xfce-desktop.service -b --no-pager
```

Session logs are under `/storage/.local/share/rocknix-xfce/logs/`. A private
mount namespace means exiting the service tears down the chroot mounts. The
uninstaller refuses to move the installation if any mount remains.

`uninstall.sh --yes` archives the runtime, persistent home, unit, boot hook, and
Tools entry under a unique
`/storage/.local/share/rocknix-xfce-backup.*` directory. It does not erase that
recovery copy or any game/save directory.

## Build provenance

`Dockerfile.rootfs` pins the Debian base digest and the Raspberry Pi FFmpeg
source commit/archive checksum. Package versions are recorded in the runtime at
`/etc/rocknix-xfce-packages.tsv`. Debian package feeds are not snapshot-pinned,
so rebuilds are not expected to be bit-for-bit identical.

The build exports the immutable Docker image ID, validates required Sway files,
rejects Xorg/XFCE session binaries, and writes the archive checksum. Never run a
Debian package manager against the ROCKNIX host.

See `contributor.md` for development policy. This is an independent community
project, not an official ROCKNIX release.
