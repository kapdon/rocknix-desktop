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
paths = list(Path('rootfs-overlay/usr/local/bin').iterdir())
paths.append(Path('tests/firefox-marionette.py'))
for path in paths:
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
test "$VERSION" = development
test "$ASSET" = rocknix-sway-rp6-arm64.tar.xz
grep -q 'dist/rocknix-sway-rp6-arm64.tar.xz' README.md
grep -q 'button: LeftStick' payload/input/desktop.yaml
grep -q 'bindsym XF86Tools' payload/bin/launch-sway-desktop
grep -q 'bindsym F13' payload/bin/launch-sway-desktop
grep -q 'systemctl stop essway.service' payload/bin/launch-sway-desktop
if grep -q 'systemctl stop sway.service' payload/bin/launch-sway-desktop; then
  printf 'FAIL: Sway compositor would be stopped\n' >&2; exit 1
fi
grep -q 'rocknix-keyboard-toggle' rootfs-overlay/etc/xdg/waybar/config.jsonc
grep -q 'kill -34' payload/bin/rocknix-keyboard-toggle
grep -q 'kill -34' rootfs-overlay/usr/local/bin/rocknix-keyboard-toggle
grep -q 'systemctl start --no-block "${unit}"' payload/bin/restore-emulationstation
if grep -q '^systemctl start sway.service$' payload/bin/restore-emulationstation; then
  printf 'FAIL: synchronous Sway recovery can deadlock in ExecStopPost\n' >&2; exit 1
fi
grep -q '^TimeoutStopSec=45$' payload/systemd/xfce-desktop.service
grep -q '^SuccessExitStatus=143$' payload/systemd/xfce-desktop.service
grep -q 'rm -f -- "${CONTROL_FIFO}"' payload/bin/launch-sway-desktop
grep -q '/usr/share/applications/firefox-esr.desktop' Dockerfile.rootfs
grep -q '/usr/share/applications/foot-server.desktop' Dockerfile.rootfs
grep -q '/usr/share/applications/footclient.desktop' Dockerfile.rootfs
grep -q 'execute=Return KP_Enter space' rootfs-overlay/etc/xdg/fuzzel/fuzzel.ini
grep -q '2fe08f3bd52c6e795df8353d29deb89596b5099d' Dockerfile.rootfs
grep -q 'i64 = 32' experiments/ffmpeg/build.sh
grep -q 'BindsTo=sway.service' payload/systemd/xfce-desktop.service
grep -q '^source /etc/profile$' payload/bin/preflight
grep -q 'TOUCHKEYBOARD_SETTING=$(get_setting' payload/bin/launch-sway-desktop
grep -q 'INPUT_STATE_PRESENT=1' payload/bin/restore-emulationstation
grep -q 'ROCKNIX_SWAY_RUNTIME=1' rootfs-overlay/etc/rocknix-xfce-release
grep -q -- '--iidfile' build-rootfs.sh
python3 -m json.tool rootfs-overlay/etc/xdg/waybar/config.jsonc >/dev/null
if rg -q '%-' rootfs-overlay/etc/xdg/waybar/config.jsonc; then
  printf 'FAIL: Waybar chrono format contains an unsupported modifier\n' >&2; exit 1
fi
if rg -q 'xfce4-session|xfwm4|xserver-xorg|[[:space:]]onboard[[:space:]\\]' Dockerfile.rootfs; then
  printf 'FAIL: retired XFCE/Xorg package remains in rootfs\n' >&2; exit 1
fi
printf 'PASS: syntax, checksum rejection, lifecycle, shell and release checks\n'
grep -q 'dev/install.sh' README.md
bash tests/persistence.sh
bash tests/upgrade.sh
bash tests/release-selection.sh
bash tests/installer-flow.sh
python3 tests/session-lifecycle.py
