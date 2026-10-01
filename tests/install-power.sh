#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source ./install.sh
power_test=$(mktemp -d)
trap 'rm -rf -- "$power_test"' EXIT
printf 'Battery\n' >"$power_test/type"
for capacity in 10 50 100; do
  printf '%s\n' "$capacity" >"$power_test/capacity"
  check_power "$power_test"
done
printf 'Charging\n' >"$power_test/status"
for capacity in 0 9 101 -1 unknown '' 5.0 999999999999; do
  printf '%s\n' "$capacity" >"$power_test/capacity"
  if (check_power "$power_test") >/dev/null 2>&1; then
    printf 'FAIL: accepted battery %s\n' "$capacity"; exit 1
  fi
done
rm "$power_test/capacity"
if (check_power "$power_test") >/dev/null 2>&1; then exit 1; fi
printf 'PASS: public installer battery gate rejects low, missing and invalid telemetry\n'
