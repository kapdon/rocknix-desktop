#!/usr/bin/python3
"""Run documented bootstrap and pinned-release selection through terminal fixtures."""
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import tarfile
import tempfile
import termios
import time

root = Path(__file__).resolve().parents[1]
bootstrap = 'curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash'
fixture_version = 'v1.2.3'
commands = {fixture_version: bootstrap + ' -s -- --release ' + fixture_version,
            'development': bootstrap}
readme = (root / 'README.md').read_text().splitlines()
assert bootstrap in readme, 'README bootstrap command changed'
installer = (root / 'install.sh').read_text()
guard = 'if [[ "${BASH_SOURCE[0]:-$0}" = "$0" ]]; then'
assert guard in installer, 'bash -c entry point must handle an unset BASH_SOURCE'
candidate, previous = '1' * 40, '2' * 40
asset = f'rocknix-desktop-rp6-arm64-{candidate}.tar.xz'


def terminal(command, environment, replies):
    master, slave = pty.openpty()
    attributes = termios.tcgetattr(slave)
    attributes[3] &= ~termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, attributes)
    def controlling_terminal():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    process = subprocess.Popen(['bash', '-o', 'pipefail', '-c', command], env=environment, stdin=slave,
                               stdout=slave, stderr=slave, preexec_fn=controlling_terminal)
    os.close(slave)
    output, consumed, cursor = '', 0, 0
    deadline = time.monotonic() + 15
    try:
        while True:
            if time.monotonic() > deadline:
                raise AssertionError(f'command timed out: {output}')
            if select.select([master], [], [], 0.1)[0]:
                try:
                    data = os.read(master, 65536)
                except OSError as error:
                    if error.errno == errno.EIO:
                        break
                    raise
                if not data:
                    break
                output += data.decode()
                while consumed < len(replies):
                    prompt, reply = replies[consumed]
                    position = output.find(prompt, cursor)
                    if position < 0:
                        break
                    os.write(master, b'\x04' if reply is None else (reply + '\n').encode())
                    cursor = position + len(prompt)
                    consumed += 1
            elif process.poll() is not None:
                break
        status = process.wait(timeout=2)
        assert consumed == len(replies), output
        return status, output
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)


