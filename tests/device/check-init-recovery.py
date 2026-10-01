#!/usr/bin/env python3
"""Reserved RP6 only: close Desktop, deny guest init execution, verify recovery.

Temporarily remove execute bits from the verified guest init inode, holding an
open descriptor for exact restoration in finally. No binary contents or native
configuration are changed. If the harness itself is killed, restore mode 0755
on the verified mapped-root-owned guest usr/lib/systemd/systemd before starting.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import stat
import subprocess
import time

UNIT = 'rocknix-desktop.service'
API = runpy.run_path(str(Path(__file__).with_name('check-component-recovery.py')))
active, output = API['active'], API['output']


def snapshot():
    base, _ = API['installed_paths']()
    paths = ['/run/0-runtime-dir/wayland-1', '/run/0-runtime-dir/pulse/native',
             '/dev/dri/renderD128', '/dev/video0']
    lib = base / 'host-tools/usr/lib/aarch64-linux-gnu'
    acl = output(str(lib / 'ld-linux-aarch64.so.1'), '--library-path', str(lib),
                 str(base / 'host-tools/usr/bin/getfacl'), '-p', '-n', *paths)
    env = dict(os.environ, SWAYSOCK='/run/0-runtime-dir/sway-ipc.0.sock')
    spaces = json.loads(subprocess.check_output(
        ['swaymsg', '-r', '-t', 'get_workspaces'], env=env, text=True))
    return {
        'acl': acl, 'identities': [(os.stat(p).st_dev, os.stat(p).st_ino) for p in paths],
        'sway': output('systemctl', 'show', 'sway.service', '-p', 'MainPID', '--value'),
        'profile': output('inputplumber', 'device', '0', 'profile', 'path'),
        'targets': output('inputplumber', 'device', '0', 'targets', 'list'),
        'keyboard': active('touchkeyboard.service'),
        'setting': output('/bin/bash', '-c', 'source /etc/profile; '
                          'get_setting rocknix.touchscreen-keyboard.enabled'),
        'workspace': [space['name'] for space in spaces if space['focused']],
        'accounts': [hashlib.sha256(Path(p).read_bytes()).hexdigest()
                     for p in ['/etc/passwd', '/etc/shadow', '/etc/group']],
    }


def main():
    assert os.getuid() == 0
    def interrupted(signum, frame):
        raise RuntimeError(f'Recovery probe interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGHUP, interrupted)
    assert active(UNIT) and active('sway.service')
    _, rootfs = API['installed_paths']()
    # Do not follow the guest's absolute /sbin/init symlink on the host.
    # This probe is specific to our verified Debian merged-/usr installation.
    target = rootfs / 'usr/lib/systemd/systemd'
    assert target.resolve() == target
    original = target.stat()
    assert stat.S_ISREG(original.st_mode) and original.st_uid == 200000
    assert original.st_mode & 0o111
    identity = (original.st_dev, original.st_ino, original.st_mode, original.st_uid)
    subprocess.run(['systemctl', 'stop', UNIT], check=True)
    assert active('essway.service') and not API['guest_processes']()
    before = snapshot()
    # Walk with no-follow directory descriptors, not a privileged open through
    # guest-controlled symlinks. The final fd remains valid through restoration.
    descriptor = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in target.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        child = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptor)
        os.close(descriptor)
        descriptor = child
        held = os.fstat(descriptor)
        assert (held.st_dev, held.st_ino, held.st_mode, held.st_uid) == identity
        os.fchmod(descriptor, stat.S_IMODE(original.st_mode) & ~0o111)
        started = time.monotonic()
        subprocess.run(['systemctl', 'start', UNIT], check=False, timeout=30)
        invocation = output('systemctl', 'show', UNIT, '-p', 'InvocationID', '--value')
        assert invocation
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if (not active(UNIT) and active('essway.service')
                    and not API['guest_processes']()
                    and not Path('/run/rocknix-desktop-session-state').exists()):
                break
            time.sleep(0.25)
        else:
            raise RuntimeError('Container-init failure did not restore Gaming')
        log = output('journalctl', '--no-pager', '_SYSTEMD_INVOCATION_ID=' + invocation)
        print(log[-12000:], flush=True)
        # Require actual LXC startup failure, not systemd's namespace setup
        # failure or an early host preflight refusal.
        assert 'container systemd startup failed' in log, log
        assert '/sbin/init' in log and 'Permission denied' in log, log
        assert snapshot() == before, 'Native state was not exactly restored'
        for name in ['rocknix-lxc', 'rocknix-network', 'rocknix-desktop',
                     'rocknix-desktop-input-state', 'rocknix-desktop-session-state']:
            assert not (Path('/run') / name).exists(), name
        assert not any('/run/rocknix-lxc' in line or '/run/rocknix-network' in line
                       for line in Path('/proc/self/mountinfo').read_text().splitlines())
        groups = [str(Path(parent) / name)
                  for parent, dirs, _ in os.walk('/sys/fs/cgroup')
                  for name in dirs if 'rocknix-lxc' in name]
        assert not groups, groups
        print(json.dumps({'init_exec_denied': True,
                          'recovered_seconds': round(time.monotonic() - started, 2),
                          'native_state_restored': True, 'runtime_cgroups_clean': True}),
              flush=True)
    finally:
        try:
            subprocess.run(['systemctl', 'stop', UNIT], check=True, timeout=55)
        finally:
            held = os.fstat(descriptor)
            if (held.st_dev, held.st_ino) == identity[:2]:
                os.fchmod(descriptor, stat.S_IMODE(original.st_mode))
            os.close(descriptor)
        current = target.stat()
        assert (current.st_dev, current.st_ino, current.st_mode, current.st_uid) == identity
    if subprocess.run(['systemctl', 'is-failed', '--quiet', UNIT]).returncode == 0:
        subprocess.run(['systemctl', 'reset-failed', UNIT], check=True)
    subprocess.run(['systemctl', 'start', UNIT], check=True)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        names = [name for _, name in API['guest_processes']()]
        if active(UNIT) and all(name in names for name in ['waybar', 'wvkbd-rocknix']):
            print('PASS: unchanged guest init; Desktop reopened', flush=True)
            return
        time.sleep(0.25)
    raise RuntimeError('Desktop did not reopen')


if __name__ == '__main__':
    main()
