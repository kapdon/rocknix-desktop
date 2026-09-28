# Desktop Mode keyboard

Private wvkbd v0.17 build, bundled inside the Debian runtime. It does not
replace `/usr/bin/wvkbd-mobintl`, change the native ROCKNIX keyboard package,
or install host overrides. The existing host keyboard restoration is unchanged.

- Upstream Simple typing geometry, Compose retained, readable labels.
- One custom four-row numbers/symbols page; ABC returns directly to typing.
- No navigation page or arrow keys in the two-page cycle.
- Art Book palette and Roboto configured by `launch-sway-desktop`.
- ROCKNIX output-pinning and no-popup patches retained (from the distribution
  keyboard package); upstream source archive is checksum-pinned in Dockerfile.
- Pointer-enter coordinates initialized so the first click after Sway hides
  the pointer does not require an extra motion event.

The Docker builder cross-compiles arm64. The source archive, license and
customizations ship under `/usr/local/share/wvkbd` in the runtime.

Device preview: installing the binary and launcher directly is a local test,
not proof that a published release bundle contains these changes.
