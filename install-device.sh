#!/bin/bash
set -Eeuo pipefail
SELF_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec python3 "$SELF_DIR/payload/bin/rocknix-lxc-install" --bundle "$SELF_DIR" "$@"
