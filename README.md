# ROCKNIX Desktop

A handheld-first Sway desktop for the Retroid Pocket 6, with native Wayland
applications in a Debian 13 ARM64 runtime. Open it from **Tools → Desktop Mode**
and use **Return to Gaming** to return to EmulationStation.

## Support

| Device | Tested ROCKNIX build |
| --- | --- |
| Retroid Pocket 6 (SM8550) | Nightly 20260927 |

Experimental software. Other ARM64 devices are not supported by the installer;
graphics, output scaling, touch and controller behavior need device-specific tests.
The desktop runs as root and shares host storage/services: **it is not a security sandbox**.

## Install or update

Back up your saves and settings. Exit Desktop Mode, leave EmulationStation running,
then run this single command as root on the RP6 with Internet access and at least
4 GiB free on `/storage`:

```sh
mkdir -p /storage/rocknix-desktop && curl -fL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh -o /storage/rocknix-desktop/install.sh && bash /storage/rocknix-desktop/install.sh
```

The installer shows the installed and available revisions and asks for confirmation.
It installs the latest successfully published development build, or updates an
existing installation while preserving your home. Installation does not launch
Desktop Mode or change the normal boot target. Refresh the EmulationStation game
list if the Tools entry does not appear.

To inspect the script first, run the command without its final
`&& bash /storage/rocknix-desktop/install.sh`, then read the downloaded file.

Installer options:

- `--check`: device/installation preflight only; no download or installation.
- `--yes`: install or update without the confirmation prompt.
- `--release TAG`: select a published version instead of the development channel.

The rolling release's `latest.json` pairs a source commit, commit-qualified archive
and SHA-256. A source push is not an available release: the pointer stays on the
last successful publication until the new build finishes. Checksums verify
integrity, not independent trust.

**About Desktop Mode** in Apps, or `rocknix-version` in Foot, shows the installed
revision and build date. Features described on a working branch may not yet be
in the published development bundle.

## Apps and controls

Waybar keeps **Apps**, **Settings/status**, **Keyboard**, battery, clock and
**Return to Gaming** accessible. **Windows** appears when multiple apps are open.
Firefox, Files and Foot lead the launcher; typing filters the remaining apps,
including multiword searches.

| Control | Action |
| --- | --- |
| D-pad | Navigate launcher choices and app controls |
| Bottom face button | Confirm / Enter |
| Right face button or Start | Back / Escape |
| Left face button (West) | Next field / Tab |
| Top face button (North) | Previous field / Shift+Tab |
| Select | Cycle open windows |
| L3 | Show/hide the keyboard |
| R3 | Request a normal close of the focused window |
| Bumpers / triggers | Scroll / pointer clicks |

Positions apply regardless of printed button labels. Tap and release North:
holding it also holds Shift. Apps determine their own field order.
See the [complete controller mapping](payload/input/desktop.yaml).

R3 does not force-kill an app and does not repeat while held, but an app can close
without a save warning. Closing the last app leaves the panel available.
**Return to Gaming** has a confirmation with Cancel selected initially.

### Keyboard

Desktop Mode bundles its own wvkbd; it does not replace the native ROCKNIX keyboard.

- Four-row Simple typing layout with staggered letters and larger Shift/Backspace.
- **123** opens one four-row numbers/symbols page; **ABC** returns to typing.
- Shift provides uppercase letters and alternate symbols. Shift+Space sends Tab.
- **Cmp** opens character variants after selecting a letter, such as accented vowels.
- No dedicated navigation page or arrow keys in the normal two-page cycle.
- Roboto, charcoal keys, white labels and gray pressed states match the desktop.

Panel, launcher and keyboard sizing use the active output's logical dimensions;
the RP6 configuration is not a universal sizing preset.
See [keyboard source and build notes](experiments/wvkbd/README.md).

### Window layout

One tabbed workspace is the default. Select and Windows include both tabbed and
floating apps. Firefox Picture-in-Picture floats at the bottom-right of the usable
workspace. Audio/network utilities float when they fit and become tabbed when
space is limited, including while the keyboard is visible. Normal app windows
remain tabbed; transient dialogs retain Sway's behavior.

PiP matching currently requires the bundled Firefox's English window title.
See [window-policy details and test boundaries](docs/handheld-usability-followup.md).

## Storage, updates and uninstall

Downloads and staging/recovery directories live under `/storage/rocknix-desktop/`.
The established installation path remains `/storage/.local/share/rocknix-xfce`
for compatibility. That internal directory name does not describe the desktop UI;
do not rename it manually.

| Installed directory | Contents |
| --- | --- |
| `home/` | Personal files, settings and app data; preserved in place |
| `rootfs/` | Replaceable Debian runtime; extra packages do not migrate automatically |
| `bin/`, `input/`, `integration/` | Project-managed components |
| `logs/` | Diagnostic logs |

Shared storage directories, including ROMs and games, are mounted directly,
not copied. Uninstall does not delete them. Back up personal data independently.

Use the install command again to update. For offline/local bundles, see
[upgrades and recovery](docs/upgrades.md).

To uninstall, exit Desktop Mode and run:

```sh
bash /storage/.local/share/rocknix-xfce/uninstall.sh --check
bash /storage/.local/share/rocknix-xfce/uninstall.sh --yes
```

Uninstall retains home/logs and prints the recovery location. Reinstall reuses the
retained home. Updates also retain staging/recovery data; these may consume
substantial storage. Unknown files, unsafe paths and active runtimes are refused.
No personal-data purge or automatic power-loss recovery is provided.

## Build and contribute

With Docker, ARM64 execution support, and `fakeroot` (to preserve Debian archive ownership):

```sh
bash tests/check.sh
bash build-rootfs.sh
(cd dist && sha256sum -c rocknix-sway-rp6-arm64.tar.xz.sha256)
```

Builds require clean, committed source. The archive is
`dist/rocknix-sway-rp6-arm64.tar.xz`, with a sibling `.sha256` file.
Use the local-bundle upgrade procedure for an existing installation; do not extract
over a running runtime. Test locally and on hardware before publication, and
coordinate device access with any recording session.

See [contributing](contributor.md), [architecture](docs/architecture.md),
[graphics/FFmpeg notes](experiments/ffmpeg/README.md) and
[recorded Sway validation](tests/rp6-sway-validation.md).
Historical test reports describe their named builds, not blanket guarantees for
the current revision. Suspend/resume and future OS updates are not guaranteed.
