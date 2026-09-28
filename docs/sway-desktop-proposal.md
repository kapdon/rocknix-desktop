# Native Wayland desktop on ROCKNIX Sway

Status: historical investigation proposal, written before implementation.
The sections below describe the original plan and its evidence at that time;
see the current README and test reports for implemented behavior and results.

## Decision

Prototype a lightweight desktop as native Wayland clients connected to the
Sway compositor that ROCKNIX already runs. Stop only `essway.service` for the
desktop session; do not replace, exit, or reconfigure the running compositor.
Keep the Debian ARM64 root filesystem as the application runtime, but replace
the XFCE/Xorg shell with Waybar, Fuzzel, foot, and native-Wayland GTK/Qt apps.

This is the most promising route to a controller-friendly desktop and removes
the competing Xorg/XFWM and fullscreen rootful-Xwayland paths. It is not yet a
production recommendation: buffer sharing, video decode, input, touch, OSK,
and failure recovery still require an RP6 acceptance run.

## Scope and evidence boundary

- Repository base: `dev` at `dac1d9d6b5ddac35b84f746d2b7946d9e5ba367a`.
- Public ROCKNIX source snapshot: `next` at `7cfc0cd256e1b5f9b689b25f3c05a78281302de3`
  (2026-09-28 UTC).
- Target reported by the operator: RP6, ROCKNIX nightly 20260927, SM8550,
  kernel 7.2.0, read-only system image.
- No device connection, service action, install, or runtime probe was made.
- The source snapshot is close evidence, not proof that every binary or
  revision is in the target nightly. Device-side checks remain gates.

The current [`launch-xfce`](../payload/bin/launch-xfce) and
[`restore-emulationstation`](../payload/bin/restore-emulationstation) already
provide the useful containment and recovery pieces: `/storage` persistence, a
private mount namespace, selective host bind mounts, InputPlumber state, and
`ExecStopPost` return to the gaming frontend. Remove the display-server handoff.

## What ROCKNIX already provides

The public SM8550 configuration selects Freedreno, Vulkan, Wayland, and Sway.
Its Sway package includes `foot`, `bemenu`, and Xwayland and builds swaybar,
although its tray is disabled. The service owns DRM/libinput, uses
`/var/run/0-runtime-dir`, and restarts on failure.

`essway.service` requires Sway and runs EmulationStation as a Sway client.
Stopping it explicitly with systemd does not trigger `Restart=always`; systemd
does not apply automatic restart when termination is the result of a clean
`systemctl stop` operation.

ROCKNIX contains two particularly relevant precedents:

1. Its generated `config.desktop` launches `foot.sh`, `bemenu-run`, tiling
   bindings, and swaybar. This proves that a general Sway configuration is an
   intended upstream mode, but not that it is an adequate application desktop.
2. Its QTerminal wrapper temporarily owns `wvkbd-mobintl`, selects the
   `full,nav,special` layout, and moves the terminal to a dedicated workspace
   so the keyboard's layer-shell exclusive zone is honored.

The boot-time `desktop.enabled` path is unsuitable here. Its autostart script
overwrites `/storage/.config/sway/config`, masks `essway.service`, and resets
the setting for the next boot. That adds persistent state and requires a
compositor restart; this session must use only temporary IPC commands.

## Proposed architecture

```text
systemd desktop service (host, /storage)
  |-- keeps sway.service running and watches its health
  |-- stops/starts essway.service at the session boundary
  |-- snapshots/restores InputPlumber and keyboard state
  `-- unshare mount namespace + chroot
        |-- Waybar panel and Return to Gaming action
        |-- Fuzzel application launcher
        |-- foot, Thunar, Mousepad, pavucontrol, settings tools
        `-- native GTK/Qt/mpv Wayland clients
                         |
              existing ROCKNIX Sway compositor
                         |
             Freedreno/Adreno DRM scanout and input
```

Sway remains the only DRM/KMS compositor. The Debian processes are ordinary
Wayland clients; “native” here describes their display protocol, not that the
applications are installed in the read-only ROCKNIX image.

## Session lifecycle

### Start

1. Preflight must prove that the rootfs exists, `sway.service` and
   `essway.service` are active, exactly one usable Sway IPC socket and Wayland
   socket exist, and required host/client binaries are present.
