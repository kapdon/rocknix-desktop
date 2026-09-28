#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

while IFS= read -r file; do
  if head -n 1 "$file" | grep -Eq '^#!.*/(bash|sh)$'; then
    bash -n "$file"
  fi
done < <(git ls-files --cached --others --exclude-standard)
python3 - <<'PY'
import ast
from pathlib import Path
for path in Path('rootfs-overlay/usr/local/bin').iterdir():
    if path.read_text().startswith('#!/usr/bin/python3'):
        ast.parse(path.read_text(), filename=str(path))
PY

# Source only: no device checks, downloads, or system mutations are executed.
source ./install.sh
test_dir=$(mktemp -d)
trap 'rm -rf -- "$test_dir"' EXIT
printf 'test payload\n' >"$test_dir/$ASSET"
(cd "$test_dir" && sha256sum "$ASSET" >"$ASSET.sha256")
verify_bundle "$test_dir"
printf 'corruption\n' >>"$test_dir/$ASSET"
if (verify_bundle "$test_dir") >/dev/null 2>&1; then
  printf 'FAIL: corrupt payload accepted\n' >&2; exit 1
fi
printf 'invalid checksum\n' >"$test_dir/$ASSET.sha256"
if (verify_bundle "$test_dir") >/dev/null 2>&1; then
  printf 'FAIL: malformed checksum accepted\n' >&2; exit 1
fi
bash install.sh --help >/dev/null
bash uninstall.sh --help >/dev/null
if bash uninstall.sh --invalid >/dev/null 2>&1; then
  printf 'FAIL: unknown uninstall argument accepted\n' >&2; exit 1
fi
if bash install.sh --invalid >/dev/null 2>&1; then
  printf 'FAIL: unknown argument accepted\n' >&2; exit 1
fi
grep -q 'dev/install.sh' README.md
test "$VERSION" = development
grep -q 'button: LeftStick' payload/input/desktop.yaml
grep -q '/commands/custom/XF86Tools' rootfs-overlay/usr/local/bin/rocknix-xfce-first-run
printf 'PASS: syntax, checksum rejection, CLI and release consistency checks\n'
bash tests/persistence.sh
