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
| Tools → Desktop, one tabbed workspace, persistent host Sway | Clean 8b7e9a0 package launched through actual Tools UI; panel/files render; preview verified after ES refresh | Recheck after remaining runtime changes |
| Apps favorites/search and keyboard-visible sizing | RP6 Apps launches; screenshot shows unclipped search with keyboard | Narrow logical outputs, long labels on final code |
| Confirm/back, West/North fields, Select cycle, R3 close | Injected RP6 InputPlumber key events cycle/close/dismiss correctly | Physical-controller user acceptance; West/North recheck |
| Keyboard Simple/symbols, panel and L3 toggle | wvkbd verified host UID 62000; both toggles exercised | Typing/layers after final migration, crash handling |
| Firefox | Retained profile, HTTPS rendering, seccomp content/RDD, real V4L2 H.264 frame output and PiP verified on RP6 | Broader streaming/media flow; final package |
| Vesktop without disabling sandbox | Actual Apps launch reaches Discord login; renderer seccomp=2 and distinct user/PID namespaces | Voice, screen sharing are not established by login screen |
| GPU | Real-session glmark2 uses freedreno FD740; non-root FFmpeg and Firefox use Iris; Wayland vkcube completes 1200 frames on Turnip Adreno 740 | Full media flow; final package |
| Audio/status/battery/clock | Non-root synthetic speaker-output monitor loopback passed; pavucontrol, Wi-Fi/battery/clock rendered | Audible output/user acceptance, microphone, device switching |
| Network editing | Settings and Apps use isolated editor/proxy; real inactive-profile rename/save/delete, proxy-only failure, singleton, R3 and normal/crash cleanup passed | Final package; physical-controller acceptance |
| Floating utilities and PiP | Audio utility floats; real Firefox PiP floats, shrinks above keyboard, and R3 closes only PiP | Recheck packaged runtime and narrow output |
| Shared data read/write | Desktop create/edit/rename passed; host file remains UID 0 | File-manager workflows on each actual shared mount; scripts workflow |
| Home persistence | Existing home migrated in place; retained Firefox profile opens; root/SSH maintenance reinstall passed | Upgrade/reinstall and final package permissions |
| Return confirmation and normal restoration | Latest non-root keyboard runtime: Escape/default Cancel retain desktop; confirmed Return restores ES, exact ACL, and removes all desktop processes/runtime | Recheck clean packaged installation |
| Crash restoration | Whole cgroup, keyboard-only and Waybar-only SIGKILL restore ES; no app processes; ACL and orphan runtime removed | Compositor loss, interrupted setup/reboot |
| Build/install/uninstall/provenance | Offline tests pass; clean 8b7e9a0 bundle built, installed after uninstall, and launched; home inode preserved; native-file hashes unchanged | Final revised package acceptance; GitHub release flow remains untested for this branch |

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

### Clean build and additional GPU check

Clean ARM64 build `8b7e9a0cf696664b8b4f6d9f535e6155e9101c12` completed.
Bundle SHA-256: `27d9d8fb9513d226ad3585d1393a00fbd47b976af004d0dfb34fced1515730c8`.
Archive checks show root-owned payload/bwrap, passwd mode 4755 and tmp mode 1777.
The image is `sha256:fe8c7d47d5c537469282f3192672c80335b3039c99ab7824e7b9764e4d7890eb`.
The package was subsequently installed on the RP6 as described below; remaining
feature gaps still prevent final acceptance.

On the manually deployed checkpoint 307aa86, the actual Apps validation entry
ran `vkcube --wsi wayland --c 1200 --width 640 --height 480` with
`VK_DRIVER_FILES=/usr/share/vulkan/icd.d/freedreno_icd.json`. It selected Turnip
Adreno 740 and completed normally as UID/GID 62000, CapEff=0, NoNewPrivs=1.
A repeat was visually checked in `/tmp/fresh-bwrap-vulkan-live.png`; device log
is `home/.cache/bubblewrap-vulkan.txt`. This excludes llvmpipe fallback for that
test, but is not a Vulkan performance benchmark.

### Clean packaged install on RP6

