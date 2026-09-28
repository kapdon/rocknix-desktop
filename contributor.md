# Contributing

## Pre-release maintainer workflow

Before the first public-ready release, maintainers may work directly on `dev`,
use temporary branches, and merge locally without opening pull requests. The
contributor PR and commit-size rules below are not gates for this bootstrap work.
Do not create a PR for maintainer work unless explicitly requested.

Validate locally **before pushing**: run `bash tests/check.sh`, commit locally,
then run `bash build-rootfs.sh` from that clean commit and verify its checksum
and `build-info`. Test affected installation, desktop and uninstall behavior on
the RP6 with that local bundle when changing those paths. Preserve a recovery
copy and user data; never uninstall a working desktop just to test a docs-only
change. Record what was actually tested and any remaining gaps.

Keep iterative edits, commits and builds local. Before publishing a candidate,
validate its local bundle end to end on the RP6: install, launch from Tools,
display/touch/controller/keyboard behavior, return to EmulationStation, and
uninstall/reinstall as appropriate, preserving user data and a recovery copy.
Only push the validated candidate to `dev` when ready for the final GitHub build
and download-path test. Batch changes rather than pushing every small fix.
The automatic GitHub build is the publication step, not a substitute for local
testing. Afterwards, verify the raw GitHub installer and rolling bundle URLs end
to end. Never use remote builds as the normal edit/test loop.

Development history may be consolidated into a clean, working initial release
before launch. Keep diagnostic evidence and recovery copies locally rather than
publishing a transcript of development experiments. Preserve meaningful tests,
accurate support claims, and required third-party attribution. Coordinate history
rewrites and release-tag changes explicitly; do not break published installer URLs
or silently replace release artifacts.

## Branches and pull requests

The following is the default workflow for external contributions:

Create your branch from an up-to-date `dev` and open the pull request against `dev`.
Use descriptive branch names such as `fix/keyboard-toggle`. Do not push directly
to `dev` for routine changes. The initial repository import is the exception.

Keep each commit **under 300 added lines** (`git show --numstat`). Split large
changes into cohesive, reviewable steps, not arbitrary fragments. Keep PRs focused;
aim for under 300 additions per PR too. Explain unavoidable generated-file or
large-test exceptions in the PR. Never commit built runtimes or release binaries.

Commit messages must use this form:

```text
type: short description
```

Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`.
Use the imperative mood and keep the first line under 72 characters, for example
`fix: restore the frontend after desktop logout`. Explain the reason in the body
when it is not obvious. Do not rewrite another contributor's branch without consent.

Include in each PR:

- What changed and why; link an issue if relevant.
- Commands/tests run and their actual results; identify checks not performed.
- Device model, ROCKNIX build, graphics mode and rollback steps for device changes.
- Screenshots or physical-device confirmation for visible/input behavior changes.

Wait for review and passing checks. Do not merge your own PR automatically. Prefer
squash merging small PRs; ensure the final title follows the commit-message format.

## Safety and code style

Use Bash strict mode, quote expansions, fail closed on unsupported devices, and
keep device-specific checks explicit. Never assume ROCKNIX has apt or a writable
root image. Keep persistent changes under `/storage`; preserve user homes and
refuse destructive overwrites. Separate experimental work from released defaults.

Preserve EmulationStation boot and return behavior. Test normal logout, failed
startup, controls, touch and session cleanup when changing lifecycle code.
Do not claim hardware acceleration solely from a capability flag.

Run `bash tests/check.sh` before submitting. Use ShellCheck when available.
Keep secrets, private device addresses, local logs and research checkouts out of
commits. Retain required third-party copyright/license notices. Do not add a new
device to the support table without testing on that physical hardware.

## Releases

During bootstrap, pushes to `dev` automatically publish the rolling `development`
channel. Its tag is a channel anchor, not the latest source revision; `latest.json`
and the bundle's `build-info` identify the source commit. Commit-qualified bundle
assets are immutable; only the latest pointer and release notes change. This is
an explicit exception to the versioned-release policy below.

The workflow restores and exports BuildKit layers using GitHub Actions cache
with an ARM64-specific scope and `mode=max`. The bundle build reuses that same
builder. Package layers are reused unless their Dockerfile inputs change;
overlay changes rebuild only the overlay and later layers. Payload, docs and
installer edits still repack a fresh commit-stamped bundle without reinstalling
runtime packages. Local builds use Docker's persistent local layer cache.
Caches are an optimization, not a requirement: a miss performs a full build.
Dependency refreshes must be deliberate and locally tested (use a fresh builder
or `docker buildx build --no-cache` with the same image inputs); unchanged apt
layers do not automatically pick up newer packages.

Build from a clean, tested commit. Publish versioned prereleases until fresh-device
installation and lifecycle tests pass. Upload the runtime archive and checksum to
the matching tag. Keep `install.sh`'s version and README URL synchronized. Do not
replace assets under an existing tag; publish a new version. Review dependency
license/source-distribution obligations before distributing runtime binaries.
