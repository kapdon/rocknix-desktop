# Changelog

## Highlights since v0.2.0

- Isolate Desktop-launched Steam shared memory so stopped sessions cannot accumulate new host allocations, and add Show Steam for running Keep Desktop sessions.
- Fix Gamescope SDL shutdown, coordinate window visibility with Vulkan presentation, and bound child-process cleanup when an application closes or the compositor crashes.
- Make Apps and Settings menus dismiss reliably, preserve manual controller overrides, and correct Fuzzel selection when clicking immediately after pointer entry.

<!-- development-changelog:start -->

<!-- development-revision: b79f02182f968a4e444a72fa61eba27d52b7d6b9 -->

## Changes since v0.2.0

- docs: reset development changelog after v0.2.0 \[skip ci\] ([443e23e](https://github.com/kapdon/rocknix-desktop/commit/443e23ec591675f16daf033794c62477461e06df))
- Fix guest Gamescope SDL teardown and bound reaper cleanup ([ec151b4](https://github.com/kapdon/rocknix-desktop/commit/ec151b48fc6991a1adccff96d43e7af8b3bd0377))
- fix(steam): isolate session shm and restore client access ([8cd429f](https://github.com/kapdon/rocknix-desktop/commit/8cd429f6a093a9bfab2dbfb65b6df545c3415f5e))
- Fix Desktop menu ownership and pointer entry selection ([0e40920](https://github.com/kapdon/rocknix-desktop/commit/0e409202511ae23b101708b38aeb94788044c113))
- Merge completed Gamescope teardown fix into dev \[skip ci\] ([58d50f8](https://github.com/kapdon/rocknix-desktop/commit/58d50f8c10a6e3b9678b12c3a127597f64c95302))
- Merge completed desktop menu fixes into dev \[skip ci\] ([4533c95](https://github.com/kapdon/rocknix-desktop/commit/4533c95e66a272dc15c77ffb6591735bd269e1e1))
- docs: summarize completed desktop fixes since v0.2.0 \[skip ci\] ([45c68a0](https://github.com/kapdon/rocknix-desktop/commit/45c68a00e381f00c6ccadd3c68a68886743d7020))
- Merge tested Steam lifecycle fix into dev \[skip ci\] ([b79f021](https://github.com/kapdon/rocknix-desktop/commit/b79f02182f968a4e444a72fa61eba27d52b7d6b9))

[Full comparison](https://github.com/kapdon/rocknix-desktop/compare/v0.2.0...b79f02182f968a4e444a72fa61eba27d52b7d6b9)

<!-- development-changelog:end -->
