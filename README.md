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
curl -fL https://raw.githubusercontent.com/kapdon/rocknix-xfce/v0.1.0-alpha.1/install.sh -o /storage/install-xfce.sh
bash /storage/install-xfce.sh --check
bash /storage/install-xfce.sh
```

You can inspect the downloaded script before running it. The installer downloads
the matching versioned release bundle, checks SHA-256, rejects unsupported devices
and existing installations, and installs only under `/storage`. Checksums detect
corruption; they are not independent signatures. Trust the repository/release owner.

Refresh EmulationStation's game list (or reboot), then choose **Tools → Desktop
Mode**. Use **Return to EmulationStation** or log out of XFCE to return. Installing
does not launch the desktop or change the normal boot target.

This is an alpha release. The desktop behavior was tested on an existing RP6;
the new download/install flow has automated checks but has not been end-to-end
tested on a freshly flashed device. It intentionally refuses upgrades/reinstalls.

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

## Architecture and limitations

An ARM64 Debian 13 runtime lives in `/storage/.local/share/rocknix-xfce/rootfs`.
The home directory is stored separately alongside it. ROCKNIX retains its kernel,
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
For removal, stop Desktop Mode, back up its home, and remove only the project's
runtime directory and these integration files:

- `/storage/.config/system.d/xfce-desktop.service`
- `/storage/.config/autostart/999-rocknix-xfce`
- `/storage/.config/modules/Desktop Mode.sh`

Run `systemctl daemon-reload` afterward. Removing the runtime directory also
removes the desktop home unless you have backed it up.

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
