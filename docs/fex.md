# Optional native FEX reuse

Desktop remains a Debian ARM64 container. On the RP6, optional x86 translation
reuses ROCKNIX's existing Arch x86 filesystem and native FEX implementation.
No separate Ubuntu translation filesystem is provisioned by Desktop.

The host-defined mounts expose only:

| Host source | Container destination |
| --- | --- |
| `/storage/.local/share/fex-emu/RootFS/ArchLinux` | `/run/rocknix-fex/ArchLinux` |
| `/usr/bin/FEX` | `/run/rocknix-fex/bin/FEX` |
| `/usr/bin/FEXServer` | `/run/rocknix-fex/bin/FEXServer` |
| Resolved `/usr/lib/libfmt.so.12` | `/run/rocknix-fex/lib/libfmt.so.12` |

All four mounts are read-only, nosuid and nodev. Native binaries and their
ancestors must be root-owned and not group/other-writable. The Arch root may
also belong to native UID1000, as in ROCKNIX's unpacked image; ancestors must
remain native-root-controlled. Container identities map to different host IDs.
No broad host library directory, host loader, host libc or administrative
socket is exposed. Translation executes inside the container as its caller,
never as native host root.

`/usr/local/bin/FEX` delegates to `rocknix-fex`, which selects the mounted Arch
root and scopes the native library search directory to the translator process
and children. It does not edit host or user FEX configuration. Container-admin
changes to this wrapper do not become host-executed code.

Missing Arch data or native runtime files disable this optional capability;
ordinary Desktop startup remains available. Unsafe sources still fail closed.
The wrapper reports unavailable translation with exit 126. The dependency set
is RP6-specific, not a claim that arbitrary ROCKNIX FEX releases are compatible.
After a host update, a new Desktop session picks up the host files; dependency
and ABI compatibility must still be checked. Do not update host runtime files
during an active translated application session.

## Compatibility limits

FEX availability does not guarantee that an x86 application will work. Graphical
applications and controller support depend on the application and translator.
Ordinary Desktop remains ARM64; native ROCKNIX FEX packages are outside Desktop
update and uninstall.