def run(channel=fixture_version, answers=('y',), *, healthy=False, untested=False,
        flags='', bootstrap_failure=False, corrupt=False, bad_provenance=False):
    with tempfile.TemporaryDirectory(prefix='installer-command-') as directory:
        fixture = Path(directory)
        workspace = fixture / 'workspace'
        bundle = fixture / 'bundle'
        binary = fixture / 'bin'
        binary.mkdir()
        (bundle / 'payload/bin').mkdir(parents=True)
        (bundle / 'payload/systemd').mkdir()
        (bundle / 'rootfs/etc').mkdir(parents=True)
        (bundle / 'payload/systemd/rocknix-desktop.service').write_text('canonical service\n')
        (bundle / 'rootfs/etc/rocknix-desktop-release').write_text(
            'ROCKNIX_DESKTOP_RUNTIME=1\nROCKNIX_LXC_RUNTIME=1\n')
        (bundle / 'build-info').write_text(f'commit={previous if bad_provenance else candidate}\n')
        (bundle / 'payload/bin/rocknix-install-state').write_text(
            'import json, os\nprint(json.dumps({"status": os.environ["FIXTURE_STATUS"], '
            '"reason": "fixture classifier", "revision": os.environ["FIXTURE_REVISION"]}))\n')
        (bundle / 'payload/bin/rocknix-device-profile').write_text(
            'print(\'{"profile":"fixture-sm8550"}\')\n')
        for action, filename in [('Install', 'install-device.sh'), ('Update', 'upgrade.sh')]:
            (bundle / filename).write_text(
                '#!/bin/bash\nset -eu\n[ -r /dev/tty ]\n'
                + ('exec 8>"$FIXTURE/lock"\nflock -n 8\n' if action == 'Update' else '')
                + f'printf "{action} %s consent=%s\\n" "$*" '
                '"$ROCKNIX_UNTESTED_DEVICE_CONFIRMED" >>"$FIXTURE/actions"\n')
        with tarfile.open(fixture / asset, 'w:xz') as archive:
            for path in sorted(bundle.rglob('*')):
                archive.add(path, arcname=str(path.relative_to(bundle)), recursive=False)
        checksum = hashlib.sha256((fixture / asset).read_bytes()).hexdigest()
        (fixture / 'latest.json').write_text(json.dumps(
            {'commit': candidate, 'sha256': '0' * 64 if corrupt else checksum, 'asset': asset}))
        installed = workspace / 'managed/host/bin'
        if '--uninstall' in flags:
            installed.mkdir(parents=True)
            (installed / 'rocknix-lxc-uninstall').write_text(
                'import os,sys\nfrom pathlib import Path\n'
                'with (Path(os.environ["FIXTURE"])/"actions").open("a") as stream:\n'
                ' stream.write("Uninstall " + sys.argv[1] + "\\n")\n')
        mocks = '''
WORKSPACE="$FIXTURE/workspace"
check_device() {
  [ -r /dev/tty ] || fail 'controlling terminal is missing'
  EXPERIMENTAL_DEVICE=$FIXTURE_UNTESTED
  DEVICE_MODEL='Fixture SM8550 handheld'
  check_install_target
  printf 'terminal\\n' >>"$FIXTURE/checks"
}
check_power() { printf 'power\\n' >>"$FIXTURE/checks"; }
acquire_install_lock() { exec 9>"$FIXTURE/lock"; flock -n 9; }
validate_uninstall_helpers() { printf 'trusted-uninstall\\n' >>"$FIXTURE/checks"; }
'''
        (fixture / 'installer.sh').write_text(installer.replace(guard, mocks + '\n' + guard, 1))
        curl = binary / 'curl'
        curl.write_text('''#!/usr/bin/python3
import os, pathlib, sys
fixture = pathlib.Path(os.environ['FIXTURE'])
args = sys.argv[1:]
url = next(value for value in args if value.startswith('https://'))
with (fixture / 'downloads').open('a') as log:
    log.write(url + '\\n')
if 'raw.githubusercontent.com' in url:
    source = (fixture / 'installer.sh').read_bytes()
    if os.environ['FIXTURE_BOOTSTRAP_FAILURE'] == '1':
        sys.stdout.buffer.write(source[:source.index(b'detect_installation()')])
        sys.exit(22)
    sys.stdout.buffer.write(source)
else:
    target = pathlib.Path(args[args.index('-o') + 1])
    target.write_bytes((fixture / url.rsplit('/', 1)[-1]).read_bytes())
''')
        curl.chmod(0o755)
        environment = os.environ | {
            'PATH': f'{binary}:{os.environ["PATH"]}', 'FIXTURE': str(fixture),
            'FIXTURE_STATUS': 'healthy' if healthy else 'absent',
            'FIXTURE_REVISION': previous if healthy else '',
            'FIXTURE_UNTESTED': str(int(untested)),
            'FIXTURE_BOOTSTRAP_FAILURE': str(int(bootstrap_failure)),
        }
        if healthy:
            (workspace / 'data/home').mkdir(parents=True)
            (workspace / 'data/home/sentinel').write_text('preserved')
        assert workspace.exists() == (healthy or '--uninstall' in flags)
        prompts = []
        if untested and '--uninstall' not in flags:
            prompts.append('Proceed at your own risk? [y/N] ')
        if '--yes' not in flags and '--check' not in flags:
            prompts.append('Uninstall Desktop integration?' if '--uninstall' in flags else
                           f'{"Update" if healthy else "Install"} Desktop Mode?')
        replies = list(zip(prompts, answers))
        command = commands[channel]
        if flags:
            if channel == 'development':
                command += ' -s --'
            command += ' ' + flags
        status, output = terminal(command, environment, replies)
        actions = (fixture / 'actions').read_text() if (fixture / 'actions').exists() else ''
        downloads = (fixture / 'downloads').read_text().splitlines()
        checks = (fixture / 'checks').read_text().splitlines() if (fixture / 'checks').exists() else []
        if healthy:
            assert (workspace / 'data/home/sentinel').read_text() == 'preserved'
        return status, output, actions, downloads, checks, workspace.exists()