Installed the verified 8b7e9a0 bundle after running the existing uninstaller.
Deleted the exact archived old runtime (`uninstall.uO54mY`) before installation;
the consumed incoming bundle directory was also removed after successful tests.
No recovery copy remains from this replacement. The Desktop home stayed at the
same path and device/inode, with UID/GID 62000. Installed rootfs/payload ownership
is now 0:0, passwd retains 4755 and tmp retains 1777.
Hashes of `/etc/passwd`, `/etc/group`, NetworkManager.conf and the native
`/usr/bin/wvkbd-mobintl` were unchanged before/after installation and testing.

The actual EmulationStation Tools entry launched the package, not a direct
service start. ES needed its normal list refresh after reinstall to display the
new artwork; after restarting ES the preview and description appeared. Release
date is intentionally Unknown for this unpublished local build rather than
borrowing the old release date. Screenshot: `/tmp/fresh-bwrap-tools-final.png`.

Clean-package recovery tests retained Sway PID 2515, restored both recorded ACLs,
left no UID 62000 processes, removed runtime state/work, and reopened Desktop:

- Confirmed Return UI: Gaming restored in 2.75 seconds.
- Waybar PID 494286 killed: Gaming restored in 0.86 seconds.

Apps search with the keyboard visible had an unclipped header. Clicking the
on-screen Enter key launched Firefox; F13 hid the keyboard, F14 switched between
Firefox/Thunar, and F15 closed only Firefox. The retained Firefox profile opened
and rendered HTTPS example.org. Parent PID 496500 had UID 62000, CapEff=0 and
NoNewPrivs=1; content PID 496646 and RDD PID 496651 additionally had Seccomp=2.
Screenshots: `/tmp/fresh-bwrap-clean-launcher.png` and
`/tmp/fresh-bwrap-clean-firefox.png`. These are injected-input checks, not fresh
physical-controller user acceptance. Only Thunar was left open afterwards.

Replacing the runtime removed Debian packages added only to the old test rootfs,
including Vesktop and xdg-dbus-proxy; their prior test results are not tests of
this clean package. Home/profile data was retained. Network-helper integration
must add its actual dependency to the build before final packaging.

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

The clean 8b7e9a0 image exposed a missing test: `apt-get update` failed because
the maintenance tmpfs `/tmp` was 0755 and APT's verification user could not
create its temporary signature file. The helper now explicitly sets that private
directory to 1777. After deploying this fix, HTTPS index refresh and installation
of xdg-dbus-proxy succeeded with signature/checksum verification enabled.
The installed device is consequently 8b7e9a0 plus this maintenance fix and the
Debian-only proxy dependency, not an untouched clean artifact anymore.

### Network authorization investigation

On the RP6, `/etc/NetworkManager/NetworkManager.conf` already sets
`auth-polkit=false`; no host policy was changed. Debian-only
`xdg-dbus-proxy` 0.1.6-1+deb13u3 was installed for a bounded experiment.
`check-network-proxy.py` currently **fails**: the host system bus rejects
authentication for unregistered UID 62000, both directly and through the proxy.
The existing host `nobody` UID 65534 can call `GetPermissions` and receives
NetworkManager authorization. These were read-only calls, not connection edits.

A follow-up disposable probe ran both the proxy and client as the existing
host UID 65534. Filtered `GetPermissions` succeeded, while a call to
`org.freedesktop.systemd1` failed with ServiceUnknown. Temporary mounts and the
proxy were removed afterwards. No host account or policy was changed. This is
evidence for a separate, restricted editor helper, not approval to run the
whole desktop as nobody and not yet a functional network-settings UI.

