#!/bin/bash
# Remove LXC integration while retaining persistent Desktop data.
set -Eeuo pipefail
self_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
for helper in "$self_dir/bin/rocknix-lxc-uninstall" "$self_dir/payload/bin/rocknix-lxc-uninstall"; do
  if [ -f "$helper" ]; then exec python3 "$helper" "$@"; fi
done
printf 'Missing LXC uninstaller; no files were changed.\n' >&2
exit 1