for channel in commands:
    for flags, answers, removed in (('--uninstall', ('y',), True),
                                   ('--uninstall', ('n',), False),
                                   ('--uninstall', (None,), False),
                                   ('--uninstall --check', (), False),
                                   ('--uninstall --yes', (), True)):
        status, output, actions, downloads, checks, _ = run(channel, answers, flags=flags, healthy=True)
        assert status == 0 and actions.startswith('Uninstall --check\n'), output
        assert ('Uninstall --yes\n' in actions) == removed
        assert len(downloads) == 1 and checks == ['terminal', 'trusted-uninstall']
    status, output, actions, downloads, checks, created = run(channel)
    assert status == 0 and actions == 'Install --replace consent=0\n', output
    assert created and checks == ['terminal', 'terminal', 'power', 'power', 'power']
    assert downloads[1:] == [f'https://github.com/kapdon/rocknix-desktop/releases/download/{channel}/latest.json',
                             f'https://github.com/kapdon/rocknix-desktop/releases/download/{channel}/{asset}']
    for answer in ('No', '', None):
        status, output, actions, _, _, _ = run(channel, (answer,))
        assert status == 0 and 'Cancelled.' in output and not actions, output
        status, output, actions, _, _, _ = run(channel, (answer,), healthy=True)
        assert status == 0 and 'Update Desktop Mode?' in output and 'Cancelled.' in output and not actions, output
    status, output, actions, _, _, _ = run(channel, healthy=True)
    assert status == 0 and actions.startswith('Update --bundle '), output
    assert f'--sha256 ' in actions and '--yes consent=0' in actions
    status, output, actions, _, _, created = run(channel, ('y', 'y'), untested=True)
    assert status == 0 and created and actions == 'Install --replace consent=1\n', output
    for flags, answer in [('', 'No'), ('', ''), ('', None), ('--yes', 'No'), ('--yes', ''), ('--yes', None)]:
        status, output, actions, downloads, checks, created = run(channel, (answer,), untested=True, flags=flags)
        assert status == 0 and 'Cancelled.' in output and not actions and not created, output
        assert len(downloads) == 1 and checks == ['terminal']
    status, output, actions, _, _, _ = run(channel, ('y',), untested=True, flags='--yes')
    assert status == 0 and actions == 'Install --replace consent=1\n', output
    status, output, actions, downloads, _, created = run(channel, ('y', ''), untested=True)
    assert status == 0 and created and len(downloads) == 3 and not actions and 'Cancelled.' in output, output
    for untested in (False, True):
        status, output, actions, downloads, checks, created = run(channel, (), untested=untested, flags='--check')
        assert status == 0 and 'Device checks passed. No changes made.' in output, output
        assert not actions and not created and len(downloads) == 1 and checks == ['terminal']
        assert 'Proceed at your own risk?' not in output
        assert ('Installation will require confirmation.' in output) == untested

source = subprocess.run(['bash', '-uc', 'source "$1"; test "$VERSION" = development',
                         '--', str(root / 'install.sh')], capture_output=True, text=True)
assert source.returncode == 0 and not source.stdout and not source.stderr, source
without_terminal = subprocess.run(['bash', '-c',
    'source "$1"; confirm_untested_device Fixture', '--', str(root / 'install.sh')],
    input='y\n', capture_output=True, text=True, start_new_session=True)
assert without_terminal.returncode != 0 and 'requires a terminal' in without_terminal.stderr
status, output, actions, downloads, checks, created = run(answers=(), bootstrap_failure=True)
assert status == 22 and not actions and not checks and not created and len(downloads) == 1, output
for option, error in [('corrupt', 'bundle checksum mismatch'), ('bad_provenance', 'bundle provenance mismatch')]:
    status, output, actions, _, checks, _ = run(answers=(), **{option: True})
    assert status != 0 and error in output and not actions and checks.count('power') == 2, output
print('PASS: documented bootstrap and pinned-release fixtures preserve terminal prompts, cancellation, device consent, checksum/provenance and bootstrap failure')
