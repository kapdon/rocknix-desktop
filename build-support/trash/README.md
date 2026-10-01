# Mount-aware GLib/GVfs packages

The canonical LXC build includes Debian-patched GLib/GVfs packages with narrow
Linux mount-identity Trash changes. The package builder retains Debian patches
and native ARM64 GLib tests; GVfs Debian rules defer runtime tests to
autopkgtest. Package compilation alone does not prove those runtime tests.
`patch-trash.py` applies exact-match transformations to the pinned source trees;
`prepare-package.py` records them as a Debian quilt patch.

The patch uses statx mount identities and explicit fstab Trash hints for the
five selected shares. It does not add broad mounts, a privileged delete service
or a copy/delete fallback. Guest `rocknix-trash-policy` writes only its marked
fstab block: recognized configured versions enable hints, unknown versions
select no-Trash hints. User records take precedence. APT hooks disable/recompute
policy; direct dpkg changes refresh at next session startup. Restart file managers
after library changes. Policy errors do not block security APT updates.

`build-rootfs.sh` supplies the complete package artifact directory as the
`trash-packages` build context. Cross-host builds may set
`ROCKNIX_TRASH_PACKAGES_DIR` to native ARM64 artifacts. `check-packages.py`
checks versions, ownership, architecture and payload boundaries before
`install-image.py` applies the nine runtime packages. Sources and build metadata
ship under `/usr/local/share/rocknix-desktop/trash-source`.

Retained updates deliver the package/source archive inside mapped LXC in a
network-isolated transaction. Plans reject removals and unrelated changes.
Updates keep newer installed security packages instead of downgrading them.
Fresh builds fail if those versions require the Trash patch to be rebased.
No APT hold, global loader replacement or repository pin is installed. This does not guarantee arbitrary
future security revisions retain shared Trash behavior.

See [build requirements](../../docs/build.md).
