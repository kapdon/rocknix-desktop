#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source ./install.sh
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
WORKSPACE="$scratch/project"
mkdir -p "$WORKSPACE"
select_installation_paths
test "$BASE" = "$WORKSPACE/managed/host"
test "$DATA" = "$WORKSPACE/data"
check_install_target
mv "$WORKSPACE" "$scratch/real"
ln -s "$scratch/real" "$WORKSPACE"
if (check_install_target) >/dev/null 2>&1; then exit 1; fi
rm "$WORKSPACE"
mv "$scratch/real" "$WORKSPACE"
STAGING="$scratch/stage"
python3() { printf '%s\n' "$fixture"; }
fixture='{"status":"healthy","reason":"validated","revision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
detect_installation
test "$INSTALL_STATUS" = healthy
test "$INSTALLED_REVISION" = aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
fixture='{"status":"invalid","reason":"partial install","revision":null}'
detect_installation
test "$INSTALL_STATUS" = invalid
test -z "$INSTALLED_REVISION"
fixture='{"status":"absent","reason":"not installed","revision":null}'
detect_installation
test "$INSTALL_STATUS" = absent
fixture='{"status":"healthy","reason":"bad","revision":"bogus"}'
if (detect_installation) >/dev/null 2>&1; then exit 1; fi
fixture='{"status":"unknown","reason":"bad","revision":null}'
if (detect_installation) >/dev/null 2>&1; then exit 1; fi
python3() { return 1; }
if (detect_installation) >/dev/null 2>&1; then exit 1; fi
printf 'PASS: canonical paths, unsafe workspace refusal and classifier dispatch validation\n'
