# Bubblewrap migration — work in progress

Branch: `codex/bubblewrap-research`. Feature-parity baseline: live `dev`
`39fa395a34578d2373ce20b618bfc150f3eaa892`, checked on 2026-09-28.
This baseline differs from the branch's original `929c473` only in gallery docs.
Do not publish this branch as feature-complete yet.

The RP6's active Desktop Mode implementation is replaced, not run alongside the
old chroot desktop. The published dev installer remains the fallback. No recovery
copy of the old runtime is kept on the device. Existing home data stays in place.

## Implemented boundary

- Host supervisor retains Sway/input/EmulationStation lifecycle control.
- Host Python starts Debian's bubblewrap using its dynamic loader **outside** any
  chroot. All app and keyboard processes run as host UID/GID 62000 with no
  supplementary groups, no effective/bounding capabilities, and no-new-privileges.
- Private user/PID/IPC/mount namespaces; read-only Debian root; private runtime,
  session D-Bus and temporary files. Networking deliberately remains shared.
- Only the Wayland socket, render node, identified RP6 Iris decoder, read-only sysfs, selected storage and
  fixed-command controls are exposed. No root Sway IPC, host session/system bus,
  DRM primary node, raw input nodes or host runtime directory.
- Temporary Wayland and decoder ACLs are recorded before granting access. Normal shutdown
  restores it; ExecStopPost recovers after SIGKILL and removes orphaned runtime
  directories only after verifying that rootfs/home mounts are gone.
- Desktop keyboard runs inside the non-root session. Host controller bindings
  send a fixed toggle request, never signal a user-supplied host PID.
- Shared data uses temporary idmapped mounts (host root ownership maps to desktop
  UID 62000). No recursive chown/ACL modification of ROMs or shared data.
- `/storage/scripts` remains read-only because it can contain host-executed code.
  This is an explicitly unresolved privileged-editing workflow, not parity.

This is not a per-app sandbox. Apps share their home, network, display protocols
and audio access. Browser renderer sandboxes remain separate and must be tested.
The existing localhost Pulse endpoint is used; no native ROCKNIX configuration,
account database, keyboard binary or package installation is changed.

## Parity and acceptance ledger

| Requirement from dev / migration | Current evidence | Remaining acceptance |
| --- | --- | --- |
| Tools → Desktop, one tabbed workspace, persistent host Sway | Actual service starts and renders panel/files | Launch through Tools UI again with final package |
| Apps favorites/search and keyboard-visible sizing | RP6 Apps launches; screenshot shows unclipped search with keyboard | Narrow logical outputs, long labels on final code |
| Confirm/back, West/North fields, Select cycle, R3 close | Injected RP6 InputPlumber key events cycle/close/dismiss correctly | Physical-controller user acceptance; West/North recheck |
| Keyboard Simple/symbols, panel and L3 toggle | wvkbd verified host UID 62000; both toggles exercised | Typing/layers after final migration, crash handling |
| Firefox | Retained profile, HTTPS rendering, seccomp content/RDD processes, local H.264 playback and PiP verified on RP6 | Hardware video decode, broader streaming/media flow |
| Vesktop without disabling sandbox | Actual Apps launch reaches Discord login; renderer seccomp=2 and distinct user/PID namespaces | Voice, screen sharing are not established by login screen |
| GPU | Real-session glmark2 uses freedreno FD740; non-root FFmpeg decodes 30 H.264 frames with Iris | Vulkan, Firefox decoder selection and full media flow |
| Audio/status/battery/clock | Pulse connection, pavucontrol window, Wi-Fi/battery/clock rendered | Playback/microphone/device switching |
| Network editing | Status only; UI explains Gaming Mode fallback | **Missing: safe non-root network editor integration** |
| Floating utilities and PiP | Audio utility floats; real Firefox PiP floats, shrinks above keyboard, and R3 closes only PiP | Recheck packaged runtime and narrow output |
| Shared data read/write | Desktop create/edit/rename passed; host file remains UID 0 | File-manager workflows on each actual shared mount; scripts workflow |
| Home persistence | Existing home migrated in place; retained Firefox profile opens; root/SSH maintenance reinstall passed | Upgrade/reinstall and final package permissions |
| Return confirmation and normal restoration | Latest non-root keyboard runtime: Escape/default Cancel retain desktop; confirmed Return restores ES, exact ACL, and removes all desktop processes/runtime | Recheck clean packaged installation |
| Crash restoration | Whole cgroup, keyboard-only and Waybar-only SIGKILL restore ES; no app processes; ACL and orphan runtime removed | Compositor loss, interrupted setup/reboot |
| Build/install/uninstall/provenance | Offline tests pass; archive ownership regression passes; runtime manually deployed from branch | Clean ARM64 build; fresh packaged install/uninstall |

