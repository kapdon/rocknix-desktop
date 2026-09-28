# ROCKNIX XFCE

A persistent XFCE Desktop Mode for ROCKNIX on Retroid Pocket 6.
Launch it from EmulationStation's Tools menu and log out to return to gaming.
The read-only ROCKNIX image stays unchanged.

## Device support

| Device | Status | Tested ROCKNIX build |
| --- | --- | --- |
| Retroid Pocket 6 | Experimental; desktop, touch, controls and graphics tested | Nightly 20260927, SM8550 |

No other devices are supported. A matching architecture alone is not enough.
Newer or older ROCKNIX builds may change the required display/input interfaces.

## Install

Back up your saves and settings first. Enable SSH in ROCKNIX, connect as root,
and run these commands **on the device**, with EmulationStation running.
Requires Internet access and at least 4 GiB free on writable `/storage`.

```sh
curl -fL https://raw.githubusercontent.com/kapdon/rocknix-xfce/dev/install.sh -o /storage/install-xfce.sh
bash /storage/install-xfce.sh --check
bash /storage/install-xfce.sh
```

You can inspect the downloaded script before running it. The installer downloads
the latest successful development bundle, checks SHA-256, rejects unsupported devices
and existing runtimes, and installs only under `/storage`. Checksums detect
corruption; they are not independent signatures. Trust the repository/release owner.

While idle in EmulationStation, restart its frontend from SSH to rescan Tools:

```sh
systemctl restart essway.service
```

Then choose **Tools → Desktop Mode**. Use **Return to EmulationStation** or log out of XFCE to return. Installing
does not launch the desktop or change the normal boot target.

