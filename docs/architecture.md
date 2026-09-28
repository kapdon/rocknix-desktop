# Desktop Mode architecture

This page describes published `dev`. The current research branch replaces the
rootful app runtime with non-root bubblewrap; its exact boundary, missing
features, maintenance command and hardware results are tracked in the
[migration ledger](../experiments/bubblewrap/README.md). Do not apply the old
rootful privilege assumptions to that branch or treat it as release-ready.

ROCKNIX supplies Sway, InputPlumber, audio, networking and device drivers.
Desktop Mode runs native Wayland applications in a rootful Debian 13 ARM64
chroot. It is not a virtual machine or a security boundary.

## Session lifecycle

The Tools launcher starts the installed Desktop service. Preflight verifies the
RP6, output configuration, runtime and host tools. The session records workspace,
keyboard and input state, pauses EmulationStation and keeps the host Sway alive.
Private mounts expose devices, host services, persistent home and shared storage.

The session starts Waybar and applications on `98:Desktop`, applies temporary
window/input rules and owns a private wvkbd process inside the Debian runtime.
The host keyboard binary and persistent Sway configuration are not replaced.
Return to Gaming confirms before exiting; cleanup restores the previous host
keyboard/input state and EmulationStation. The existing service and storage names
are compatibility identifiers, not additional desktop components.

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

See [upgrades and recovery](upgrades.md) before replacing an installation.
