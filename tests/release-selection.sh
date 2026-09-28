#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source ./install.sh
# Check-only exercises argument parsing without accessing or changing a device.
check_device() { printf 'selected=%s\n' "$VERSION"; }
output=$(main --release v0.2.0-alpha.1 --check)
grep -Fxq 'selected=v0.2.0-alpha.1' <<<"$output"
output=$(main --check)
grep -Fxq 'selected=development' <<<"$output"
for tag in '../dev' 'v0.2.0-alpha.1/extra' '--check' ''; do
  if (main --release "$tag" --check) >/dev/null 2>&1; then
    printf 'FAIL: invalid release tag accepted\n' >&2; exit 1
  fi
done
if (main --release) >/dev/null 2>&1; then exit 1; fi
if (main --check unexpected) >/dev/null 2>&1; then exit 1; fi
grep -Fq 'v0.2.0-alpha.1/install.sh' README.md
grep -Fq 'bash /storage/install-desktop.sh --release v0.2.0-alpha.1' README.md
printf 'PASS: pinned alpha, rolling default and invalid release selection\n'
