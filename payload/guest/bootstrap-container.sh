#!/bin/bash
# Sent to /bin/bash by lxc-attach inside the mapped, retained LXC rootfs.
set -Eeuo pipefail
prepare_packages() {
  local mode=${1:---retained} package status
  local -a prerequisites=(sudo python3 python3-gi gir1.2-gtk-3.0 systemd systemd-sysv)
  case "${mode}" in
    --retained)
      # Existing LXC images already contain these. Never let an unrelated
      # pending package be configured by an implicit bootstrap APT transaction.
      for package in "${prerequisites[@]}"; do
        status=$(dpkg-query -W '-f=${Status}' "${package}") || status=missing
        if [ "${status}" != 'install ok installed' ]; then
          printf 'Desktop prerequisite %s is not installed/configured; repair it with guest sudo/APT before retrying.\n' "${package}" >&2
          return 1
        fi
      done
      ;;
    *) echo 'Unknown bootstrap mode' >&2; return 1 ;;
  esac
}
[ "$#" -le 1 ] || { echo 'Unexpected bootstrap arguments' >&2; exit 1; }
[ "$(id -u)" = 0 ] || { echo 'Container root required' >&2; exit 1; }
for mapping in /proc/self/uid_map /proc/self/gid_map; do
  awk 'NR == 1 && NF == 3 && $1 == 0 && $2 == 200000 && $3 == 65536 {ok=1; next}
       {ok=0; exit} END {exit !ok}' "$mapping" || {
    echo 'Refusing bootstrap outside the mapped Desktop container' >&2; exit 1;
  }
done
! systemctl is-active --quiet rocknix-desktop-session.service || {
  echo 'Stop the Desktop user session before maintenance' >&2; exit 1;
}
if getent passwd rocknix >/dev/null; then
  [ "$(id -u rocknix)" = 1000 ] && [ "$(id -g rocknix)" = 1000 ] || {
    echo 'Existing rocknix identity conflicts with the desktop mapping' >&2; exit 1;
  }
else
  ! getent passwd 1000 >/dev/null || { echo 'UID 1000 already allocated' >&2; exit 1; }
fi
if getent group 1000 >/dev/null; then
  [ "$(getent group 1000 | cut -d: -f1)" = rocknix ] || {
    echo 'GID 1000 already allocated' >&2; exit 1;
  }
fi
if getent group rocknix >/dev/null; then
  [ "$(getent group rocknix | cut -d: -f3)" = 1000 ] || {
    echo 'Existing rocknix group conflicts with the desktop mapping' >&2; exit 1;
  }
fi
export DEBIAN_FRONTEND=noninteractive
prepare_packages "${1:---retained}"
if ! getent group rocknix >/dev/null; then groupadd --gid 1000 rocknix; fi
if ! getent passwd rocknix >/dev/null; then
  useradd --create-home --uid 1000 --gid 1000 --shell /bin/bash --groups sudo rocknix
else
  usermod --append --groups sudo rocknix
fi
# Existing passwords are preserved. Integration updates initialize unconfigured
# accounts to the documented default; sudo still authenticates normally.
passwd --lock root
if [ -f /usr/sbin/policy-rc.d ] && [ "$(cat /usr/sbin/policy-rc.d)" = '#!/bin/sh
# Debian packages must never start services in the ROCKNIX application runtime.
exit 101' ]; then
  rm /usr/sbin/policy-rc.d
fi
systemctl set-default multi-user.target
systemctl mask getty.target console-getty.service NetworkManager.service \
  NetworkManager-wait-online.service systemd-networkd.service \
  systemd-networkd.socket systemd-networkd-wait-online.service \
  sys-kernel-config.mount sys-kernel-debug.mount systemd-firstboot.service
printf 'Container prerequisites ready; apply Desktop integration before activation.\n'
