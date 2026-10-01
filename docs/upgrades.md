# Install, update and uninstall

## Release selection

The default installer selects the latest published stable version. Add `--dev`
for rolling development, or `--release TAG` for a specific version. These
selection flags cannot be combined. The installer script is served from `dev`
for every selection; the bundle comes from the selected release.
See the [README installation commands](../README.md#install-or-update).

The public workflow has three operations: Install, Update and Uninstall.

| Operation | Desktop applications and home |
| --- | --- |
| Install | Replaces Desktop-owned applications, home, profiles and settings after an explicit overwrite warning; no recovery copy |
| Update | Preserves the existing Debian filesystem, installed applications, accounts, passwords and home |
| Uninstall | Removes native launch integration; retains Desktop data and trusted tools |

Shared ROCKNIX storage and native ROCKNIX accounts are outside these operations.

## Install and Update

Exit Desktop and leave native ROCKNIX running. Install/Update requires at
least 4 GiB free on `/storage` and 10% main-device battery. Other eligible
[SM8550 devices](devices.md) receive an automatic
untested-device warning on each invocation, before bundle download or storage
mutation. The answer defaults to No; `--yes` cannot bypass this warning.
Charging does not bypass the battery threshold; missing telemetry blocks
installation/update.

The installer downloads and checksum-verifies its bundle before
validating the existing installation. It checks host paths and ownership, then
boots a maintenance container with bundled tools to check mapped
identity, configured packages, APT and sudo. Guest code runs as mapped container
root, never as native host root. This validation may start and stop Debian;
it does not launch the graphical desktop or perform an APT install.

A healthy installation defaults to Update. An absent or invalid/partial
installation offers Install, with the data-overwrite warning. An invalid
installation is identified as invalid, not mislabeled as absent.

- `--install` selects replacement, including same-version replacement.
- `--update` refuses absent or invalid installations.
- `--yes` accepts the selected operation without prompting, **including data
  deletion when Install is selected**. Untested-device confirmation remains
  mandatory.
- `--check` checks device prerequisites only. It does not download a bundle,
  inspect availability, or establish installation health. It does not prompt;
  on eligible non-RP6 devices it reports that installation requires confirmation.
- `--release TAG` selects the named published build.
- `--dev` selects the rolling development build.

Normal installation checks GPU/decoder identities before classifying
or replacing Desktop data; `--check` does not run those checks. Device warning
confirmation and the later Install/Update confirmation are separate decisions.

Running the ordinary installer shows the available revision and asks before
Install/Update. For a healthy install already on that revision and bundle checksum,
Update is a no-op. Rebuilding the same revision can produce a new bundle;
that bundle still receives an Update. An explicitly selected older release is not a package-downgrade guarantee:
package transactions still enforce their compatibility/no-downgrade checks.

SHA-256 establishes download integrity, not independent publisher trust.
Bundles include privileged host integration code; use trusted project releases.

## Uninstall

For an installed LXC runtime, exit Desktop and use the project-owned wrapper:

```sh
curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash -s -- --uninstall --check
curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash -s -- --uninstall
```

Uninstall removes the recognized service, boot hook and Tools entry/artwork.
It does not erase `data/rootfs` or `data/home`. On an experimental device,
identity/model consent is still required, but live GPU/decoder endpoints are not.
Retained host state includes the model-bound consent record. A later
**Install replaces those retained trees**; it is not a data-preserving reactivation operation.

## Interrupted operations

Keep the downloaded bundle, staging directories and journals. Do not delete
update guards or manually start Desktop against a partial installation.

Running the ordinary installer checks the current state again. It refuses
Update when the installation is invalid and offers Install with the same
explicit data-overwrite warning. Choosing Install replaces Desktop data.

An interrupted host-file update can be retried with its original bundle and
checksum using that bundle's `upgrade.sh`; run `upgrade.sh --help` for the
options. Debian's package database must be healthy and fully configured. The
updater does not repair unfinished unpack/configure transactions. An existing
update journal refuses a different bundle; the public curl-pipe installer
does not automatically resume a guarded update.

Live processes, mounts, unsafe paths and customized native integration can
block replacement. An overwrite confirmation does not permit following links
or deleting unrelated data. Do not assume an interrupted operation rolled back
or that arbitrary power-loss recovery is available.

## Persistence and backups

Update keeps Debian and home in place, including numeric UID/GID mapping.
Guest integration is applied inside mapped LXC; it never executes guest-controlled
loaders, libraries or scripts as host root. Managed-file changes preserve local
edits beside `.rocknix-new` copies; conflicting systemd edits stop activation.

Make independent backups while Desktop and maintenance containers are stopped.
Preserve `data/` with numeric ownership, modes, links, ACLs and extended attributes.
Also preserve `managed/host/state/display/preferences.json` if you want the
confirmed resolution/scaling preferences. Do not restore active journals or
runtime state as if they were preferences. Shared storage needs separate backups.
Offline backup/restore has not been hardware-tested.
