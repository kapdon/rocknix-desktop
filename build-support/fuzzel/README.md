# Upstream touchscreen launcher

Desktop menus use unmodified Fuzzel **1.15.0**. Debian trixie's 1.12 lacks native touch handling;
upstream added it in 1.13 and corrected scaled touch coordinates in 1.14.
Desktop uses its native touch handling.

`Dockerfile` cross-builds for ARM64 against the existing Debian guest ABI.
Fuzzel requires Pixman >=0.46 and wayland-protocols >=1.41. The latter is only
a build dependency. Pixman 0.46.4 is private to `/opt/rocknix-fuzzel/lib` and
resolved through the launcher's ELF RUNPATH. No global `LD_LIBRARY_PATH`,
`ld.so.conf`, system library replacement or native ROCKNIX change is used.
Children launched by Fuzzel do not inherit its RUNPATH. Existing Debian Fuzzel
remains package-managed; Desktop explicitly selects `rocknix-fuzzel`.

Source archives are checksum-pinned and shipped with the build recipe and
licenses. Fuzzel has no source changes. Version and checksum pins are updated
together; installation does not fetch from a moving upstream branch.

Every artifact build runs `check-artifact.py`: both ELF files must be ARM64,
the library must resolve inside the private directory, the launcher must be
executable with the exact private RUNPATH, and build sources/licenses must be
present. `tests/fuzzel-artifact.py` exercises rejection of broken artifacts.
These checks verify packaging and private dependency isolation.

The regular build exports this artifact and includes it in both fresh rootfs
and retained-data integration payloads. CI prepares the same artifact before
caching runtime layers.

Build independently from repository root:

```sh
docker buildx build --platform linux/arm64 --target artifact \
  --output type=local,dest=build/fuzzel \
  -f build-support/fuzzel/Dockerfile .
```