## RP6 observations, 2026-09-28

- Kernel 7.2.0, ROCKNIX nightly 20260927; existing Debian 13 rootfs based on
  published `929c473`, manually patched with branch files. This is **not** a
  published or clean-build artifact.
- Added Debian-only packages: bubblewrap `0.12.0-1~deb13u1`, acl `2.3.2-2+b1`.
- Nested `unshare -Ur` succeeds inside the non-root bubblewrap session.
- Vesktop parent PID 419694: host UID 62000, CapEff=0, NoNewPrivs=1.
  Renderer PID 419807: same host UID, Seccomp=2, user namespace 4026533391 and
  PID namespace 4026533392 versus parent 4026532773/4026532772. No `--no-sandbox`.
- GPU smoke: glmark2 2023.01, Mesa 25.0.7, renderer FD740. Short offscreen
  benchmark only; its score is not a performance comparison.
- Non-root keyboard PID 427701 confirmed after moving it out of the old helper.
- Shared-file test created `/storage/Desktop/.bubblewrap-parity.eL2a5a.renamed`
  from UID 62000; host stat reported UID/GID 0. Test file is disposable.
- Forced full-cgroup SIGKILL at 10:20:47 PDT: ES restored by 10:20:48;
  Wayland ACL exactly back to user=rwx/group=r-x/other=r-x, no added UID grant;
  `/run/rocknix-bwrap-state` and runtime `rocknix-bwrap-1gc3evu0` absent.
- Earlier startup failures (missing host chgrp, masked managed defaults) restored
  Gaming automatically. Fixed with numeric chown and explicit defaults mount.
- `check-failure-recovery.py` on the active RP6: keyboard-only SIGKILL
  (PID 434445) restored Gaming in 1.09s; Waybar-only SIGKILL (PID 451366)
  restored it in 0.86s. Both retained Sway PID 2515, left zero UID 62000
  processes, restored the exact saved Wayland ACL and removed runtime state/work
  directories. Each successful test reopened Desktop with a non-root keyboard
  and panel. No browser/document windows or recording were active before tests.
- Latest Return UI screenshot: `/tmp/fresh-bwrap-return-latest.png`. Actual panel
  click opened confirmation with Cancel selected; Escape and Enter-on-Cancel
  retained Desktop. Down/Enter confirmation restored Gaming, left zero desktop
  UID processes, retained Sway PID 2515, restored ACL and removed runtime state.
  The first harness restart hit an unnecessary `reset-failed` error on a cleanly
  unloaded unit; fixed the harness to reset only failed units, then retested.
- Firefox launched from Apps as UID 62000 and rendered `https://example.org`.
  Parent PID 458568 had CapEff=0, NoNewPrivs=1; RDD PID 458688 and content
  PID 458815 had Seccomp=2 and distinct user namespaces (4026533391 and
  4026533636 versus parent 4026532779). No debugging or sandbox-disable flags.
  Screenshot: `/tmp/fresh-bwrap-firefox-example.png`.
- Existing local H.264 fixture played with visible frame/time progression
  (0.467s to 27.633s in captured frames). Real PiP floated at
  `(1132,548) 768x432`; showing the keyboard moved/shrank it to
  `(1436,341) 464x261`, above the panel/keyboard boundary. F15 (R3 equivalent)
  closed only PiP, leaving the main Firefox window. Screenshots:
  `/tmp/fresh-bwrap-pip.png`, `/tmp/fresh-bwrap-pip-keyboard.png`.
  This earlier playback/layout check was **not hardware decoder evidence**:
  that revision exposed neither video node.