This is an unstable development channel, not a public alpha release. Every `dev`
push builds and publishes a bundle; until that finishes, the installer selects the
previous successful build. The rolling `development` release's `latest.json`
selects a commit-qualified archive and checksum together. The installed
`/storage/.local/share/rocknix-xfce/build-info` records its exact source commit.
Open **About Desktop Mode** from the desktop or application menu to see that
commit and build date, or run `rocknix-version` in the desktop terminal. This
identifies the installed runtime, not whatever currently happens to be on GitHub.
For local-bundle upgrades, see [Updates and user data](#updates-and-user-data)
before replacing an installation. Home-preserving reinstall has passed local RP6
validation but is not yet published; see [test results](tests/rp6-home-preservation-validation.md).

The earlier alpha installation flow was tested on an RP6 after removing its
previous desktop installation, not on a freshly flashed OS. See
[validation results](tests/rp6-alpha1-validation.md). A successful automated build
is not itself proof that every new change works on hardware.

## Controls

| Control | Desktop action |
| --- | --- |
| Right stick | Mouse pointer |
| L2 / R2 | Left / right click |
| L1 / R1 | Scroll down / up |
| L3 (left-stick press) | Show/hide on-screen keyboard |
| D-pad | Arrow keys |
| Start / Select | Escape / Tab |
| Left stick | W / A / S / D |
| Bottom face button | Space |
| Top face button | R |
| Left face button | F |
| Right face button | E |

Face-button names describe physical positions, regardless of printed labels.
These mappings apply only in Desktop Mode; the previous controller profile is
restored when you return to EmulationStation. Guide and Quick Access retain their
InputPlumber UI events; no extra XFCE actions are assigned to them.

Touchscreen input is supported. XFCE may ask you to trust a desktop launcher on
first use; the L3 keyboard shortcut does not use that launcher.

## Installation paths and persistence

Everything installed by this project is on ROCKNIX's writable `/storage`
partition. Here, **runtime rootfs** means the Debian directory below, not the
device's read-only ROCKNIX root filesystem (`/`). No system partition is replaced.

In this table, `BASE` means exactly `/storage/.local/share/rocknix-xfce`:

| Location on ROCKNIX | Contents and persistence |
| --- | --- |
| `BASE/rootfs/` | Debian runtime, XFCE, libraries and system configuration. Persists across reboots, but is a replaceable component, not a safe place for personal files. Extra packages or edits inside it would need to be reapplied after runtime replacement. |
| `BASE/home/` | Your desktop home; mounted as `/home/rocknix` inside Desktop Mode. Contains personal files, `.config/` settings, `.local/share/` application data and `.cache/`. The new uninstaller leaves it in place for reinstall to reuse. |
| `BASE/bin/`, `BASE/input/`, `BASE/integration/` | Project-managed launch scripts, controller profile and integration templates. Treat these as replaceable, not supported user customization directories. |
| `BASE/graphics-mode` | Optional user-selected display mode (`xorg` or `shm`). |
| `BASE/logs/` | Session diagnostics, not personal documents. |
| `BASE/build-info`, `BASE/install-info` | Installed bundle commit and device/install metadata. Older experimental installs may lack `build-info`. |
| `BASE/README.md`, `BASE/uninstall.sh` | Bundled documentation and uninstaller. |
| `/storage/.config/system.d/xfce-desktop.service` | Project-managed service definition. |
| `/storage/.config/autostart/999-rocknix-xfce` | Project-managed boot hook. |
| `/storage/.config/modules/Desktop Mode.sh` | Generated Tools launcher; the boot hook replaces it from the installed template. Do not customize this generated copy. |
| `/storage/.rocknix-xfce-install.*` | Temporary download/extraction staging. Removed on success; retained with its path printed on failure. |
| `BASE/.home-retained` | Uninstall marker allowing reinstall to recognize retained data. Do not create this manually to bypass checks. |
| `/storage/.local/share/rocknix-xfce-backup.*/installation/` | Removed runtime and managed files retained for recovery. The new uninstaller does not move the home here. Not automatically restored or deleted. |

Existing `/storage/Desktop`, `/storage/Steam`, `/storage/backup`,
`/storage/games-external`, `/storage/games-internal`, `/storage/roms` and
`/storage/scripts` are exposed at the same paths inside Desktop Mode. They remain
outside `BASE`; uninstall does not remove them. These are writable shared files,
not copies: deleting one from the desktop deletes the real file.
`/home/rocknix/Desktop` is your XFCE desktop folder; `/storage/Desktop` is a
different, shared ROCKNIX folder.

Persistence does not mean backup. Back up personal files separately. ROCKNIX OTA
is expected to retain `/storage`, but desktop compatibility after OTA is not yet
validated; reflashing or formatting storage may erase it.

## Updates and user data

**Locally RP6-tested, not yet published:** uninstall
leaves `/storage/.local/share/rocknix-xfce/home/`, logs and `graphics-mode` in place.
Reinstall reuses that same home, not a new copy. The runtime and managed
integration files are archived separately. No personal-data purge is provided.
An existing runtime still blocks the fresh installer; use the separate upgrader.
Only recognized retained data is accepted; unknown content, symlinked retained
directories and existing integration files stop installation safely.

Older published uninstallers archive the entire installation, including home.
Their recovery home is `<printed-recovery-directory>/installation/home/` and is
not automatically restored. Use a matching newly validated installer/uninstaller
pair once published; an older bundled script does not gain this behavior itself.

On desktop startup, the new implementation refreshes these integration fixes:

- The Return to EmulationStation and On-Screen Keyboard launchers.
- The recognized battery indicator configuration, without resetting panel layout.
- The L3 keyboard binding and disabled XFWM compositing.
- Missing ROCKNIX folder links. Existing personal files or custom links win.

Changed recognized launcher/battery files are copied to unique sibling
`*.before-refresh.*` backups before replacement. Unrecognized files or symlinks
at those paths are left alone. Appearance, unrelated shortcuts, documents and
application data are not reset. The disposable `.cache/sessions` cache is still
cleared each session. Controller defaults live outside the home at
`BASE/input/desktop.yaml` and are replaced with the integration payload.

Applications installed into `rootfs/` must be reinstalled after runtime replacement;
their home-based files/settings remain. Applications can migrate their settings,
so downgrading may cause compatibility issues even with an intact home. Keep an
independent backup before changing versions.

### Local-bundle upgrade (experimental)

Exit Desktop Mode first. Copy a trusted locally built bundle and `upgrade.sh`
to the RP6. Supply the SHA-256 from that build, not a random downloaded script:

```sh
bash upgrade.sh --bundle /storage/rocknix-xfce-rp6-arm64.tar.xz --sha256 YOUR_64_CHARACTER_SHA256 --check
bash upgrade.sh --bundle /storage/rocknix-xfce-rp6-arm64.tar.xz --sha256 YOUR_64_CHARACTER_SHA256 --yes
```

The upgrader holds the install/uninstall lock, verifies and stages the bundle,
shows old/new commits, and treats the same commit as a no-op. `--check` leaves
the installed desktop unchanged but retains staging files. `--yes` backs up home,
replaces managed components and restores old components on ordinary activation
failure. Home, logs and graphics preference remain in place. Custom edits and
extra runtime packages are retained in the old runtime, not merged into the new
one. Installing a different commit is explicit; commit hashes do not indicate
whether it is newer or older.

Recovery data is retained at `/storage/.local/share/rocknix-xfce-upgrade.*`:
`old/` contains previous managed components, `home-before.tar` is a separate
backup, and `state` records the outcome. Rollback never restores an old home over
current user files. No automatic deletion of recovery data occurs. An interrupted
upgrade can leave `BASE/.upgrade-in-progress`; stop and inspect its recovery path,
do not delete the marker and retry blindly. Automatic power-loss recovery and
GitHub-download upgrades are not implemented. See [upgrade design](docs/upgrades.md).

## Architecture and limitations

An ARM64 Debian 13 runtime lives in `/storage/.local/share/rocknix-xfce/rootfs`.
Its separate home is `/storage/.local/share/rocknix-xfce/home`, mounted at
`/home/rocknix` inside the desktop. ROCKNIX retains its kernel,
Wi-Fi, audio and InputPlumber services. Desktop Mode temporarily stops
EmulationStation/Sway, starts Xorg/XFCE, and restores the previous frontend/input
profile on exit. No ROCKNIX system partition is remounted or modified.

- Mesa Freedreno OpenGL and Turnip Vulkan are enabled; XFWM compositing is off.
- MPV prefers Iris H.264 hardware decoding with copy-back and software fallback.
- Browser hardware decoding is **not integrated**; Firefox is not bundled.
- Suspend/resume, every application, and future OTA builds are not guaranteed.
- The desktop runs as root and shares host devices, storage and system services.
  It is **not a security sandbox**. Do not run untrusted applications. X11 TCP
  listening is disabled, but local X clients are not isolated from each other.

The persistent boot hook recreates the Tools entry after ROCKNIX's module sync.
OTA updates should leave these files intact, but compatibility still needs testing.

## Troubleshooting and recovery

From SSH, stop a stuck desktop with:

```sh
systemctl stop xfce-desktop.service
systemctl start sway.service essway.service
journalctl -u xfce-desktop.service -b --no-pager
```

Session logs are in `/storage/.local/share/rocknix-xfce/logs/`. To use the slower
shared-memory display fallback, put `shm` in that directory's sibling file
`/storage/.local/share/rocknix-xfce/graphics-mode`, then relaunch. Use `xorg` to return
to the default. The fallback sacrifices accelerated X11 presentation.

An interrupted installation preserves its staging directory and prints its path.
Do not delete or overwrite your existing runtime/home to retry; inspect the error.

## Uninstall

Save your work first: this closes Desktop Mode. From a checkout containing
`uninstall.sh`, copy it to the device and run (or use the bundled script):

```sh
bash uninstall.sh --check
bash uninstall.sh --yes
```

The standalone uninstaller works with the existing alpha runtime. It stops XFCE,
restores EmulationStation, checks for remaining mounts, and removes the active
runtime and its three integration files. The new local implementation leaves
home, logs and display preference in place and **preserves** removed components
in a unique `/storage/.local/share/rocknix-xfce-backup.*` recovery directory.
It does not free that disk space or erase your games/saves. Older published
uninstallers also move home into recovery; see the update notes above.
Refresh the frontend's game list to clear any cached Tools entry.

Development installations include it at
`/storage/.local/share/rocknix-xfce/uninstall.sh`. For older installs, download it:

```sh
curl -fL https://raw.githubusercontent.com/kapdon/rocknix-xfce/dev/uninstall.sh -o /storage/uninstall-xfce.sh
bash /storage/uninstall-xfce.sh --check
bash /storage/uninstall-xfce.sh --yes
```

## Build and contribute

On a Docker host with ARM64 execution support (native ARM64 or configured binfmt):

```sh
bash tests/check.sh
./build-rootfs.sh
```

Outputs are `dist/rocknix-xfce-rp6-arm64.tar.xz` and its checksum. Build packages
come from Debian repositories; package versions are recorded inside the runtime
at `/etc/rocknix-xfce-packages.tsv`. The base image is pinned, but package feeds are
not, so rebuilds are not bit-for-bit reproducible. Build locally; never run Debian
package-manager commands against the ROCKNIX host.

See [contributor.md](contributor.md) for the `dev` branch workflow and small-commit
policy. This is an independent community project, not an official ROCKNIX release.
