# Building ROCKNIX Desktop

Build from a clean, committed checkout with Docker Buildx and `fakeroot` for
non-root archive packaging. Local AMD64 hosts can build the ARM64 target.
The private Firefox FFmpeg and keyboard builds use an ARM64 cross-compiler
on the build platform. Docker's QEMU/binfmt support runs ARM64 image stages
when needed.
The native ARM64 Trash package build retains Debian rules and the mandatory
GLib test gate; emulation has ptrace limitations. GVfs rules defer runtime tests
to autopkgtest, so package compilation alone is not a GVfs runtime-test pass. A cross-host build can set `ROCKNIX_TRASH_PACKAGES_DIR`
to a complete audited artifact directory from a validated native ARM64 run.

From the repository root:

```sh
bash tests/check.sh
bash build-rootfs.sh
(cd dist && sha256sum -c rocknix-desktop-rp6-arm64.tar.xz.sha256)
```

On an AMD64 host, supply the complete unchanged native Trash package artifact
directory while using the ordinary local Docker builder:

```sh
ROCKNIX_TRASH_PACKAGES_DIR=/path/to/native/trash-packages bash build-rootfs.sh
```

The bundle is `dist/rocknix-desktop-rp6-arm64.tar.xz`. Inspect its `build-info` for
source commit, build time and image provenance. The builder exports independent
trusted host tools, the persistent Debian runtime and retained-update payloads.
Never extract over a running installation. For a local retained update, use the
bundle's `upgrade.sh --help` and supply `--bundle FILE --sha256 HASH`
with `--check` before `--yes`; ordinary
users should use the [download installer](../README.md#install-or-update).

Build inputs are defined in [Dockerfile.rootfs](../Dockerfile.rootfs),
[host tools](../build-support/lxc/Dockerfile.host-tools),
[Trash packages](../build-support/trash/README.md),
[Fuzzel](../build-support/fuzzel/README.md),
[wvkbd](../build-support/wvkbd/README.md) and
[Firefox FFmpeg](../build-support/ffmpeg/README.md).
MPV uses Debian's package-managed FFmpeg libraries. Firefox selects a separate,
minimal H.264/AAC library build only for its own process and children. Its
source archive is checksum-pinned; the archive and build recipe ship with the
runtime. Test affected graphics and media behavior on the RP6.
Source archives, patches and required licenses ship with the corresponding
artifacts. Review distribution obligations when changing dependencies.

Upstream suites are not a default build gate. Run them when relevant source
changes or explicit requirements call for them, and record which checks ran.
Keep the existing artifact and source checks. The GLib gate above remains
required for the mount-aware source changes. Test affected runtime behavior
on the RP6 using the local bundle.

Docker and CI reuse BuildKit layers. An unchanged APT layer does not fetch new
security packages. Refresh dependencies deliberately with a fresh builder or
no-cache build using the same inputs, then validate locally and on hardware.
A cache miss performs a full build; cache availability is not a requirement.

The manually dispatched [Development bundle workflow](../.github/workflows/development.yml)
builds the release bundle. Preserve the bundle/checksum, build logs and source
metadata; cached checks must identify their original execution rather than
claim a new run. Verify bundle checksum and
embedded source/image provenance before RP6 testing. Rolling publication is
restricted to `dev`; [versioned publication](../.github/workflows/release.yml)
is restricted to `main`.

See [contributing and publication](../contributor.md). Local checks/builds do
not prove device behavior or GitHub delivery.