2. Atomically record the active InputPlumber profile and targets, the
   touchscreen-keyboard setting/service state, focused output/workspace, and
   any Sway bindings the session may replace. If state cannot be captured, do
   not mutate anything.
3. Explicitly stop `essway.service` and verify it is inactive while Sway stays
   active. Never call `swaymsg exit`, stop Sway, or set `desktop.enabled`.
4. Load the desktop InputPlumber profile and reassert the RP6 touchscreen's
   mapping to the active internal output.
5. Select a dedicated workspace such as `98:Desktop`, install only the
   collision-checked temporary bindings, and launch the chroot session.

Keep `Restart=no`, `KillMode=control-group`, and unconditional `ExecStopPost`.
`BindsTo=sway.service` plus `After=sway.service` should end the desktop when
the compositor disappears. Do not persistently mask EmulationStation.

### Return and failure

The panel's large `Return to Gaming` item sends an exit request to the outer
supervisor through a private runtime control file/FIFO; it must not run
`swaymsg exit`. Use the same path when the critical panel/session process dies.
Require a menu action or confirmation rather than a single controller button.

Cleanup terminates the desktop cgroup, removes temporary bindings/rules,
restores keyboard and InputPlumber state exactly, returns to the prior
workspace, and starts `essway.service`. It must wait with a bounded timeout for
Sway and EmulationStation to become active and log a terminal success or
failure. During shutdown it should restore local state but not fight the
system's stopping transaction by starting services.

If Sway crashes, let `sway.service` perform its configured restart, then make
the cleanup path restore EmulationStation. The acceptance test must cover this
case; dependency declarations alone are not proof of correct ordering.

## Chroot Wayland environment

Reuse the current private mount namespace and bind mounts. Start clients with a
clean environment containing at least:

```text
XDG_RUNTIME_DIR=/var/run/0-runtime-dir
WAYLAND_DISPLAY=<discovered live socket basename>
SWAYSOCK=<discovered live IPC socket>
DBUS_SESSION_BUS_ADDRESS=unix:path=/var/run/0-runtime-dir/bus
DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
PULSE_SERVER=unix:/run/0-runtime-dir/pulse/native
XDG_SESSION_TYPE=wayland
XDG_CURRENT_DESKTOP=sway
GDK_BACKEND=wayland
QT_QPA_PLATFORM=wayland
SDL_VIDEODRIVER=wayland
```

Do not export `DISPLAY`, `QT_QPA_PLATFORM=xcb`, or forced GL driver overrides
until measurements show they are required. GTK and Qt both provide explicit
Wayland backend selectors. Binding the live socket into the chroot makes the
connection plausible, but only a device run can prove protocol and Mesa/kernel
compatibility.

## Desktop shell and applications

- **Waybar in the Debian runtime:** a 52-64 px top bar with launcher, compact
  workspaces/window title, network, audio, battery, clock, OSK, and Return to
  Gaming. Its layer-shell exclusive zone keeps maximized apps below it. Waybar
  has its own tray implementation, so Sway's compile-time tray disablement is
  not decisive; the shared session bus still needs testing.
- **Fuzzel in the Debian runtime:** an XDG desktop-entry launcher with large
  text/icons. It launches inside the chroot, so selected apps inherit the
  Debian filesystem and the clean Wayland environment. D-pad/Enter/Escape is
  the first navigation target; touch behavior is an acceptance gate.
- **foot in the Debian runtime:** a small native-Wayland terminal whose shell
  is the Debian environment. ROCKNIX's host `foot.sh` remains a diagnostic
  fallback, not the primary terminal.
- **Applications:** retain Thunar, Mousepad, pavucontrol, and
  `nm-connection-editor` where they operate natively on GTK Wayland. Remove the
  XFCE session, panel, desktop, window manager, Xorg, the rootfs Xwayland, and
  Onboard from the target image after dependency and fallback audits.

## Controller, touch, and OSK

The current InputPlumber approach is reusable. The provisional mapping is:

| Control | Desktop action |
| --- | --- |
| D-pad | Arrow keys |
| South | Enter/activate |
| East or Start | Escape/back |
| Select | Tab |
| Right stick | Pointer |
| Triggers | Left/right click |
| Bumpers | Scroll |
| L3 | Toggle OSK |
| Launcher | Dedicated tested key/chord or the panel item |

