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
grep -Fq 'dev/install.sh' README.md
grep -Fxq 'mkdir -p /storage/rocknix-desktop && curl -fL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh -o /storage/rocknix-desktop/install.sh && bash /storage/rocknix-desktop/install.sh' README.md
grep -Fq '`--release TAG`' README.md
if sed 's@/storage/.local/share/rocknix-xfce@@g' README.md | grep -Eiq 'xfce|fxce|legacy'; then
  printf 'FAIL: retired desktop references in README\n' >&2; exit 1
fi
printf 'PASS: pinned alpha, rolling default and invalid release selection\n'