- Decoder access implementation: `/sys/class/video4linux/video0/name` must be
  exactly `qcom-iris-decoder` and `/dev/video0` must be a character device before
  granting access. The encoder (`/dev/video1`) stays hidden. Original decoder
  ACL is journaled before modification and restored on normal/failed exit.
- With decoder access enabled, the actual Apps validation command ran FFmpeg
  as UID 62000 and decoded 30 frames of the existing 1280x720 H.264 fixture.
  Output selected `/dev/video0`, `iris_driver`, `Iris Decoder`, H264/NV12 and
  completed normally. This proves real non-root hardware decode, but not yet
  Firefox's decoder choice. A subsequent Waybar crash test checks both saved
  device and Wayland ACLs, along with the existing lifecycle cleanup assertions.

Local screenshot evidence is in `/tmp/fresh-bwrap-desktop.png`,
`/tmp/fresh-bwrap-vesktop.png` and `/tmp/fresh-bwrap-launcher-keyboard.png`.
These are local test artifacts, not screenshots of the final release.

## Reproducible checks

### Debian package maintenance (branch-only)

Return to Gaming first. From root SSH, use:

```sh
/storage/.local/share/rocknix-xfce/bin/rocknix-maintenance -- apt-get update
/storage/.local/share/rocknix-xfce/bin/rocknix-maintenance -- apt-get install PACKAGE
```

This is an explicit administrator command, not desktop sudo or a root IPC
endpoint. It shares installer/runtime locks and refuses an active Desktop or
unfinished upgrade. A writable Debian root is exposed to trusted package scripts,
but home/shared storage, hardware devices, and host service sockets are not.
Debian service startup is denied by policy-rc.d. It retains selected package
management capabilities, not SYS_ADMIN or MKNOD. It is not a security boundary
against malicious administrator-supplied packages. Package changes are not
guaranteed to survive replacing the runtime with a new release bundle.

RP6 test: refused while Desktop was active; after returning to Gaming,
`apt-get check` and reinstall of `xdg-dbus-proxy` 0.1.6-1+deb13u3 succeeded.
This proves a small real Debian package operation, not every package maintainer
script. Generic package installation still requires normal administrator judgment.

### Network authorization investigation

On the RP6, `/etc/NetworkManager/NetworkManager.conf` already sets
`auth-polkit=false`; no host policy was changed. Debian-only
`xdg-dbus-proxy` 0.1.6-1+deb13u3 was installed for a bounded experiment.
`check-network-proxy.py` currently **fails**: the host system bus rejects
authentication for unregistered UID 62000, both directly and through the proxy.
The existing host `nobody` UID 65534 can call `GetPermissions` and receives
NetworkManager authorization. These were read-only calls, not connection edits.

A disposable systemd DynamicUser service started successfully, but libc
`pwd.getpwnam('rocknixdesktop')` could not resolve its account even after startup,
despite `passwd: files systemd` in nsswitch.conf. Both transient probe services
were stopped. Thus DynamicUser alone is not a verified solution on this firmware.
Do not expose the whole host bus or run the editor as root to bypass this failure.
Remaining options need evaluation: a narrow non-root network-editor runtime
using a host-resolvable identity, or a typed network broker. Neither is implemented
or approved as a parity claim. The current desktop and host account files remain
unchanged by these probes; temporary probe directories are removed automatically.

Packaging now extracts and repacks the Docker export in one root/fakeroot
context. `tests/package-rootfs.py` exercises the real packager with a tiny export
fixture: root-owned executables, a setuid executable, service-owned data, and
sticky `/tmp` all retain their metadata. Project host payload files are
normalized to root ownership without blanket-chowning Debian service data.
This passed locally outside the Codex filesystem sandbox (which rejects the
fake ownership syscalls). It is not evidence of a clean ARM64 package or install.
Both CI workflows install fakeroot before running the regression suite.

`bash tests/check.sh` exercises offline contracts. `check-idmap.py` runs on host
RP6 Python as root, creates only disposable files, and cleans its private mount.
`check-session.sh` runs as the desktop user; the companion temporary desktop entry
lets it use the exact app environment through Apps. Remove that test entry and its
one generated shared file after collecting results. No account login is needed.

Further work must retain the original dev feature list. Missing features above
must not be reclassified as completed simply because the safer subset works.
