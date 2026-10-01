#!/usr/bin/env python3
"""RP6 session-destructive check; closes apps, leaves Gaming on failure.

Run on a reserved RP6 as host root. Component tests kill only the selected
mapped-user process, mapped guest init, or identity-verified Desktop supervisor.
The startup test writes a temporary guest-only override.
ACL verification uses independent host tools, never guest code. If startup
testing fails before cleanup, stop Desktop and run remove-startup-override.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


OVERRIDE = '/etc/systemd/system/rocknix-desktop-session.service.d/99-lxc-recovery-test.conf'
MARKER = '/var/tmp/rocknix-lxc-startup-failure-test'
CONTENTS = ('[Service]\nExecStart=\n'
            'ExecStart=/bin/sh -c "echo injected-startup-failure > '
            + MARKER + '; sleep 3; exit 73"\n')


def override_script(remove=False):
    return f'''from pathlib import Path
import os
assert os.getuid() == 0
assert Path('/proc/self/uid_map').read_text().split() == ['0', '200000', '65536']
path = Path({OVERRIDE!r})
marker = Path({MARKER!r})
if {remove!r}:
    assert not path.is_symlink() and path.read_text() == {CONTENTS!r}
    path.unlink()
    if marker.exists():
        assert not marker.is_symlink() and marker.read_text() == 'injected-startup-failure\\n'
        marker.unlink()
        print('PASS: installed session executed the injected failure', flush=True)
    else:
        raise RuntimeError('Injected startup command was not reached')
else:
    assert not marker.exists() and not marker.is_symlink()
    path.parent.mkdir(exist_ok=True)
    with path.open('x') as stream:
        stream.write({CONTENTS!r})
'''


def installed_paths():
    import runpy
    project = Path('/storage/rocknix-desktop')
    base = project / 'managed/host'
    updater = runpy.run_path(str(base / 'bin/rocknix-lxc-upgrade'))
    updater['configure_layout']()
    values = updater['configure_layout'].__globals__
    return values['BASE'], values['ROOTFS']


def runtime(state='/run/rocknix-lxc'):
    import runpy
    base, rootfs = installed_paths()
    api = runpy.run_path(str(base / 'bin/rocknix-lxc'))
    return api['Runtime'](base / 'host-tools', rootfs, Path(state))


def remove_override():
    instance = runtime('/run/rocknix-lxc-failure-cleanup')
    try:
        instance.start()
        result = instance.attach('/usr/bin/python3', '-', input=override_script(True))
        print(result.stdout, result.stderr, flush=True)
        assert result.returncode == 0
    finally:
        instance.close()


def output(*command):
    return subprocess.check_output(command, text=True).strip()


def active(unit):
    return subprocess.run(['systemctl', 'is-active', '--quiet', unit]).returncode == 0


def guest_processes():
    result = []
    for process in Path('/proc').iterdir():
        if not process.name.isdecimal():
            continue
        try:
            uid = int(next(line for line in (process / 'status').read_text().splitlines()
                           if line.startswith('Uid:')).split()[1])
            if 200000 <= uid < 265536:
                result.append((int(process.name), (process / 'comm').read_text().strip()))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component', choices=['waybar', 'wvkbd-rocknix', 'startup', 'stop',
                                             'supervisor', 'guest-init',
                                             'remove-startup-override'])
    args = parser.parse_args()
    assert os.getuid() == 0
    if args.component == 'remove-startup-override':
        remove_override()
        return
    assert active('rocknix-desktop.service') and active('sway.service')
    keyboard_setting_before = output('/bin/bash', '-c', 'source /etc/profile; '
                                     'get_setting rocknix.touchscreen-keyboard.enabled')
    if args.component not in ('startup', 'stop'):
        if args.component == 'supervisor':
            record = json.loads(Path('/run/rocknix-lxc/resources.json').read_text())
            target = int(record['owner'])
            import runpy
            base = installed_paths()[0]
            api = runpy.run_path(str(base / 'bin/rocknix-lxc'))
            assert api['process_identity'](target) == record['identity']
            command = Path(f'/proc/{target}/cmdline').read_bytes().split(b'\0')
            assert str(base / 'bin/rocknix-lxc').encode() in command, command
            targets = [target]
        elif args.component == 'guest-init':
            targets = []
            for pid, name in guest_processes():
                if name != 'systemd':
                    continue
                status = dict(line.split(':', 1) for line in
                              Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)
                if status['NSpid'].split()[-1] == '1' and status['Uid'].split()[0] == '200000':
                    targets.append(pid)
        else:
            targets = [pid for pid, name in guest_processes() if name == args.component]
        assert len(targets) == 1, targets
        target = targets[0]
        assert 'rocknix-desktop.service' in Path(f'/proc/{target}/cgroup').read_text()
    grants = json.loads(Path('/run/rocknix-lxc/desktop-access/grants.json').read_text())
    input_state = Path('/run/rocknix-desktop-input-state').read_text()
    session_state = dict(line.split('=', 1) for line in
                         Path('/run/rocknix-desktop-session-state').read_text().splitlines())
    keyboard_mask = Path('/run/systemd/system/touchkeyboard.service')
    if session_state.get('touchkeyboard_mask_owned') == '1':
        assert keyboard_mask.is_symlink() and keyboard_mask.readlink() == Path('/dev/null')
    sway = output('systemctl', 'show', 'sway.service', '-p', 'MainPID', '--value')
    if args.component == 'startup':
        result = runtime().attach('/usr/bin/python3', '-', input=override_script())
        assert result.returncode == 0, result.stderr
        subprocess.run(['systemctl', 'stop', 'rocknix-desktop.service'], check=True)
        started = time.monotonic()
        subprocess.run(['systemctl', 'start', 'rocknix-desktop.service'], check=True)
        # Do not mistake the previous Gaming session for recovery. The injected
        # guest command stays alive for three seconds so this journal is visible.
        deadline = time.monotonic() + 30
        while not Path('/run/rocknix-lxc/desktop-access/grants.json').exists():
            if time.monotonic() > deadline:
                raise RuntimeError('Installed startup never reached the access grant')
            time.sleep(0.05)
    elif args.component == 'stop':
        started = time.monotonic()
        subprocess.run(['systemctl', 'stop', 'rocknix-desktop.service'], check=True)
    else:
        started = time.monotonic()
        descriptor = os.pidfd_open(target)
        try:
            # Pin the process before signaling; never signal a recycled PID.
            assert 'rocknix-desktop.service' in Path(f'/proc/{target}/cgroup').read_text()
            if args.component == 'supervisor':
                assert api['process_identity'](target) == record['identity']
            signal.pidfd_send_signal(descriptor, signal.SIGKILL)
        finally:
            os.close(descriptor)
    while time.monotonic() - started < 50:
        if (active('essway.service') and not active('rocknix-desktop.service')
                and not guest_processes()
                and not Path('/run/rocknix-desktop-session-state').exists()):
            break
        time.sleep(0.25)
    else:
        raise RuntimeError('Gaming restoration did not finish within 50 seconds')
    elapsed = round(time.monotonic() - started, 2)
    if args.component == 'stop':
        assert output('systemctl', 'show', 'rocknix-desktop.service',
                      '-p', 'ActiveState', '--value') == 'inactive'
        assert output('systemctl', 'show', 'rocknix-desktop.service',
                      '-p', 'Result', '--value') == 'success'
    assert active('sway.service')
    assert output('systemctl', 'show', 'sway.service', '-p', 'MainPID', '--value') == sway
    tools = installed_paths()[0] / 'host-tools'
    lib = tools / 'usr/lib/aarch64-linux-gnu'
    for grant in grants:
        stat = os.stat(grant['path'])
        assert [stat.st_dev, stat.st_ino] == grant['identity'], grant['path']
        acl = subprocess.check_output([str(lib / 'ld-linux-aarch64.so.1'),
            '--library-path', str(lib), str(tools / 'usr/bin/getfacl'),
            '-p', '-n', grant['path']], text=True)
        assert acl == grant['acl'], (grant['path'], acl, grant['acl'])
    for path in ['/run/rocknix-lxc', '/run/rocknix-network', '/run/rocknix-audio', '/run/rocknix-desktop',
                 '/run/rocknix-desktop-input-state', '/run/rocknix-desktop-session-state']:
        assert not Path(path).exists(), path
    assert not any('/run/rocknix-lxc' in line or '/run/rocknix-network' in line or '/run/rocknix-audio' in line
                   for line in Path('/proc/self/mountinfo').read_text().splitlines())
    expected_profile = next(line.split('=', 1)[1] for line in input_state.splitlines()
                            if line.startswith('profile='))
    actual_profile = output('inputplumber', 'device', '0', 'profile', 'path')
    assert actual_profile == f"Current profile path: '{expected_profile}'", actual_profile
    targets_text = output('inputplumber', 'device', '0', 'targets', 'list')
    actual_targets = [line.split('│')[1].strip() for line in targets_text.splitlines()
                      if line.count('│') == 3 and line.split('│')[1].strip() != 'Id']
    expected_targets = [line[7:] for line in input_state.splitlines()
                        if line.startswith('target=')]
    assert sorted(actual_targets) == sorted(expected_targets), targets_text
    assert active('touchkeyboard.service') == (session_state['touchkeyboard_active'] == '1')
    if session_state.get('touchkeyboard_mask_owned') == '1':
        assert not os.path.lexists(keyboard_mask), 'Owned native keyboard mask leaked'
    setting = output('/bin/bash', '-c', 'source /etc/profile; '
                     'get_setting rocknix.touchscreen-keyboard.enabled')
    assert setting == keyboard_setting_before, setting
    sway_environment = dict(os.environ, SWAYSOCK='/run/0-runtime-dir/sway-ipc.0.sock')
    workspaces = json.loads(subprocess.check_output(
        ['swaymsg', '-r', '-t', 'get_workspaces'], env=sway_environment, text=True))
    assert [item['name'] for item in workspaces if item['focused']] == [session_state['workspace']]
    remaining_groups = [str(Path(parent) / name)
                        for parent, directories, _ in os.walk('/sys/fs/cgroup')
                        for name in directories if 'rocknix-lxc' in name]
    assert not remaining_groups, remaining_groups
    print(json.dumps({'component': args.component, 'recovered_seconds': elapsed,
        'exact_endpoint_acls_restored': len(grants), 'mapped_processes_remaining': [],
        'runtime_and_host_mounts_clean': True, 'original_profile': expected_profile,
        'targets_restored': actual_targets,
        'native_keyboard_restored': True, 'sway_pid_unchanged': sway,
        'keyboard_setting_restored': setting, 'workspace_restored': session_state['workspace'],
        'lxc_cgroups_removed': True}), flush=True)
    if args.component == 'startup':
        # A subprocess keeps the maintenance runtime's private mount namespace
        # out of the host-side verification/restart process.
        subprocess.run([sys.executable, __file__, 'remove-startup-override'], check=True)
    if subprocess.run(['systemctl', 'is-failed', '--quiet',
                       'rocknix-desktop.service']).returncode == 0:
        subprocess.run(['systemctl', 'reset-failed', 'rocknix-desktop.service'], check=True)
    subprocess.run(['systemctl', 'start', 'rocknix-desktop.service'], check=True)
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        names = [name for _, name in guest_processes()]
        if active('rocknix-desktop.service') and all(name in names for name in
                                                ['waybar', 'wvkbd-rocknix']):
            print('PASS: Desktop reopened with mapped-user panel and keyboard', flush=True)
            return
        time.sleep(0.25)
    raise RuntimeError('Desktop did not reopen')


if __name__ == '__main__':
    main()
