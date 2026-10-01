#!/usr/bin/python3
"""Read-only usability checks, executed only inside mapped LXC maintenance."""
import grp
import os
from pathlib import Path
import pwd
import stat
import subprocess

PACKAGES = ('sudo', 'python3', 'python3-gi', 'gir1.2-gtk-3.0',
            'systemd', 'systemd-sysv', 'apt', 'dpkg', 'dbus', 'waybar', 'foot')


def check_mapping():
    if os.geteuid() != 0:
        raise RuntimeError('container-root check required')
    for name in ('uid_map', 'gid_map'):
        if Path('/proc/self', name).read_text().split() != ['0', '200000', '65536']:
            raise RuntimeError('refusing health check outside mapped Desktop LXC')


def check_user():
    user = pwd.getpwnam('rocknix')
    if (user.pw_uid, user.pw_gid, user.pw_dir) != (1000, 1000, '/home/rocknix'):
        raise RuntimeError('Desktop user identity/home does not match the supported layout')
    if grp.getgrgid(1000).gr_name != 'rocknix':
        raise RuntimeError('Desktop primary group is invalid')
    if 'rocknix' not in grp.getgrnam('sudo').gr_mem:
        raise RuntimeError('Desktop user lacks container sudo group membership')
    info = Path('/usr/bin/sudo').stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or not info.st_mode & stat.S_ISUID:
        raise RuntimeError('container sudo executable lacks root ownership/setuid')


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=20,
                            env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'})
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed: {result.stderr.strip()}')
    return result.stdout


def check_packages():
    for package in PACKAGES:
        if run('dpkg-query', '-W', '-f=${Status}', package).strip() != 'install ok installed':
            raise RuntimeError(f'Desktop prerequisite is incomplete: {package}')
    if run('dpkg', '--audit').strip():
        raise RuntimeError('container package database has unfinished transactions')
    run('apt-get', '--version')
    run('visudo', '-c')
    run('sudo', '-l', '-U', 'rocknix')


def main():
    check_mapping()
    check_user()
    check_packages()
    print('Container health passed: mapped identity, configured packages, APT and sudo.')


if __name__ == '__main__':
    main()
