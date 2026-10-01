#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
bash upgrade.sh --help >/dev/null
if bash upgrade.sh --bundle >/dev/null 2>&1; then exit 1; fi
if bash upgrade.sh --unknown >/dev/null 2>&1; then exit 1; fi
bash uninstall.sh --help >/dev/null
if bash uninstall.sh --unknown >/dev/null 2>&1; then exit 1; fi
printf 'PASS: LXC wrappers dispatch and reject invalid arguments\n'
