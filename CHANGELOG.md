# Changelog

## Highlights since v0.1.0

- **Guest Gamescope cleanup:** Contain each launch in an unprivileged service,
  clear detached Wine helpers on exit or compositor loss, and keep the shared
  FEX server outside individual game lifetimes.
- **Gamescope app picker:** Keep “Launch with Gamescope” first in the initial
  Apps list, reuse installed app entries and display settings, and show a gamepad
  icon for both it and Steam games.
- **Gamescope display fitting:** Default nested games to the current Sway
  content area, with an option to use the full monitor resolution and a shared launcher for
  LXC X11/Wine games. Keep the game resolution stable while Gamescope scales
  window changes without forcing application windows fullscreen. Native DRM
  launching remains unchanged.
- **Component replacement:** Replace the system container on update while preserving
  home data and metadata; installed system packages and password changes reset.
  Legacy-export migration and interrupted replacement were tested on RP6.
- **Guest X11 and controllers:** Supply patched Xwayland, publish Sway work areas,
  expose the native virtual gamepad, and provide an always-available one-tap
  Desktop/Game override with secondary Gamescope detection.
- **Scoped host providers:** Add opt-in native graphics reuse with narrow read-only
  mounts. Packaged providers remain the default; native codecs remain diagnostic.
- **Simpler cached builds:** Cache finished archives in GitHub Actions and rebuild
  only changed layers. Publish one complete installation bundle per development
  or versioned release. CI validates and assembles the complete system; devices
  download and extract it without component assembly or integration generation.
- **Apps and Settings toggles:** Tap either button again to close its open menu.
- **Better cache reuse:** Preserve Trash packages and remote Docker layers, and
  include the keyboard layout in its compiler inputs.
- **Recorded release history:** Successful development builds automatically
  record all changes since the latest stable release in this changelog; release
  pages show curated highlights and link to the full history.
- **Native Steam games:** Launch installed ROCKNIX Steam shortcuts with a choice
  to close Desktop or keep it running, reusing the native Steam scope and shared
  library. Keep mode adds controller focus switching and a touch override.
- **Steam session recovery:** Handle Steam's update/restart request in Keep mode
  and block installation or maintenance until session recovery finishes.
- **Desktop file chooser:** Include the GTK portal backend and preserve its
  configuration through managed component updates. This does not fix native
  Steam's separate Browse dialog.

<!-- development-changelog:start -->

<!-- development-revision: ff70db2b52a9dca2971195158129c38d200b93b2 -->

## Changes since v0.1.0