Do not hard-code the launcher or OSK Sway key symbol from Linux input names.
The current `KeyF13` is observed as `XF86Tools` in the XKB layout. Capture
`swaymsg -t get_bindings` and `wev` output on the RP6, reject collisions, and
restore any prior runtime binding.

Use the host's patched `wvkbd-mobintl`, not Onboard. First test the existing
hidden simple keyboard and its SIGRTMIN toggle. If terminal use requires the
full layout, follow ROCKNIX's QTerminal pattern: save the setting, stop the
keyboard supervisor, run one `full,nav,special` instance sized for both RP6
orientations, and restore the previous state. Manual toggle is the baseline;
automatic focus-driven popup is not assumed for ROCKNIX's pinned v0.17.

Touch mapping stays in Sway. Reapply `map_to_output` after the InputPlumber
transition and test every edge/corner in the device's transformed orientation.
No Xorg transformation matrix belongs in the new path.

## Graphics and video expectations

Keeping Sway alive removes compositor handoff and the known fullscreen
rootful-Xwayland repaint path. Lower overhead is plausible but unmeasured.

The first device run must prove each representative client's buffer path:
accelerated dmabuf/modifiers, another accelerated path, or wl_shm. Record logs
for GTK, Qt, foot, Waybar, and mpv. Exercise resize, overlap, focus, OSK,
suspend/resume, and repeated desktop/ES transitions for stale frames.

For mpv, use `vo=gpu`/`gpu-next` with a Wayland GPU context and keep the current
Iris H.264 preference with copy-back and software fallback until measured.
Upstream mpv documents copy modes as less efficient; successful decoder
initialization is not enough. Record decoder, GPU context, dropped frames, CPU,
memory, temperature/power, and A/V sync on representative H.264 files. Browser
hardware decoding remains unproven and outside the first milestone.

X11-only apps are not acceptance criteria. The host contains Xwayland, but
legacy X11 clients require a separate opt-in test before any support claim.

## Distribution choices

1. **Recommended: versioned Debian ARM64 runtime under `/storage`.** Continue
   the existing checksummed archive and persistent home, but make the rootfs a
   lean Wayland-client image. This works with the read-only host and is least
   coupled to ROCKNIX OTA contents. Measure the resulting archive/install size
   and retain package/license/source manifests.
2. **Host-only desktop wrappers.** The shipped swaybar, bemenu, foot, QTerminal,
   and wvkbd could form a tiny utility desktop, but the immutable host has no
   general application ecosystem and host foot is not the Debian environment.
   Useful as a recovery/diagnostic fallback, not the main product.
3. **Custom ROCKNIX image/packages.** Cleanest compositor/application
   integration, but it replaces the stock image, couples releases to the full
   firmware build, and changes the project's installation model. Not
   recommended for the first iteration.
4. **Flatpak, OCI, or system-extension runtime.** No required host support was
   established. These add lifecycle and graphics integration risk without
   solving a demonstrated problem; defer unless the chroot path fails.

## Validation sequence and acceptance gates

Implement only after the parallel uninstall/reinstall test is complete.

1. **Read-only inventory:** exact image/build ID; versions and presence of
   Sway, wvkbd, QTerminal, protocols, sockets, services, output/input names,
   renderer, and current runtime bindings. No service changes.
2. **Single native client:** while ES remains visible, launch a disposable
   Wayland client against the live socket, verify rendering/input, then remove
   it. This isolates chroot/socket/Mesa compatibility from lifecycle work.
3. **Supervised session:** stop only `essway`, launch foot plus Waybar on the
   dedicated workspace, return through the service, and prove exact input and
   keyboard-state restoration across success, client crash, service stop,
   Sway restart, and shutdown.
4. **Interaction shell:** add Fuzzel and representative GTK/Qt apps; test every
   controller path, touch edge, OSK layout, audio/network action, and panel
   module.
5. **Graphics/video soak:** repeat transitions, window damage tests, H.264
   playback, suspend/resume, external-display hotplug if supported, and an
   extended idle/load run. Compare memory, CPU, power, and thermal data to the
   current XFCE/Xorg baseline.
6. **Install/update/recovery:** fresh install, upgrade with preserved home,
   checksum failure, interrupted start, removal, reboot, and a ROCKNIX OTA.