A disposable systemd DynamicUser service started successfully, but libc
`pwd.getpwnam('rocknixdesktop')` could not resolve its account even after startup,
despite `passwd: files systemd` in nsswitch.conf. Both transient probe services
were stopped. Thus DynamicUser alone is not a verified solution on this firmware.
Do not expose the whole host bus or run the editor as root to bypass this failure.
The mixed-identity variant (proxy 65534, client 62000) also failed authentication.
That is consistent with the upstream proxy's documented forwarding of client
authentication data and proxy credentials:
[xdg-dbus-proxy source](https://raw.githubusercontent.com/flatpak/xdg-dbus-proxy/main/flatpak-proxy.c).

`check-network-editor.py` now proves a bounded **prototype**, not launcher
integration: separate editor/proxy as existing UID 65534, read-only Debian root,
private home/runtime/session bus, and only the filtered NetworkManager bus.
The supervisor passes a single pre-connected Wayland fd, so it adds no socket
ACL grant for nobody and mounts neither the host Wayland socket nor Sway IPC.
The editor has no ROM/shared-data mounts or device nodes beyond private /dev.
This is not an isolation boundary against other host processes using the same
nobody identity; the main desktop remains UID 62000.

RP6 prototype editor PID 507695 showed the existing Wi-Fi profile, floated at
1200x800, and exited normally on injected F15/R3. UID/GID 65534, CapEff=0,
CapBnd=0, NoNewPrivs=1 were inspected from the live process. Screenshot:
`/tmp/fresh-bwrap-network-editor.png`. Host account, NetworkManager configuration,
and native keyboard hashes remained unchanged. No connection was changed.
Proxy and private mounts were cleaned afterwards. Pending: production lifecycle
integration, dependency packaging, fixed Settings request, inactive-profile
save/delete tests, and failure/exit cleanup. This is still a parity gap.

### Integrated network settings, 2026-09-28

The newer `payload/bin/rocknix-network` replaces the prototype for normal use.
The root supervisor accepts only the fixed `network` request. Both Settings and
the Apps Network Connections entry use that request; no command text is accepted.
The helper uses a single-instance lock and a fixed root-owned temporary directory.
Both proxy and editor now run in bubblewrap with read-only roots, private PID/user
namespaces, no capabilities and disposable homes. Only the proxy sandbox sees the
host system-bus socket; only NetworkManager is allowed through to the editor.
The editor uses one connected Wayland fd, not a broad host socket/ACL grant.
The existing shared nobody identity remains a limitation versus a dedicated host
account; native account files are not changed.

Hardware checks on the 8b7e9a0 package plus branch patches:

- Opened the helper from panel Settings and separately from Apps search.
- Created disposable inactive Ethernet UUID `9d1409ed-57a8-432f-b4c1-f214d7c779ac`,
  bound to nonexistent `bwrap-test0` with autoconnect disabled. In the GUI renamed
  it from `bwrap-parity-test` to `bwrap-saved`, saved, verified by exact UUID, then
  deleted through the GUI. Active Wi-Fi and loopback UUIDs/devices stayed unchanged.
- Corrected a real layout defect: `Editing ...` forms now float above the main
  connection list. With the keyboard visible, both become tabs and the form's
  Save/Cancel remain visible. The separate unchanged confirmation dialogs still
  retain Sway's own behavior. A recreated layout fixture was deleted afterwards.
- Normal R3 close removed `/run/rocknix-network`.
- Return while editor/proxy active restored Gaming in 3.29 seconds, reaped editor
  and proxy PIDs 520872/520865, restored original display/decoder ACLs, removed
  runtime directories, and reopened Desktop.
- Waybar crash while editor/proxy active restored Gaming in 1.68 seconds, reaped
  editor and proxy PIDs 523509/523502, performed the same cleanup and reopened.
  Host Sway PID 2515 stayed unchanged in both cases.
- Native account, NetworkManager configuration and keyboard binary hashes still
  matched their pre-install values. No test network profile remains.

Screenshots: `/tmp/fresh-bwrap-network-integrated.png`,
`/tmp/fresh-bwrap-network-edit-fixed.png`, and
`/tmp/fresh-bwrap-network-edit-keyboard.png`. Full offline suite passes, including
new helper policy/cleanup tests. Impeccable guided the scoped window adaptation;
its mechanical detector returned no findings (not a substitute for these RP6
screenshots). Packaging now includes xdg-dbus-proxy and the Settings wrapper, but
this revision has not yet had a clean rebuild/install. Narrower logical widths and physical input remain
explicit acceptance work; the overall migration is not feature-complete.

`check-network-lifecycle.py` subsequently passed on the same patched RP6:
proxy PID 527668 and editor PID 527675 had UID 65534, zero effective/bounding
capabilities, no-new-privileges and private PID namespaces. Reopening Settings
kept exactly that one pair. Killing only the proxy closed the editor and removed
its runtime without stopping Desktop. Reopening then R3-closing cleaned up again.
This test changed no NetworkManager profiles. It uses injected input, not a
physical-controller acceptance test.

Startup cleanup now also covers rootfs bind/remount and home preparation, before
the display-access journal is created. Offline failure injection verifies that
each failure removes the temporary runtime and only unmounts a successful bind.
`check-early-setup.py` then passed on RP6 against candidate f5aefcb: injected
remount and home-preparation failures after a real rootfs bind each removed the
runtime and left Gaming active, with no display ACL journal created and without
calling home migration. The candidate was installed and normal confirmed Return
restored Gaming in 2.23 seconds, restored ACLs, removed all application processes
and runtime, and retained host Sway PID 2515. Desktop reopened with its non-root
panel and keyboard. Native account, NetworkManager and keyboard hashes matched.
This is still the older clean package plus branch patches, not a new bundle.
The next revision journals a random runtime path before creating it or mounting
anything. `check-early-setup.py ... kill-home` sent real SIGKILL after rootfs bind
and before home migration on RP6. The separate `--restore-access` invocation
removed the exact journaled runtime (`rocknix-bwrap-b7359aaeeb134173ade21c0042d7516a`)
and journal; Gaming remained active. This exercises the recovery command used by
ExecStopPost, not automatic service failure at that exact injection point.
After deploying the candidate, Waybar PID 541641 SIGKILL restored Gaming in 1.39
seconds with exact ACL restoration, runtime/process cleanup and unchanged Sway
PID 2515. Desktop reopened and native hashes matched. Full offline suite passed.
An older abandoned runtime `rocknix-bwrap-aav1g7eh` was separately identified;
its rootfs/home were empty and no live process mount namespace referenced it.
It was removed, not kept as a recovery copy. Reboot recovery remains unverified.

### Firefox hardware decoder verified on the bubblewrap runtime

Deployed final 4ae77a1 mountpoint guards; confirmed Return restored Gaming in
2.19 seconds with exact ACL/runtime cleanup and unchanged Sway PID 2515, then
reopened the non-root panel/keyboard. Firefox was launched through a temporary
Apps entry using the normal wrapper/profile and existing local H.264 fixture.
Only diagnostic environment variables were added, using Mozilla's
[Gecko logging mechanism](https://firefox-source-docs.mozilla.org/xpcom/logging.html):
`MOZ_LOG=PlatformDecoderModule:5,FFmpegVideo:5` and a user-cache log destination.
No decoding preferences or sandbox settings were changed.

`check-firefox-decoder.py` passed during playback: RDD host PID 551037, UID 62000,
zero effective capabilities, no-new-privileges and seccomp mode 2. Its mapped
codec was `/opt/ffmpeg-rpi-7.1.5/lib/libavcodec.so.61`, and its open decoder fd
pointed to `/dev/video0` (`qcom-iris-decoder`). Logs explicitly selected
`h264_v4l2m2m`, reported successful V4L2 initialization and 1160 hardware frame
outputs through PTS 38533333 microseconds. VA-API discovery failed but V4L2
succeeded; this is not software fallback. The test checks actual frame output,
not just advertised codec support. The fixture also visibly advanced.

Logs saved locally in `/tmp/rocknix-firefox-decoder-evidence/`; screenshots
`/tmp/fresh-decoder-start.png` and `/tmp/fresh-decoder-playing.png` show playback.
R3 closed Firefox and the temporary Apps entry was removed. Existing profiles
and media were retained. This proves local H.264 decode, not streaming-service,
DRM-content, audio-output or final clean-package acceptance.

### Non-root audio output path

`check-audio.sh` ran through a temporary Apps entry as UID 62000 against the
normal Pulse TCP endpoint. It refused concurrent playback streams, generated a
one-second 440 Hz signal, and captured only the default Speaker sink's output
monitor (not a microphone). With explicit 50 ms stream latency, it captured
201600 bytes including 47920 nonzero samples. Sink volume remained 20%, mute
remained off and the default route did not change. No pacat/parec process remained.
The first short captures used Pulse's default latency and returned no samples;
those attempts were not counted as passes. The runtime lacks Python and jq, so
the final harness uses its existing shell/awk/Pulse tools without added packages.

This proves the application-to-PipeWire speaker-output path, not audibility,
speaker quality, microphone capture or route switching. Temporary launcher and
harness files were removed, and generated audio was discarded. The text log is
saved locally at `/tmp/rocknix-audio-check.log`. Desktop remained active and
native account/NetworkManager/keyboard hashes still matched.

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
