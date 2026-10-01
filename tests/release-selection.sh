#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source ./install.sh
# Check-only exercises argument parsing without accessing or changing a device.
check_device() { printf 'selected=%s\n' "$VERSION"; }
output=$(main --release v0.2.0-alpha.1 --check)
grep -Fxq 'selected=v0.2.0-alpha.1' <<<"$output"
for tag in v0.2.0-beta.1 v0.2.0-rc.1 v0.2.0; do
  output=$(main --release "$tag" --check)
  grep -Fxq "selected=$tag" <<<"$output"
done
output=$(main --check)
grep -Fxq 'selected=latest' <<<"$output"
output=$(main --dev --check)
grep -Fxq 'selected=development' <<<"$output"
for tag in 'development' '../dev' 'v0.2.0-alpha.1/extra' 'v0.2.0-beta.1/extra' 'v0.2.0-beta' 'v0.2.0-preview.1' '--check' ''; do
  if (main --release "$tag" --check) >/dev/null 2>&1; then
    printf 'FAIL: invalid release tag accepted\n' >&2; exit 1
  fi
done
if (main --release) >/dev/null 2>&1; then exit 1; fi
if (main --check unexpected) >/dev/null 2>&1; then exit 1; fi
grep -Fq 'dev/install.sh' README.md
grep -Fxq 'curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash' README.md
grep -Fq '`--release TAG`' README.md
printf 'PASS: latest stable default, explicit dev/stable/alpha/beta/rc and invalid release selection\n'
