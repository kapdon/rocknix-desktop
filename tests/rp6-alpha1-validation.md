# RP6 alpha 1 lifecycle validation

Test date: 2026-09-27 (device local time).
Device: Retroid Pocket 6, aarch64/SM8550, ROCKNIX nightly 20260927.
ROCKNIX build: `55752d441dc90caa1fa81e5e4658ba7cc6293b83`.

This test uses a clean application installation on the existing ROCKNIX device,
not a factory reset or newly flashed OS. The previous experimental runtime and
home are archived outside the active installation path; none were copied into
the new runtime/home.

## Uninstall

- Initial dry run rejected the live Tools entry because it differed from the
  stored template (the Xorg process-name fix). Ownership recognition was corrected
  to support both versions while preserving both in the backup.
- Revised `--check` passed without stopping the desktop or modifying installation.
- `--yes` returned 0; runtime/home and all three integration paths were archived.
- Confirmed all active installation paths absent afterward.
- Sway and EmulationStation were active; InputPlumber used its default profile.
- No system partition was modified. Archive retained for recovery.

## Published installer

Downloaded the unchanged script from:
`https://raw.githubusercontent.com/kapdon/rocknix-xfce/v0.1.0-alpha.1/install.sh`.
Script SHA256: `3177f1ea4464d771f8cd6a505bf87b90209218dea7915f82ba1389bd15216606`.

The script downloaded the bundle and checksum from the matching GitHub release.
Bundle SHA256: `8fa0684f385ecb5c9a6ea6542b0a7ef15771058e6a3d1e354f949cd2b2b85c1a`.

- Device `--check`: passed after uninstall.
- Full network download, checksum verification, extraction and install: exit 0.
- Desktop preflight passed; desktop was not automatically started.
- Fresh home directory was created; Sway and EmulationStation remained active.
- A second installer check refused the existing installation (exit 1).
- Uninstaller dry run recognized the freshly installed alpha integration.
- Host systemd printed a sixaxis template-dependency warning during unit verify;
  verification and installation still succeeded.

The user initially reported a missing Tools entry. The executable was present at
the configured Tools path, but EmulationStation predated the install. Restarted
only `essway.service` to rescan; both frontend services remained active and the
entry file persisted. README now gives that explicit post-install step.

Frontend visibility/launch, physical controls and logout confirmation are pending.
