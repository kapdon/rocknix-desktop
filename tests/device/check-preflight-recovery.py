#!/usr/bin/env python3
"""Installed RP6 early startup refusal using an exclusive temporary update guard.

Closes Desktop apps; never replaces an existing update guard. Removes only its
own marker in finally. Run on a reserved test device, outside a real update.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import time
import uuid

API = runpy.run_path(str(Path(__file__).with_name('check-component-recovery.py')))
BASE, _ = API['installed_paths']()
UPDATER = runpy.run_path(str(BASE / 'bin/rocknix-lxc-upgrade'))
UPDATER['configure_layout']()
GUARD = UPDATER['configure_layout'].__globals__['GUARD']
assert not GUARD.exists() and not GUARD.is_symlink()


def output(*command):
    return subprocess.check_output(command, text=True).strip()


def active(unit):
    return subprocess.run(['systemctl', 'is-active', '--quiet', unit]).returncode == 0


def snapshot():
    lib = BASE / 'host-tools/usr/lib/aarch64-linux-gnu'
    acl = subprocess.check_output([str(lib / 'ld-linux-aarch64.so.1'),
        '--library-path', str(lib), str(BASE / 'host-tools/usr/bin/getfacl'), '-p', '-n',
        '/run/0-runtime-dir/wayland-1', '/run/0-runtime-dir/pulse/native',
        '/dev/dri/renderD128', '/dev/video0'], text=True)
    env = dict(os.environ, SWAYSOCK='/run/0-runtime-dir/sway-ipc.0.sock')
    spaces = json.loads(subprocess.check_output(['swaymsg', '-r', '-t', 'get_workspaces'],
                                                text=True, env=env))
    return {'acl': acl, 'sway_pid': output('systemctl', 'show', 'sway.service',
                '-p', 'MainPID', '--value'),
            'profile': output('inputplumber', 'device', '0', 'profile', 'path'),
            'targets': output('inputplumber', 'device', '0', 'targets', 'list'),
            'keyboard_active': active('touchkeyboard.service'),
            'keyboard_setting': output('/bin/bash', '-c', 'source /etc/profile; '
                                       'get_setting rocknix.touchscreen-keyboard.enabled'),
            'workspace': [space['name'] for space in spaces if space['focused']],
            'native_accounts': [hashlib.sha256(Path(path).read_bytes()).hexdigest()
                                for path in ['/etc/passwd', '/etc/shadow', '/etc/group']]}


subprocess.run(['systemctl', 'stop', 'rocknix-desktop.service'], check=True)
assert active('essway.service') and active('sway.service')
before = snapshot()
marker = 'LXC preflight test ' + uuid.uuid4().hex + '\n'
with GUARD.open('x') as stream:
    stream.write(marker)
try:
    started = time.monotonic()
    result = subprocess.run(['systemctl', 'start', 'rocknix-desktop.service'],
                            text=True, capture_output=True, timeout=30)
    assert result.returncode != 0, 'Preflight unexpectedly accepted the guard'
    assert active('essway.service') and active('sway.service')
    assert not active('rocknix-desktop.service')
    assert snapshot() == before, 'Native Gaming state changed after early refusal'
    for name in ['rocknix-lxc', 'rocknix-network', 'rocknix-desktop',
                 'rocknix-desktop-input-state', 'rocknix-desktop-session-state']:
        assert not (Path('/run') / name).exists(), name
    invocation = output('systemctl', 'show', 'rocknix-desktop.service',
                        '-p', 'InvocationID', '--value')
    assert invocation
    log = output('journalctl', '--no-pager', '_SYSTEMD_INVOCATION_ID=' + invocation)
    assert 'upgrade in progress or recovery required' in log, log
    print(json.dumps({'early_start_refused': True, 'reason': 'upgrade guard',
        'seconds': round(time.monotonic() - started, 2),
        'native_accounts_permissions_input_workspace_unchanged': True,
        'no_desktop_runtime_left': True}), flush=True)
finally:
    assert not GUARD.is_symlink() and GUARD.read_text() == marker
    GUARD.unlink()
subprocess.run(['systemctl', 'reset-failed', 'rocknix-desktop.service'], check=True)
subprocess.run(['systemctl', 'start', 'rocknix-desktop.service'], check=True)
deadline = time.monotonic() + 40
while time.monotonic() < deadline:
    names = []
    for process in Path('/proc').iterdir():
        if process.name.isdecimal():
            try:
                if (process / 'status').read_text().split('Uid:\t', 1)[1].split()[0] == '201000':
                    names.append((process / 'comm').read_text().strip())
            except (FileNotFoundError, ProcessLookupError):
                pass
    if active('rocknix-desktop.service') and 'waybar' in names and 'wvkbd-rocknix' in names:
        print('PASS: guard removed; mapped-user Desktop restarted', flush=True)
        break
    time.sleep(.25)
else:
    raise RuntimeError('Desktop did not become ready')
