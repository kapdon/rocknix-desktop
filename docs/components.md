# Component build and release format

Local, development and versioned builds use `scripts/build-components.py`.
`build-rootfs.sh` invokes the same component builder. Historical full archives
remain readable for explicit fresh installs; Update requires a component manifest.

Actions caches each finished compressed archive independently. Cache hits skip
compilation, export and compression. Cache misses rebuild only the affected
parts, with BuildKit layer caching available for compiler work. Caches are
optional and disposable: an empty or evicted cache causes a normal rebuild.

Each release publishes one assembled system archive. CI validates every component
and the combined path/link graph, assembles the rootfs, and generates integration
metadata before compressing the final archive. The device verifies its download
checksum, extracts it once, and installs it; it does not assemble components or
generate integration archives. The final archive is a durable public download;
installers never depend on Actions caches or run artifacts. There are no individual
component releases or registry packages.

## Components and invalidation

| Component | Inputs that rebuild it |
| --- | --- |
| Guest base | Debian snapshot, runtime package recipe, Trash family, account/bootstrap policy |
| Trusted host runtime | Debian snapshot and host package recipe |
| Firefox media | Pinned sources, private FFmpeg build recipe, compiler snapshot |
| MPV media | Pinned sources, codec patches, compiler snapshot |
| Fuzzel | Launcher, Pixman and protocol sources/recipes, compiler snapshot |
| Keyboard | Sources, layout/patches, compiler snapshot |
| Xwayland | Satellite sources, compiler snapshot |
| Integration | Guest overlay, host helpers, installer, service/input files and GTK theme |

Trash packages are a ninth **build-only cache entry**, used to produce the guest
base. They are not an installed layer or a separately published download.

Changing Waybar CSS, a launcher flag or GTK theme rebuilds only integration. Changing an MPV patch rebuilds MPV media.
Changing the Trash family rebuilds its transaction payload and fresh-install
base. A base-only bootstrap change consumes the cached package artifacts instead
of rebuilding the native packages. Producer and archive ownership policy changes invalidate components conservatively.
Cache transport, release publication and CLI changes do not invalidate compiled
archives; guest/host helper changes rebuild integration.

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

Fakeroot ownership exists only for that session. Inspect or archive the result
inside the same fakeroot session; do not deploy its loose directory as a
metadata-preserving copy. The device installer extracts the completed archive as actual host root.

The same command with `--profile update` includes the same complete system.
A downloaded release manifest fetches its CI-assembled system archive, verifies
the checksum and embedded provenance, and extracts it with numeric owners and
permissions preserved. Component validation and integration generation run only
in the CI packaging step. `packaging-timings.json` records assembly/validation and
compression separately from component build timing.

## Publication and compatibility

The development and versioned workflows calculate exact input keys, restore each
finished archive with `actions/cache`, resolve misses, and set up Buildx only when
compilation is necessary. Both use the same builder and dependency lock.

Publication uploads and verifies the bundle, checksum, manifest and bootstrap
helper before advancing `latest.json`. Only `development` and explicit versioned
releases receive public assets. Partial uploads leave the previous pointer intact.
The manifest retains format 2 so the installer and transactional updater keep
using the established complete-system replacement path. Its `bundle` field
identifies the one immutable tar download by release tag, name, size and SHA-256.

For a branch benchmark, dispatch `development.yml` with `benchmark=true`. It
builds and populates Actions caches, but changes no releases, tags, pointers,
notes or changelog. Cached entries are scoped according to GitHub's branch cache
rules; benchmark and release comparisons should use the same branch. Plans and
timings are saved as workflow artifacts. A cold build seeds the caches; subsequent
runs measure reuse and selective invalidation. Cache transfer and bundle upload
time remain part of the hosted job even when no compiler runs.

Publication is serialized by the workflow. GitHub's pointer clobber operation is
not atomic; the installer retries a brief missing-pointer window. Manual
publishers must obey the same single-writer rule. Keep bundles referenced by
supported releases when retiring old development assets.

After a successful development publication, Actions records the full cumulative
commit history in [CHANGELOG.md](../CHANGELOG.md), comparing the published source
commit with the latest stable release. The release page shows a short summary
from the changelog's `Highlights since <stable tag>` section and links to the full
file. Maintain those highlights alongside feature changes; they are outside the
generated history. If the stable tag changes before its highlights are updated,
release notes show the new comparison's commit count and full-changelog link
instead of repeating an old release's highlights. The generated section replaces the previous
change list; the file contains only highlights and commit details, while Git history retains older
snapshots. The workflow saves both Markdown files with its timing artifacts.

A separate `docs: record development changelog [skip ci]` commit changes only that
file on `dev`. The release manifest and a hidden changelog comment identify the
source commit actually built. These bot commits are omitted from future change lists,
and changelog files are outside component inputs, so recording or refreshing notes
does not rebuild components. Publication failure or benchmark mode leaves the
changelog untouched. The update preserves unrelated concurrent commits and fails
if someone edits the changelog during the build; it never force-pushes `dev`.

Install and Update extract the same CI-assembled system, including the guest
base. Updates replace `data/rootfs`; they never run APT or copy an overlay into
the old container. Existing monolithic LXC installations with the separated
storage layout migrate through this same path. Home and shared storage are
preserved; packages, passwords and edits inside the old rootfs are replaced.

The updater checks the candidate in an isolated mapped maintenance container,
then switches rootfs and trusted host integration under a checksum-bound journal.
Activation failure restores the old rootfs and host integration. After successful
activation it removes the old rootfs. Repeating the same update after interruption
finishes cleanup or rolls back and retries. Staging requires room for the complete
new system and temporary host backup; the old rootfs is renamed, not copied.

Build reuse remains component-based: unchanged immutable artifacts need no
recompilation or per-component recompression. CI assembles and compresses the final
system archive for each release; device updates extract that finished rootfs.
The `trash-packages` artifact remains a build-cache dependency for the guest base;
neither install nor update delivers an offline package transaction to the device.

## Testing component builds

`fakeroot -- python3 tests/components.py` exercises real packing, composition and
updater application with small producer fixtures. It checks dependency invalidation,
zero producers on a warm run, one small compression on a CSS change, fresh-runner
finished-archive cache restoration and cache eviction, preserved ownership/setuid/symlinks, full union retention,
and fail-before-extraction corruption/path checks. Replacement tests exercise interruption boundaries, rollback and home identity
preservation. These filesystem fixtures do not establish RP6 runtime acceptance.

After a real local build, run `python3 scripts/benchmark-components.py` for three
warm and three CSS-change trials using the real cached artifacts. It edits a
disposable source copy, rejects any Docker invocation, and records compression
input sizes in `dist/component-benchmark/results.json`. Use a constrained Ubuntu
container for runner-like packaging measurements; retain the component store
and the same native-package override environment used for the initial build. Fixture timings are correctness evidence, not GitHub performance
claims. Test development-channel delivery and RP6 installation, replacement
updates and recovery separately. Source tests and build benchmarks do not
establish hardware behavior.

Implementation references: [BuildKit GHA cache authentication](https://docs.docker.com/build/cache/backends/gha/) and [GitHub release asset digests](https://docs.github.com/en/rest/releases/assets).

## Xwayland delivery

The Xwayland component carries the guest-owned Satellite bridge and its source
and license files. Debian X11 dependencies are installed in the guest base.
Install and Update both receive them in the new rootfs; there is no retained
container package updater or compatibility path for older component manifests without the bundled layout.
