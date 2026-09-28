# Upgrades and recovery

The fresh installer refuses existing runtimes. Home-preserving reinstall passed
local RP6 validation. `upgrade.sh` now implements explicit local-bundle upgrades,
same-commit no-op, home backup and rollback on ordinary activation failure.
The requirements below include remaining work: durable automatic power-loss
recovery and managed-file edit detection are not implemented. The GitHub installer
downloads and verifies published bundles before dispatching to this upgrader.
Keep the existing `/storage/.local/share/rocknix-xfce` layout for
compatibility; do not move personal data into the replaceable runtime.

## Ownership and detection

- Distinguish absent, recognized, incomplete and unknown installations. Check
  runtime markers, canonical paths, integration ownership and installed metadata;
  directory existence alone is not sufficient proof of ownership.
- Use `build-info` source commit to detect an already installed bundle. An equal
  commit is a no-op, not an instruction to reset settings. Commit hashes are not
  version ordering; require an explicit choice for downgrades.
- Missing metadata in older alpha installs requires an explicit migration path.
  Unknown, symlinked, mounted or partially installed targets fail closed.
- Preserve `home/` (including hidden files, initialization markers and metadata),
  `graphics-mode` and logs. Never extract a bundle over the active installation.
- Replace managed runtime, scripts, controller defaults, templates and metadata.
  Detect local edits to managed files and stop or archive them with a clear
  warning; do not silently discard them. Store a managed-file manifest in future
  installs to make this check reliable.
- Do not replace shared ROCKNIX storage, games, saves or host configuration not
  owned by this project. Extra packages in the old runtime do not migrate
  automatically; show that limitation before proceeding.

## Transaction and recovery

1. Acquire the same lock used by install/uninstall. Validate device, ownership,
   bundle provenance and enough space for staging, rollback and a settings backup.
   Download and check everything before disrupting the current desktop.
2. Ask the user to save work and exit to EmulationStation. Refuse a live desktop
   by default. Verify the service is stopped and no runtime mounts remain.
3. Back up settings while idle and record the old managed files and metadata in
   a unique recovery directory. Leave the live home in place; do not initialize
   it from new defaults.
4. Stage the new runtime on the same filesystem. Validate contents and run
   applicable preflight checks before activation. Track each replacement in a
   durable transaction journal: runtime plus three integration files cannot be
   replaced as one atomic rename. An interrupted operation must be recoverable
   on retry or boot without mixing old and new integration.
5. Activate the runtime and managed files, reload the service and verify the
   frontend remains usable. Record the new installed commit only after success.
   Do not auto-launch the desktop or declare visual success based only on service state.
6. On failure, restore old managed files and frontend operation. Retain rollback
   until the user validates the desktop. Never automatically purge recovery data.

Runtime rollback must not replace the live home with an old snapshot: that could
erase documents created after upgrading. Any settings restoration must be a
separate explicit operation, preserve newer files, and explain compatibility risks.

## Settings migrations

Apply cosmetic defaults only for missing settings. Version required migrations
and make them repeatable and narrowly scoped. The agreed exceptions are project
launchers, controller defaults and the L3 keyboard shortcut remain project-managed
fixes. Preserve changed
recognized home files in sibling backups before refreshing them. Never replace
unrecognized personal files or symlinks. Preserve unrelated settings.
Do not claim that every setting is untouched.

## Acceptance before publication

Build locally and test on the RP6 before pushing. Cover same-commit no-op,
recognized older installs, modified/unknown installs, insufficient space,
corrupt/incomplete bundles, active-session refusal, concurrent operations,
interruption at each activation step, rollback and reboot recovery. Seed the home
with documents and customized settings, then verify they survive upgrade and
rollback, including files created after the upgrade. Test Tools launch, display,
touch, controller, L3, audio and return to EmulationStation. Finally verify the
GitHub download/install path with the published candidate. Until this passes,
README must distinguish locally tested operations from unvalidated guarantees.