- docs: clarify ROCKNIX project independence ([a70f578](https://github.com/kapdon/rocknix-desktop/commit/a70f578d935f2f073b713b3ab43c5e27b21c838f))
- fix: toggle Apps and Settings menus on repeated taps ([bef1135](https://github.com/kapdon/rocknix-desktop/commit/bef1135540ea28832ac8a3f2a04452b008cec364))
- perf: retain dependency layers across desktop overlay changes ([e146ce1](https://github.com/kapdon/rocknix-desktop/commit/e146ce17f4efdd02abae4f43d75899a765dd86aa))
- perf: compress release bundles with parallel fast xz ([8fb9fe8](https://github.com/kapdon/rocknix-desktop/commit/8fb9fe802f4115c5962d9a58f769897c283af5d8))
- perf: restore original release compression ([ee0c169](https://github.com/kapdon/rocknix-desktop/commit/ee0c1698c932d6844c0d6266198901876dc68de8))
- perf: isolate stable dependencies from mutable build inputs ([2f15fe8](https://github.com/kapdon/rocknix-desktop/commit/2f15fe81f10d6bb19756b790823db652dde288c2))
- fix: include keyboard symbols in compiler inputs ([4034218](https://github.com/kapdon/rocknix-desktop/commit/40342182b75601c88c1469847ac35f39a4702ac4))
- fix: integrate Apps and Settings menu toggles ([dca1b28](https://github.com/kapdon/rocknix-desktop/commit/dca1b28caffd5dc4c52d43d5d66e1445133c8996))
- feat: generate development notes since the latest stable release ([c1a1aec](https://github.com/kapdon/rocknix-desktop/commit/c1a1aec8e89b6ddeef3c9b78e58b132be5805599))
- fix: preserve cache reuse for packages and remote image layers ([7476ca8](https://github.com/kapdon/rocknix-desktop/commit/7476ca8ec156460e638f5ab1d13faa3792c4ab57))
- Build and publish reusable Desktop release components ([c3e9aa1](https://github.com/kapdon/rocknix-desktop/commit/c3e9aa1f2edc0e4edc45cfc05aac99ff982d0064))
- Reuse verified package artifacts for base-only rebuilds ([bcd3999](https://github.com/kapdon/rocknix-desktop/commit/bcd3999504bfb37ec1fb6e17afd7b49e9b82da09))
- Preserve component prefixes in extended tar headers ([aae9465](https://github.com/kapdon/rocknix-desktop/commit/aae9465933a5541ec1ea877d4532dd241c53b238))
- Give integration components exclusive ownership of managed defaults ([15d68ba](https://github.com/kapdon/rocknix-desktop/commit/15d68ba46fe4deb5784427b93dfcba7cabea710c))
- Keep component input keys stable across Python versions ([cb02f8d](https://github.com/kapdon/rocknix-desktop/commit/cb02f8df2edb0653a93acdcfaca65cdccf0e47be))
- Add repeatable local component build benchmarks ([07467c1](https://github.com/kapdon/rocknix-desktop/commit/07467c1eeb15ac582ad84e0acf4fca9fe9af8ed4))
- Record local component architecture validation and timings ([61cbb66](https://github.com/kapdon/rocknix-desktop/commit/61cbb664b128baed66ca088a1a20a98d82f0ea7d))
- Allow component benchmarks on development branches ([9f032bd](https://github.com/kapdon/rocknix-desktop/commit/9f032bdc53ee8ecb3b853c0349c0d9e6bf5576b6))
- fix: enable GTK file chooser in LXC desktop ([f28f4f0](https://github.com/kapdon/rocknix-desktop/commit/f28f4f02232db7f494a39bc771666e12d9b93491))
- Record native GitHub component cache benchmark results ([9594bc9](https://github.com/kapdon/rocknix-desktop/commit/9594bc9f036019b3871e2f2bf531e07ab9f8e107))
- Record successful development builds in the changelog ([a7775b2](https://github.com/kapdon/rocknix-desktop/commit/a7775b29a0a109c9842ebd3c5919e4e1090eebd2))
- Merge pull request #2 from kapdon/codex/component-builds ([caab3d1](https://github.com/kapdon/rocknix-desktop/commit/caab3d169064aa2050d8d8e495a4b20bf38f7090))
- Summarize development release notes and link the full changelog ([c95e0d4](https://github.com/kapdon/rocknix-desktop/commit/c95e0d4bab216f5a02a110640cc123cd535ed51a))
- feat: launch native Steam games with configurable Desktop lifecycle ([11cb43b](https://github.com/kapdon/rocknix-desktop/commit/11cb43bccb5200e179ed08dbda555903de588ed1))
- Use stock ROCKNIX DRM launch when closing Desktop ([60044bb](https://github.com/kapdon/rocknix-desktop/commit/60044bb75b541c558e167ef42f2272cf3ee92f79))
- Read Steam game menu from ROCKNIX desktop shortcuts ([925f0cf](https://github.com/kapdon/rocknix-desktop/commit/925f0cf55c7c343d56cdd50e22ca604d73b06f2c))
- Switch Steam controller profiles with focus and touch override ([6a61c09](https://github.com/kapdon/rocknix-desktop/commit/6a61c09bfb51073489a958a11559e6094971415f))
- Use a shared Gamescope presentation baseline for Steam sessions ([873b243](https://github.com/kapdon/rocknix-desktop/commit/873b2437ae0b44589c3bb27d21414b92ea6c7503))
- Merge remote-tracking branch 'origin/dev' into codex/steam-lxc-reuse ([8876837](https://github.com/kapdon/rocknix-desktop/commit/88768374c736e0503f45495c0747aa8af4239509))
- Include portal configuration in managed component updates ([260f51c](https://github.com/kapdon/rocknix-desktop/commit/260f51cfd945880bbe2d442349cca03eead51d0d))
- Reuse ROCKNIX native Steam scope and document compatibility tradeoffs \[skip ci\] ([cf88fdb](https://github.com/kapdon/rocknix-desktop/commit/cf88fdbcaf50ff2a45930524674260c01b0957c5))
- Fix Steam restart and maintenance recovery handling \[skip ci\] ([048c8ed](https://github.com/kapdon/rocknix-desktop/commit/048c8ed9135670cec5861c63675cdbf2877c840d))
- Backfill committed development changes in changelog \[skip ci\] ([5eafc7b](https://github.com/kapdon/rocknix-desktop/commit/5eafc7b3c7abe7432652885595f9be009dd68343))
- feat: scope native Vulkan providers to Desktop sessions ([db9bcee](https://github.com/kapdon/rocknix-desktop/commit/db9bcee6edd30b3c7240d0ec55305d5f6d60a6dc))
- feat: select matching native Mesa EGL and DRI components ([8dba4d0](https://github.com/kapdon/rocknix-desktop/commit/8dba4d03296ba91ca6c0ce6a6fb26278c6cafbb8))
- feat: scope native codecs to media applications and check provider loads ([55c236f](https://github.com/kapdon/rocknix-desktop/commit/55c236fc427e3416d92e91cb6d1032845523d3c3))
- fix: include the matching native GBM backend ([d32dc8c](https://github.com/kapdon/rocknix-desktop/commit/d32dc8c02256345e45dc2e3b340649674e4ff713))
- fix: include narrow provider paths for sandboxed browser graphics ([518abde](https://github.com/kapdon/rocknix-desktop/commit/518abde90921ac94f24d0aa933a4d2e4d272c435))
- feat: provide guest Xwayland for legacy desktop applications ([ee65e7a](https://github.com/kapdon/rocknix-desktop/commit/ee65e7ab1349ae22028fc12dda708108775ed95a))
- fix: include Xwayland package validation in the build context ([266cdaa](https://github.com/kapdon/rocknix-desktop/commit/266cdaa9d23ce0388d3b68e33dfd47b0036ece49))
- test: constrain offline X11 dependency updates ([f0d51af](https://github.com/kapdon/rocknix-desktop/commit/f0d51af2f56a4243a61dd979d7e54ef2cda8fde8))
- build: allow ignored scratch directory symlinks ([3f887b4](https://github.com/kapdon/rocknix-desktop/commit/3f887b4bfc1146ed50eb6926ce78cf301fcee6a6))
- docs: explain guest Xwayland and FEX cache reuse ([45a99d5](https://github.com/kapdon/rocknix-desktop/commit/45a99d504c318cee6c3f7539ae9c2b50931821d2))
- feat: deliver Xwayland through cached components ([cbc914b](https://github.com/kapdon/rocknix-desktop/commit/cbc914bcf43170b0a6d90b0a7472a52803c91774))
- feat: add recoverable container replacement transaction ([2d96a28](https://github.com/kapdon/rocknix-desktop/commit/2d96a28d7709796da2d6642f2ab4e4d32f2e9427))
- refactor: assemble complete component systems for updates ([adcac36](https://github.com/kapdon/rocknix-desktop/commit/adcac36ed607547b40aabc03a21f758a94750fee))
- feat: replace legacy containers while preserving home ([24f9bce](https://github.com/kapdon/rocknix-desktop/commit/24f9bcec7258d3cabcea3dc84d3a3f430159aba4))
- build: use components for local and versioned releases ([732e308](https://github.com/kapdon/rocknix-desktop/commit/732e308c6956234c00cfe2c13386e32bda83645a))
- test: verify home preservation across rootfs replacement ([40b5d39](https://github.com/kapdon/rocknix-desktop/commit/40b5d39acb5af98007b6eb9cd0fe6c2b7d9c2d2c))
- docs: clarify system replacement and password reset ([799a28e](https://github.com/kapdon/rocknix-desktop/commit/799a28efbd692862d204d305f160e9dec18065ac))
- test: expect one complete component assembly per install ([4728757](https://github.com/kapdon/rocknix-desktop/commit/47287578893cf4a8e6172d499bca3a8e91dcca39))
- test: record component replacement validation on latest dev ([ac74d64](https://github.com/kapdon/rocknix-desktop/commit/ac74d64fff3361a3c430a49d36fc1574fd1b96d0))
- fix: make controller switching available throughout Desktop ([2f89ada](https://github.com/kapdon/rocknix-desktop/commit/2f89ada995408d1093e71fc9f27011a3f50dabd6))
- feat: add one-tap controller override and guest Gamescope detection ([ea090d1](https://github.com/kapdon/rocknix-desktop/commit/ea090d1741483ba1357203074815745c8845a318))
- fix: honor compositor geometry for tiled X11 windows ([c151371](https://github.com/kapdon/rocknix-desktop/commit/c1513717137442fc07a537cbceb55e2e92a9973c))
- fix: expose native virtual gamepad to desktop applications ([d2518e7](https://github.com/kapdon/rocknix-desktop/commit/d2518e730c98ff68cd2bc6776fed6fd600c67a4f))
- fix: publish Sway work area to LXC X11 applications ([360524c](https://github.com/kapdon/rocknix-desktop/commit/360524cae05c876d0e8adbe36abc01c1c66bb637))
- fix: reconcile X11 fullscreen state with the compositor ([52a5ace](https://github.com/kapdon/rocknix-desktop/commit/52a5ace078c515401c5c3f688ab6d38a91cbc5ff))
- docs: record windowed-mode findings with LXC terminology ([964c475](https://github.com/kapdon/rocknix-desktop/commit/964c4753d41de8ba28db8cd0581d15bedede6911))
- docs: record LXC work-area validation and Wine handoff ([01e66e5](https://github.com/kapdon/rocknix-desktop/commit/01e66e56260fac8f4cb1a0e3f71ed2ffc90f61f1))
- docs: correct PD2 windowed validation and resize diagnosis ([ea1e722](https://github.com/kapdon/rocknix-desktop/commit/ea1e7223a0505e5689a4ec070ba3d1c8328ed7d5))
- feat: fit nested Gamescope displays to the desktop by default ([2374b61](https://github.com/kapdon/rocknix-desktop/commit/2374b61ca5c4c26fe07098b58e36ace8faf2875c))
- test: cover Gamescope display sizing and settings persistence ([197131d](https://github.com/kapdon/rocknix-desktop/commit/197131da1a9c5b92f5bf343a10377986353138f3))
- fix: package Gamescope from Debian contrib at its installed path ([b0f4e95](https://github.com/kapdon/rocknix-desktop/commit/b0f4e956722297bca8dd505d5fee32d288994e17))
- fix: find Debian Gamescope child process helpers ([0686f0a](https://github.com/kapdon/rocknix-desktop/commit/0686f0a1eb4e1067a90a77d5bd6242d40a212897))
- fix: install the trusted host Gamescope sizing helper ([fedd188](https://github.com/kapdon/rocknix-desktop/commit/fedd1881ab33f504ccd555e71571d63057114670))
- feat: add a pinned Gamescope app picker ([a947a9d](https://github.com/kapdon/rocknix-desktop/commit/a947a9d5a518f14e8210ac5066fedfc498b6dc48))
- docs: record 0.2.0 release readiness and repository cleanup ([f928ce3](https://github.com/kapdon/rocknix-desktop/commit/f928ce36a5442ab734f2661f486dc82eec92bb73))
- fix: contain guest Gamescope application teardown ([611e71b](https://github.com/kapdon/rocknix-desktop/commit/611e71b185e3ab7c9e481b9276f2d9d5264a5598))
- test: verify Gamescope cleanup and record RP6 evidence ([74229cf](https://github.com/kapdon/rocknix-desktop/commit/74229cff4099f9f13b5f22c23361a75a18731f5f))
- docs: keep agent workflow records in ignored experiments ([ee89c1e](https://github.com/kapdon/rocknix-desktop/commit/ee89c1e4bb794c6fcb18155488864d06330daf72))
- Keep changelog to release highlights and individual changes ([a6eef69](https://github.com/kapdon/rocknix-desktop/commit/a6eef696aab4d922a65c21b8a0a2bf15f3927122))
- chore: ignore local OMC workflow state \[skip ci\] ([974f2d5](https://github.com/kapdon/rocknix-desktop/commit/974f2d5785eaded560a5e75a455e235313fab792))
- build: cache finished layers and publish one installation bundle ([7d498cd](https://github.com/kapdon/rocknix-desktop/commit/7d498cd2146d3162838bc585f9a33dce047e8c7e))
- build: include Docker target selection in archive cache keys ([a17f979](https://github.com/kapdon/rocknix-desktop/commit/a17f97945bf74f510ceeb66371eb39bc3bdf8388))
- fix: stop forcing nested Gamescope windows fullscreen \[skip ci\] ([ee2234a](https://github.com/kapdon/rocknix-desktop/commit/ee2234af4eca053dd70755b9f1fa8dcaa0b29e10))
- build: assemble and validate release systems in CI \[skip ci\] ([0066557](https://github.com/kapdon/rocknix-desktop/commit/0066557ddec432ad37029d3a1eae12d265323f90))
- fix: extract assembled releases with ROCKNIX BusyBox tar \[skip ci\] ([ff70db2](https://github.com/kapdon/rocknix-desktop/commit/ff70db2b52a9dca2971195158129c38d200b93b2))

[Full comparison](https://github.com/kapdon/rocknix-desktop/compare/v0.1.0...ff70db2b52a9dca2971195158129c38d200b93b2)

<!-- development-changelog:end -->
