# Desktop Mode architecture

This page describes `codex/bubblewrap-research`, not the currently published
`dev` installer. Published dev uses a rootful Debian chroot; this branch uses
non-root bubblewrap. The [migration ledger](../experiments/bubblewrap/README.md)
records exact build provenance, hardware evidence and remaining parity gaps.
The branch is not yet release-ready.

ROCKNIX supplies Sway, InputPlumber, audio, networking and device drivers.
Desktop Mode runs native Wayland applications in a Debian 13 ARM64 filesystem.
A privileged host supervisor prepares access and launches bubblewrap; application
and keyboard processes run as UID/GID 62000 with no supplementary groups or
capabilities and with no-new-privileges. It is not a virtual machine or a
per-application sandbox: desktop applications share home, display, audio and
network access. Firefox's own child-process sandboxes remain enabled.

## Session lifecycle

The Tools launcher starts the installed Desktop service. Preflight verifies the
RP6, output configuration, runtime and host tools. The session records workspace,
keyboard and input state, pauses EmulationStation and keeps the host Sway alive.
Private mounts expose persistent home, selected shared storage and the limited
device/service interfaces described below.

The session starts Waybar and applications on `98:Desktop`, applies temporary
window/input rules and owns a private wvkbd process inside the Debian runtime.
The host keyboard binary and persistent Sway configuration are not replaced.
Return to Gaming confirms before exiting; cleanup restores the previous host
keyboard/input state and EmulationStation. The existing service and storage names
are compatibility identifiers, not additional desktop components.

The supervisor journals temporary display/decoder ACLs before granting access.
Normal cleanup restores them; the service's post-stop cleanup also recovers
orphaned setup state after a killed supervisor. Panel or keyboard failure ends
Desktop so the native Gaming environment can recover. Real compositor-loss
recovery depends on ROCKNIX's Sway service restart policy and is slower than a
panel-only failure. Orderly reboot and crash tests do not establish power-loss
durability.

## Access boundary

- Read-only Debian root, private user/PID/IPC/mount namespaces and temporary
  runtime directories; persistent writable desktop home.
- Wayland socket, DRM render node and the identified RP6 Iris decoder. No raw
  input devices, DRM primary node or root Sway IPC socket in the app runtime.
- The existing host Pulse TCP endpoint and shared networking; these are deliberate
  service access, not network isolation.
- Fixed-command controls for window switching, layout, keyboard and network
  settings. The desktop cannot submit arbitrary host commands through them.
- Network editing uses a separate non-root editor and D-Bus proxy allowing
  NetworkManager access, not the broad host system bus. Its helper uses the host's
  existing nobody UID; that shared identity is a documented limitation.
- Shared data uses temporary idmapped mounts: desktop UID 62000 writes map to
  host root ownership without recursively changing shared files. Host-executed
  `/storage/scripts` is read-only pending a privileged-editing decision.

Separate home/shared bind mounts have a known GLib Trash limitation: matching
filesystem device IDs can select the home Trash, but rename across the mounts
fails. Permanent deletion is not a substitute for verified recoverable Trash.
See the migration ledger's GUI test and isolated reproduction.

## Runtime and presentation

- Waybar: app launcher, context-dependent window switcher, settings/status,
  keyboard toggle, battery, clock and return action.
- Fuzzel: favorites-first launcher with ordinary multiword search.
- wvkbd: privately built Simple typing plus one four-row symbols page, styled
  with the same Art Book-inspired palette and Roboto as the desktop.
- Sway: tabbed apps, adaptive floating utilities and Firefox Picture-in-Picture.
- GTK and Waybar: project-provided theme; applications retain native behavior.

Output-aware sizing does not establish support for untested devices.
See [keyboard build details](../experiments/wvkbd/README.md) and
[window policy](handheld-usability-followup.md).

## Graphics and media

Mesa Freedreno/Turnip provide native Wayland OpenGL/Vulkan. MPV prefers Qualcomm
Iris H.264 decoding with software fallback. Firefox uses a private pinned FFmpeg
build and a profile selecting the tested H.264 path. These libraries do not
replace host or other runtime applications' media libraries.

Capability flags alone do not prove acceleration or reliable playback. See the
[FFmpeg evidence and limitations](../experiments/ffmpeg/README.md) and
[RP6 validation](../tests/rp6-sway-validation.md).

## Installation boundaries

The installer modifies only project-owned files on writable storage. Personal
home remains separate from the replaceable runtime. Shared ROM/game directories
are real host storage, not disposable copies. Debian package versions depend on
repository state at build time; image/source pins and build metadata record
provenance. The bundled keyboard source and customizations ship with the runtime.

Debian package maintenance is an explicit host-root SSH operation using
`rocknix-maintenance` while Desktop is stopped. It supplies a writable Debian
root in a separate bubblewrap invocation without host home/storage/device access.
Package scripts are trusted administrator code; this is not a malicious-package
sandbox. Extra packages still do not migrate automatically when an update replaces
the rootfs. No host account, native keyboard binary or native ROCKNIX package is
replaced by this migration.

See [upgrades and recovery](upgrades.md) before replacing an installation.
