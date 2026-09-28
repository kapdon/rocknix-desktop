# RP6 home-preserving replacement validation

Candidate: `cf385c21f465b4bd90ae0cc9bdb51f6f257bcd39` (local build, not pushed).
Device: Retroid Pocket 6, ROCKNIX nightly 20260927, kernel 7.2.0, aarch64.
Test date: 2026-09-28 UTC.

This tests the new uninstaller followed by the local bundle's device installer.
It is **not** a single-command or transactional upgrade, nor a GitHub download
test. The starting installation was the previously tested alpha runtime.

## Passed

- Local syntax/checksum/persistence tests and bundle build; package layers cached.
- Bundle SHA-256 verified on PC and RP6 before extraction.
- Existing home backed up before mutation; old runtime retained for recovery.
- Seeded personal text, hidden settings, binary content, a relative symlink,
  filenames with spaces and specific permissions/timestamps.
- After uninstall and reinstall: all 135 original/seeded home-file checksums
  matched; home device/inode stayed identical; seeded metadata matched.
- Reinstall accepted the retained-home marker; installation preflight passed.
- Installed metadata and runtime metadata exactly matched the bundle commit.
- Tools launcher started the desktop. Live XFWM compositing was disabled,
  keyboard toggle binding correct and battery helper returned live charge data.
- After desktop startup: seeded metadata/content preserved. Seven pre-existing
  files changed: Mesa caches (three), integration log, battery configuration,
  panel XML and desktop icon layout. Changed battery configuration had a backup.
- User confirmed correct display, touchscreen/controller/L3 operation, battery
  indicator and visible About Desktop Mode version.
- User confirmed logout returned to EmulationStation with working controls;
  service checks confirmed desktop inactive/success and Sway/EmulationStation active.

## Pending / not covered

- Power-loss recovery, rollback execution, reboot and OTA compatibility.
- A single-command upgrade implementation and GitHub installation of this build.

Dummy files and recovery copies were deliberately retained. No public push or
release was made as part of this test.
