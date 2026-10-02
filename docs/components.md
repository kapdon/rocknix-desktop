# Component build and release format

Development builds use `scripts/build-components.py`. Stable releases and the
explicit offline `build-rootfs.sh` builder still support the existing full
archive format. The download installer reads both formats.

The performance target is the configuration-only GitHub Actions build. Resolve
small immutable component descriptors **before** setting up Buildx. If a matching
artifact exists, reference its digest without downloading, loading, exporting,
compressing or uploading it again. BuildKit caches accelerate actual component
misses; they are not the release artifact store.

## Components and invalidation

| Component | Inputs that rebuild it |
| --- | --- |
| Guest base | Debian snapshot, runtime package recipe, Trash family, account/bootstrap policy |
| Trusted host runtime | Debian snapshot and host package recipe |
| Firefox media | Pinned sources, private FFmpeg build recipe, compiler snapshot |
| MPV media | Pinned sources, codec patches, compiler snapshot |
| Fuzzel | Launcher, Pixman and protocol sources/recipes, compiler snapshot |
| Keyboard | Sources, layout/patches, compiler snapshot |
| Guest integration | Overlay scripts, configuration, desktop defaults |
| Host integration | Host helpers, installer, service/input files, guest updater |
| Host theme | GTK configuration and ROCKNIX theme assets |
| Trash packages | Native package recipe, patches, sources and dependency snapshot |

Changing Waybar CSS rebuilds only guest integration. A GTK theme edit rebuilds
guest integration and host theme. Changing an MPV patch rebuilds MPV media.
Changing the Trash family rebuilds its transaction payload and fresh-install
base. Changing the packaging format/validator rebuilds components conservatively.

Keys contain source bytes, modes, links, selected Docker stages, build architecture
where applicable, and the explicit dependency lock. Commit IDs, clocks and
per-run export attestations are excluded. Keys identify inputs; separate SHA-256
digests identify actual compressed artifact bytes. Existing bindings are immutable.
The source commit and timestamp live in a small release manifest.

`build-support/components/dependencies.json` pins the Debian and Debian-security
snapshot used for component builds. Refresh it explicitly to adopt distribution
updates. The pinned base image alone does not freeze APT. Snapshot builds disable
only the historical index freshness deadline; signed indexes and package hashes
remain required. The guest base restores normal Debian update sources before
export; users' later APT security updates are not pinned to the build snapshot.
Private compiled components carry their source/license payloads.

Account creation and the randomly salted initial password run only in the stable
base target. Overlay changes do not rerun account initialization. Host theme
files are outside the host-runtime target. Fresh installs retain service owners,
hardlinks and setuid bits and use the existing one-time mapped ownership shift.

## Local commands

```sh
python3 scripts/build-components.py --plan
python3 scripts/build-components.py
# Resolve existing release assets before building on a fresh machine:
python3 scripts/build-components.py --repository kapdon/rocknix-desktop
```

Artifacts and immutable key bindings are in `build/component-store/`; the release
manifest, plan and timings are in `dist/components/`. Preserve the store between
local trials. No command above publishes or triggers a hosted build.

On a cross-host build, `ROCKNIX_TRASH_PACKAGES_DIR` can reuse an audited native
package directory. Its content is included in distinct local input keys and the
publisher refuses these local-override manifests. On hosts without `dpkg-deb`,
`ROCKNIX_PACKAGE_AUDITOR_IMAGE=sha256:...` may select an existing ARM64 Debian image
containing Python and dpkg to audit the package directory read-only without a
network. Normal Ubuntu ARM64 CI audits natively.

Assemble an install profile into a new staging directory, preserving ownership
under a single fakeroot session:

```sh
fakeroot -- python3 payload/bin/rocknix-components \
  --manifest dist/components/release.json --cache build/component-store \
  --profile install --output dist/component-install
```

The same command with `--profile update` omits the Debian base and includes the
existing audited package transaction. Assembly verifies every artifact and the
combined path/link graph before extraction. Corruption, path overlap, unsafe
links, unrepresentable owners and insufficient free space stop assembly.

## Publication and compatibility

The development workflow resolves first, conditionally creates a builder, builds
misses, then calls `scripts/publish-components.py`. Components live in prereleases
named `components-v1-<three input-key hex digits>`, separate from the rolling
`development` release. Content-addressed archives and input-key descriptors are
write-once. The publisher checks remote sizes/digests, skips uploaded components,
and refuses shards approaching the release asset limit. No garbage collector or
rolling legacy pruner deletes component assets.

Upload and verify all components, then an immutable release manifest and hashed
installer helper, before advancing `latest.json`. Publication is serialized by
the development workflow. GitHub's clobber operation is not atomic: the installer
retries the brief missing-pointer window; prior immutable manifests remain
available for recovery. A failed partial upload cannot change the old pointer.
Manual publishers must obey the same single-writer rule.

The installer initially stages the non-base profile, using candidate-owned host
tools for installation classification. It downloads the base only for Install.
The updater binds its existing interruption journal to the immutable manifest
checksum. It performs the existing mapped-container health checks, audited APT
transaction and host activation sequence. It does not execute guest-writable
binaries as host root or replace retained rootfs/home/accounts.

This first version optimizes **build reuse**. Device updates stage the complete
non-base component set, and assemble one complete guest managed-file union. They
do not yet transfer only changed files or reuse an installed host runtime based
on a receipt. That preserves current local-edit, deletion, package simulation,
newer-security-version and recovery behavior without inventing installed state.
The package transaction may decide no work is needed; a release reference is not
proof a package was installed. Debian transactions are not advertised as atomic
rollback. The full fresh-install archive is no longer a routine CI output.

## Validation and remaining acceptance

`fakeroot -- python3 tests/components.py` exercises real packing, composition and
updater application with small producer fixtures. It checks dependency invalidation,
zero producers on a warm run, one small compression on a CSS change, fresh-runner
metadata-only resolution, preserved ownership/setuid/symlinks, full union retention,
and fail-before-extraction corruption/path checks. Existing installer/update tests
continue to cover the legacy format and transaction safeguards.

Use real local component builds and repeated warm/config-change runs to measure
build time. Fixture timings are correctness evidence, not GitHub performance
claims. Native ARM64 GitHub timing and RP6 fresh-install, retained-update and
interruption acceptance remain separate gates before calling this production
validated. No hosted build or hardware operation is part of local source testing.

Implementation references: [BuildKit GHA cache authentication](https://docs.docker.com/build/cache/backends/gha/) and [GitHub release asset digests](https://docs.github.com/en/rest/releases/assets).