Promotion requires all of the following: no frame corruption in native apps;
reliable controller, touch, and manual OSK operation; terminal proof that every
exit path restores ES and prior input state; measured acceptable playback and
idle overhead; and a recovery path that uses only `/storage` changes. Any
failure preserves the current released runtime as last known good.

## Explicit unknowns

- Whether the 20260927 image exactly matches the inspected public source and
  contains the expected wvkbd patches, QTerminal, protocols, and versions.
- Whether Debian Mesa and the host Adreno/Sway stack negotiate stable dmabuf
  formats/modifiers for every app, or fall back to wl_shm.
- Whether Waybar's tray/modules and settings apps behave correctly across the
  shared host session/system D-Bus, Pulse socket, sysfs, and NetworkManager.
- Exact RP6 controller key symbols/chords, focus semantics, touch transform,
  keyboard size, and full-layout usability.
- Whether Iris H.264 decode, Vulkan/OpenGL clients, suspend/resume, display
  hotplug, and long-running damage tracking are correct under this topology.
- Rootfs size savings, package/license obligations, OTA compatibility, and the
  migration plan for an existing installed runtime.

## Primary sources

- [ROCKNIX SM8550 options](https://github.com/ROCKNIX/distribution/blob/7cfc0cd256e1b5f9b689b25f3c05a78281302de3/projects/ROCKNIX/devices/SM8550/options)
- [ROCKNIX Sway package](https://github.com/ROCKNIX/distribution/blob/7cfc0cd256e1b5f9b689b25f3c05a78281302de3/projects/ROCKNIX/packages/wayland/compositor/sway/package.mk), [service](https://github.com/ROCKNIX/distribution/blob/7cfc0cd256e1b5f9b689b25f3c05a78281302de3/projects/ROCKNIX/packages/wayland/compositor/sway/system.d/sway.service), [desktop config](https://github.com/ROCKNIX/distribution/blob/7cfc0cd256e1b5f9b689b25f3c05a78281302de3/projects/ROCKNIX/packages/wayland/compositor/sway/config/config.desktop), and [boot selection](https://github.com/ROCKNIX/distribution/blob/7cfc0cd256e1b5f9b689b25f3c05a78281302de3/projects/ROCKNIX/packages/wayland/compositor/sway/autostart/111-sway-init)
- [ROCKNIX EmulationStation service](https://github.com/ROCKNIX/distribution/blob/7cfc0cd256e1b5f9b689b25f3c05a78281302de3/projects/ROCKNIX/packages/ui/emulationstation/system.d/essway.service)
- [ROCKNIX QTerminal/wvkbd integration](https://github.com/ROCKNIX/distribution/blob/7cfc0cd256e1b5f9b689b25f3c05a78281302de3/projects/ROCKNIX/packages/apps/qterminal/scripts/qterminal.sh) and [pinned keyboard package](https://github.com/ROCKNIX/distribution/blob/7cfc0cd256e1b5f9b689b25f3c05a78281302de3/projects/ROCKNIX/packages/apps/rocknix-touchscreen-keyboard/package.mk)
- [Sway 1.11 commands](https://github.com/swaywm/sway/blob/1.11/sway/sway.5.scd), [input](https://github.com/swaywm/sway/blob/1.11/sway/sway-input.5.scd), and [IPC](https://github.com/swaywm/sway/blob/1.11/sway/sway-ipc.7.scd)
- [systemd service restart and cleanup semantics](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [Waybar](https://github.com/Alexays/Waybar), [Debian 13 Waybar](https://packages.debian.org/trixie/waybar), [Fuzzel](https://packages.debian.org/trixie/fuzzel), and [foot](https://packages.debian.org/trixie/foot)
- [GTK 3 Wayland](https://docs.gtk.org/gtk3/wayland.html), [GTK backend selection](https://docs.gtk.org/gtk3/running.html), and [Qt Wayland](https://doc.qt.io/qt-6/wayland-and-qt.html)
- [wvkbd v0.17](https://github.com/jjsullivan5196/wvkbd/tree/v0.17)
- [mpv video output](https://github.com/mpv-player/mpv/blob/master/DOCS/man/vo.rst) and [hardware decoding/GPU context options](https://github.com/mpv-player/mpv/blob/master/DOCS/man/options.rst)
