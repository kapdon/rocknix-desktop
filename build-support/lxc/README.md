# Trusted host tools

[Dockerfile.host-tools](Dockerfile.host-tools) builds the independent ARM64
host runtime used by the LXC supervisor and protected audio/network helpers.
It includes LXC, uidmap, ACL/mount utilities, slirp4netns, PulseAudio,
bubblewrap, D-Bus proxy and the network editor. Bubblewrap isolates the trusted
non-root helpers; LXC runs Debian applications.

The installed host-tools tree stays outside guest-writable rootfs/home and
is not mounted broadly into Debian. Package/version manifests are recorded by
the builder. ROCKNIX supplies native kernel drivers and services.

See [build requirements](../../docs/build.md),
[privilege boundaries](../../docs/architecture.md), and
[device probes](../../tests/device). Source checks and host-tools
compilation do not establish installed hardware behavior.
