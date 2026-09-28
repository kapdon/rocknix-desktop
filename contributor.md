# Contributing

## Pre-release maintainer workflow

Before the first public-ready release, maintainers may work directly on `dev`,
use temporary branches, and merge locally without opening pull requests. The
contributor PR and commit-size rules below are not gates for this bootstrap work.
Do not create a PR for maintainer work unless explicitly requested.

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

Build from a clean, tested commit. Publish versioned prereleases until fresh-device
installation and lifecycle tests pass. Upload the runtime archive and checksum to
the matching tag. Keep `install.sh`'s version and README URL synchronized. Do not
replace assets under an existing tag; publish a new version. Review dependency
license/source-distribution obligations before distributing runtime binaries.
