# ROCKNIX Desktop

Experimental Retroid Pocket 6 desktop mode, using ROCKNIX's existing Sway
compositor with native Wayland applications in a Debian 13 ARM64 runtime.

## Support

Only **Retroid Pocket 6**, tested on ROCKNIX nightly 20260927 (SM8550).
Sway migration validation is in progress. Rockchip compatibility is not implied
by ARM64 support; graphics, orientation, input and media need physical testing.
`dev` is the development channel. XFCE history remains recoverable separately
when the Sway candidate passes the migration gate.

## Install and build

Back up saves/settings. On the RP6, as root, with EmulationStation running,
Internet access and 4 GiB free on `/storage`:

```sh
curl -fL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh -o /storage/install-desktop.sh
bash /storage/install-desktop.sh --check
bash /storage/install-desktop.sh
```

Inspect scripts before execution. The rolling `development` release uses
`latest.json` to select a commit-qualified archive and checksum together.
Checksums establish integrity, not independent trust. Until a build completes,
the pointer selects the previous successful build. The Sway installer rejects
an old XFCE pointer rather than downloading the wrong runtime.

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

Waybar provides Apps, Firefox, Keyboard, audio, network, battery, clock and Return
to Gaming. Fuzzel launches apps, Foot is the terminal, and Thunar opens `/storage`.
Firefox ESR and MPV run natively on Wayland. L3 toggles the host on-screen keyboard.
D-pad selects in Apps; the bottom face button opens the selection.

See [the full controller mapping](payload/input/desktop.yaml). Physical button
positions apply regardless of printed labels. Guide/Quick Access retain their
InputPlumber UI events; the prior profile and targets are restored on return.

## Persistence and upgrades

Everything installed is on writable `/storage`. The legacy base path
`/storage/.local/share/rocknix-xfce` (`BASE`) and `xfce-desktop.service` are retained
so older installations and recovery tools stay recognizable.

| Location | Ownership and persistence |
| --- | --- |
| `BASE/home/` | Personal files/settings/app data, mounted at `/home/rocknix`; retained in place across replacement. Back up independently. |
| `BASE/rootfs/` | Replaceable Debian runtime. Extra packages/edits do not migrate automatically. |
| `BASE/bin/`, `input/`, `integration/` | Replaceable project-managed scripts, controller defaults and templates. |
| `BASE/logs/`, `graphics-mode` | Retained; legacy XFCE graphics preference has no effect on Sway. |
| `BASE/build-info`, `install-info` | Exact source/build and installation metadata. |
| `/storage/.config/system.d/xfce-desktop.service` | Managed service. |
| `/storage/.config/autostart/999-rocknix-xfce` | Managed hook recreating the Tools launcher. |

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
ordering. Recovery under `rocknix-xfce-upgrade.*` includes `old/`, `home-before.tar`
and `state`. Even `--check` retains staging. Rollback never overwrites live home.

Older installs without source metadata require home-preserving uninstall/reinstall
with these new scripts, not fabricated metadata. `uninstall.sh --yes` archives
runtime/integration under `rocknix-xfce-backup.*`, leaving home, logs and graphics
preference in place. The `.home-retained` marker allows reinstall to reuse home.
Unknown content and symlinked homes fail closed. Old published uninstallers instead
archive the entire home; that recovery copy is not automatically restored.

Recognized Return, keyboard and About shortcuts refresh with sibling
`*.before-refresh.*` backups. Personal collisions and links remain untouched.
Saved XFCE panel settings do not configure Waybar. Controller defaults are replaced
with the payload. Applications may migrate settings; back up before downgrading.
Automatic power-loss recovery and remote-download upgrades are not implemented.
Never erase `.upgrade-in-progress` blindly; see [upgrade design](docs/upgrades.md).

## Architecture and graphics

Preflight checks RP6, Sway IPC, DSI-1 landscape transform and required tools.
Desktop Mode saves workspace, keyboard and input state, stops only EmulationStation
and keeps Sway alive. Private chroot mounts expose host devices/services/storage.
Clients use workspace `98:Desktop`; there is no Xorg or XFCE session in the runtime.

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

```sh
systemctl stop xfce-desktop.service
systemctl start sway.service essway.service
journalctl -u xfce-desktop.service -b --no-pager
```

Logs are in `BASE/logs/`. Run `bash uninstall.sh --check` before `--yes`; keep the
printed recovery directory. Mounted runtimes are refused; no personal-data purge
is provided.

The Debian base digest and FFmpeg source/archive checksum are pinned. Build metadata
records the source commit and immutable Docker image ID; package versions are in
`/etc/rocknix-xfce-packages.tsv`. Debian packages still depend on repository state at
build time. See [FFmpeg notes](experiments/ffmpeg/README.md) and
[contributor guide](contributor.md). Historical XFCE reports are not Sway results.
