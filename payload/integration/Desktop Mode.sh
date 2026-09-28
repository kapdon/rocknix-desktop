#!/bin/bash

source /etc/profile

BASE=/storage/.local/share/rocknix-xfce

pause_on_error() {
  printf '\n%s\n' "$*" >&2
  printf 'This window will close in 10 seconds.\n' >&2
  sleep 10
  exit 1
}

"${BASE}/bin/preflight" || pause_on_error "Desktop Mode is not ready."

if systemctl is-active --quiet xfce-desktop.service; then
  pause_on_error "Desktop Mode is already running."
fi

systemctl reset-failed xfce-desktop.service 2>/dev/null || true

if command -v set_kill >/dev/null 2>&1; then
  set_kill set "xfce4-session Xorg Xwayland"
fi

systemctl start --no-block xfce-desktop.service || pause_on_error "Could not start Desktop Mode."
