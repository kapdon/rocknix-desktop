# RP6 Sway migration validation — 2026-09-28

## Candidate and boundary

- RP6, ROCKNIX nightly 20260927, SM8550, kernel 7.2.0.
- Source: `9c9b236c6d1b5175e09c684dc95d1b16f55f83fd`.
- Bundle SHA-256: `0f679ce5c77d2a3ffdb64a14b23900dd9b03b89a0470ab6e0104ab00eb49088b`.
- Runtime image: `sha256:b5c8279e83a86aa67717694b6b6d45f8a14d17220f0bd8ffc1387075ed4da72e`.
- Build time: `2026-09-28T07:37:47Z`.
- Private raw logs, hashes and screenshots retained on the test device; no SSH
  credentials or private device addresses are published here.

Automated results below pass. The operator also confirmed **all checks pass** for
touch/orientation, stick/click, D-pad/face buttons in Apps, L3 keyboard show/hide,
Firefox YouTube picture/audio, and Return to Gaming on this installation.
This supports RP6 feature-parity promotion, not Rockchip or universal-app support.

## Features brought forward from XFCE dev

The Sway branch merges XFCE `dev` through `7f5ee5c`, retaining ancestry rather than
discarding the three locally newer XFCE commits.

| Feature | Sway integration |
| --- | --- |
| Rolling development builds | Same commit-qualified archive/pointer design, Sway artifact name, planned `rocknix-desktop` repository. Publication remains gated. |
| Persistent home | Uninstall archives managed runtime separately; reinstall retains the same home directory. |
| Managed home refresh | Return/About/keyboard shortcuts refresh with sibling backups; custom files/links win. Old Onboard shortcut migrates to the native keyboard toggle. |
| Explicit upgrades | Trusted local bundle/checksum, check-only, same-commit no-op, home backup and ordinary-failure rollback. |
| Build identification | Source commit + immutable image ID, `rocknix-version`, About launcher using Foot. |
| Controller bindings | Same physical mapping; Sway owns the temporary L3 keyboard binding and restores the previous profile/targets. |

XFCE panel layout/compositing settings remain saved but are not applied to Waybar.
This is equivalent functionality, not preservation of the XFCE window manager UI.
Legacy base paths and unit names remain for upgrade/uninstall compatibility.

## Installation and upgrade tests

1. Replaced the earlier Sway experiment, which lacked source metadata, using the
   new home-preserving uninstaller and installer. Installed intermediate merge
   `2c8e93b`. Home inode and every existing file SHA-256 were unchanged.
2. Confirmed Debian package inventory byte-for-byte unchanged from the previous
   Sway runtime. Firefox executable and isolated FFmpeg `libavcodec` also compare
   byte-for-byte equal on the final candidate.
3. Wrong SHA-256 rejected without changing installed build metadata.
4. `upgrade.sh --check` for `9c9b236` passed without changing installed metadata.
5. `--yes` activated `9c9b236`; preflight passed, home inode and original file
   checksums remained unchanged. Recovery/home backup retained separately.
6. Repeated same-commit upgrade reported no-op; rootfs inode stayed unchanged.
7. Local regression tests cover rollback without home replacement, unknown and
   symlinked retained-home rejection, managed refresh/collision safety, and CLI
   validation. These do not prove arbitrary power-loss recovery.

The complete migration from an actual XFCE installation to Sway was not repeated
in this run: device replacement used the existing Sway installation. XFCE home
shortcut migration has a local fixture test. Historical XFCE home-preservation
results remain in their separate report.

## Return-to-Gaming regression

Cause: the session EXIT trap called unqualified `wait`, including a still-running
Thunar child. Return stopped Waybar but never finished the desktop session.
Cleanup now signals owned helpers without waiting for unrelated applications;
systemd owns bounded cleanup of the desktop cgroup. ExecStopPost also clears
stale FIFO/keyboard PID state and only unbinds keys marked as desktop-owned.

On both `2c8e93b` and final `9c9b236`:

| Scenario | Result |
| --- | --- |
| Return with Thunar open, twice | Gaming restored in 0–1 seconds. |
| `systemctl stop` | Gaming restored in 0–1 seconds. |
| Terminate Waybar | Gaming restored in 0–1 seconds. |
| Saved profile/target set | Exactly matches before-session values after every test. |
| Saved workspace/keyboard setting | Exactly restored after every test. |
| Runtime FIFO and keyboard PID file | Removed after every test. |
| Compositor | Remained active. |

Local lifecycle tests also exercise invalid control input, SIGTERM and unexpected
panel exit with deliberately lingering mock clients. No reboot or compositor-loss
fault injection was repeated for this candidate.

## Graphics/media recheck

- OpenGL: `glmark2-wayland`, 800×600, five-second build scene completed with
  `freedreno / FD740`, Mesa 25.0.7. Score 10089 is a short smoke test, not comparable
  to the earlier full-suite score 5954.
- Vulkan: 120-frame Wayland `vkcube` completed on Turnip Adreno 740.
- MPV: 15-second H.264 sample selected `h264_v4l2m2m`, `/dev/video0`, Iris Decoder,
  NV12 and `gpu-next`. Iris interrupts rose from 95334 to 95523.
- About launcher rendered installed provenance correctly. Screenshot inspected
  at 1920×1080 with landscape orientation and the complete Waybar shell visible.
- Firefox launched from the actual Waybar button; its binary and isolated decoder
  library are unchanged from the earlier sustained-playback validation.

Earlier Sway evidence, **not rerun as full-duration tests on this commit**:

- Firefox local H.264: 55 seconds, 1649 frames, zero drops, Iris activity.
- YouTube pause/resume/seek: pause held, resumed advancement 10.0266 seconds,
  seek error 0.54 seconds, 2072 decoded frames, five drops; audio stream active.
- Normal Firefox, without Marionette: complete 5:13 720p60 video, 18808 decoded
  frames, hardware-decoder flag, Iris activity, normal EOF.
- Marionette-driven YouTube stalled with UMP/SPS rejection under both hardware
  and confirmed software decode. This is not evidence of capture-buffer starvation.

See [RAM measurements](rp6-idle-ram-20260928.md) for controlled idle comparisons.

## Promotion and publication

- Physical touch/orientation, stick/click, D-pad/face-button, L3 keyboard,
  YouTube picture/audio and Return-to-Gaming confirmation: operator passed.
- Preserve the exact XFCE `dev` tip before promoting Sway; do not rewrite/delete
  historical release artifacts. Rename the public repository to `rocknix-desktop`
  only as part of the approved promotion.
- Validate the published development workflow and download pointer after promotion;
  local installer/upgrade success is not proof of the GitHub download path.
