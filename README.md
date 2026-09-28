# ROCKNIX Desktop

Experimental Retroid Pocket 6 desktop mode, using ROCKNIX's existing Sway
compositor with native Wayland applications in a Debian 13 ARM64 runtime.

## Support

| Device | ROCKNIX version | Tested |
| --- | --- | --- |
| Retroid Pocket 6 | Nightly 20260927 (SM8550) | ✅ |

Desktop checks passed on the RP6. Rockchip compatibility is not implied
by ARM64 support; graphics, orientation, input and media need physical testing.
`dev` is the development channel.

## Install and build

Back up saves/settings. On the RP6, as root, with EmulationStation running,
Internet access and 4 GiB free on `/storage`:

```sh
curl -fL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh -o /storage/install-desktop.sh
bash /storage/install-desktop.sh --release v0.2.0-alpha.1 --check
bash /storage/install-desktop.sh --release v0.2.0-alpha.1
```

Inspect scripts before execution. [Sway alpha v0.2.0-alpha.1](https://github.com/kapdon/rocknix-desktop/releases/tag/v0.2.0-alpha.1)
pins the package selection; the installer comes from the maintained `dev` branch.

The installer shows installed and available revisions and asks once to
install or update. Matching revisions report already up to date. Updates preserve
home/settings and retain a recovery copy; exit Desktop Mode first. `--yes` confirms
non-interactively; `--check` only checks the device without downloading or updating.
Uninstall remains separate: run the installed `uninstall.sh --check`, then `--yes`.
Never delete your home to bypass a safety check.

For development builds, use the same installer and omit `--release`.
The rolling `development` release uses
`latest.json` to select a commit-qualified archive and checksum together.
Checksums establish integrity, not independent trust. Until a build completes,
the pointer selects the last successful build. Versioned alpha assets and their
manifest are not replaced after publication.

Build locally with Docker and ARM64 execution support:

```sh
bash tests/check.sh
./build-rootfs.sh
sha256sum -c dist/rocknix-sway-rp6-arm64.tar.xz.sha256
```

Builds require clean committed source. Copy and verify the archive on-device,
extract to a new staging directory on `/storage`, and run its `install-device.sh`.
Existing runtimes are refused; use the upgrade procedure below. Refresh the
EmulationStation game list and select **Tools → Desktop Mode**. Installation
does not launch the desktop or change the normal boot target.

**About Desktop Mode** in Apps, or `rocknix-version` in Foot, shows the installed
commit/build date, not the current GitHub revision.

## Desktop and controls

Waybar keeps Apps, a combined status/settings entry, battery, clock, Keyboard and
Return to Gaming visible. A Windows entry appears only when more than one app is
open. Fuzzel puts Firefox, Files and Foot first, then filters apps as you type.
Its size, the panel and the host keyboard are derived from the active output's
logical dimensions. Firefox ESR and MPV run natively on Wayland.

In Apps, use the D-pad to move, the bottom face button to launch and the right
face button to dismiss. Select cycles open apps, and L3 shows or hides the host
on-screen keyboard. Space remains available for multiword searches.
Return to Gaming asks for confirmation before closing desktop apps. Cancel is
selected initially; choose Return to Gaming explicitly after saving your work.

See [the full controller mapping](payload/input/desktop.yaml). Physical button
positions apply regardless of printed labels. Guide/Quick Access retain their
InputPlumber UI events; the prior profile and targets are restored on return.

## Persistence and upgrades

Everything installed is on writable `/storage`. Inside the installation directory:

| Location | Ownership and persistence |
| --- | --- |
| `home/` | Personal files/settings/app data, mounted at `/home/rocknix`; retained in place across replacement. Back up independently. |
| `rootfs/` | Replaceable Debian runtime. Extra packages/edits do not migrate automatically. |
| `bin/`, `input/`, `integration/` | Replaceable project-managed scripts, controller defaults and templates. |
| `logs/` | Retained diagnostic logs. |
| `build-info`, `install-info` | Exact source/build and installation metadata. |

Shared `/storage/Desktop`, `Steam`, `backup`, `games-external`, `games-internal`,
`roms` and `scripts` are writable real directories, not copies. Uninstall never
removes them. OTA is expected to retain storage, but future OTA compatibility
and suspend/resume are not guaranteed.

Exit Desktop Mode. Use a trusted bundle and its known SHA-256:

```sh
bash upgrade.sh --bundle /storage/rocknix-sway-rp6-arm64.tar.xz --sha256 YOUR_64_CHARACTER_SHA256 --check
bash upgrade.sh --bundle /storage/rocknix-sway-rp6-arm64.tar.xz --sha256 YOUR_64_CHARACTER_SHA256 --yes
```

The upgrader checks ownership, provenance, checksum, space and idle state. It
backs up home, replaces managed components and restores old components on ordinary
activation failure. Same-commit upgrades are no-ops; hashes do not indicate version
ordering. The printed recovery directory includes the previous runtime, a home
backup and transaction state. Even `--check` retains staging. Rollback never
overwrites live home.

`uninstall.sh --yes` keeps a recoverable copy of runtime/integration and leaves
home and logs in place. Reinstall reuses that home. Unknown content and symlinked
homes fail closed.

Recognized Return, keyboard and About shortcuts refresh with sibling
`*.before-refresh.*` backups. Personal collisions and links remain untouched.
Controller defaults are replaced with the payload. Applications may migrate
settings; back up before downgrading.
Automatic power-loss recovery is not implemented.
Never erase `.upgrade-in-progress` blindly; see [upgrade design](docs/upgrades.md).

## Architecture and graphics

Preflight checks RP6, Sway IPC, DSI-1 landscape transform and required tools.
Desktop Mode saves workspace, keyboard and input state, stops only EmulationStation
and keeps Sway alive. Private chroot mounts expose host devices/services/storage.
Native Wayland clients use workspace `98:Desktop`.

- Mesa Freedreno/Turnip provide Wayland OpenGL/Vulkan.
- MPV prefers Qualcomm Iris `h264_v4l2m2m`, with normal decoder fallback.
- Firefox alone uses isolated pinned Raspberry Pi FFmpeg 7.1.5 DRM-PRIME/V4L2
  libraries. MPV/system libraries are unchanged. The candidate uses 32 capture
  buffers, a tested configuration, not proof that it fixes starvation: the
  automated YouTube stall also occurred with software decoding.
- The dedicated Firefox profile disables AV1/WebM to select tested H.264.
  Normal non-WebDriver YouTube playback completed a 5:13 720p60 video.

Capability flags alone do not prove acceleration. Prior rendered-frame, decoder,
Iris-interrupt and playback evidence does not certify every site/codec. See
[idle RAM measurements](tests/rp6-idle-ram-20260928.md). The desktop runs as root
and shares host devices/storage/services: **not a security sandbox**.

## Recovery and provenance

Use **Return to Gaming** to leave the desktop. Diagnostic logs are retained in
the installation's `logs/` directory. Run `bash uninstall.sh --check` before `--yes`; keep the
printed recovery directory. Mounted runtimes are refused; no personal-data purge
is provided.

The Debian base digest and FFmpeg source/archive checksum are pinned. Build metadata
records the source commit and immutable Docker image ID. Debian packages depend on repository state at
build time. See [FFmpeg notes](experiments/ffmpeg/README.md) and
[contributor guide](contributor.md).
The private FFmpeg source archive, downstream patch and build script ship under
`/opt/ffmpeg-rpi-7.1.5/share/source/`; its license is retained under `share/licenses/`.
See [Sway validation](tests/rp6-sway-validation.md) for the exact tested candidate
and the distinction between hardware acceptance and subsequent publishing checks.
