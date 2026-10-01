#!/usr/bin/env python3
"""RP6: interrupt dpkg while configuring one disposable, dependency-free package.

Exercises authenticated guest administration, not the Desktop bundle updater.
Does not interrupt real application packages or simulate power loss.
"""
import hashlib
from pathlib import Path
import runpy

base = Path('/storage/rocknix-desktop')
host = base / 'managed/host'
runtime = runpy.run_path(str(host / 'bin/rocknix-lxc'))['Runtime'](
    host / 'host-tools', base / 'data/rootfs')
accounts = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
            for p in ('/etc/passwd', '/etc/shadow', '/etc/group')}
result = runtime.attach('/usr/sbin/runuser', '-u', 'rocknix', '--',
    '/usr/bin/python3', '-', timeout=240, input=r'''
import json, os, subprocess, tempfile
from pathlib import Path

assert os.getuid() == 1000
assert Path('/proc/self/uid_map').read_text().split() == ['0', '200000', '65536']
name = 'rocknix-lxc-interruption-probe'
state = Path('/var/lib') / name
def output(*args):
    return subprocess.check_output(args, text=True, timeout=30).strip()
def sudo(*args, check=True):
    return subprocess.run(['sudo', '-S', '-k', '-p', '', *args],
        input='rocknix\n', text=True, capture_output=True, check=check, timeout=90)
def inventory():
    return output('dpkg-query', '-W', '-f=${Package} ${Version} ${db:Status-Status}\n')
before = inventory()
automatic = output('apt-mark', 'showauto')
assert not any(line.split()[0] == name for line in before.splitlines())
assert not state.exists() and not state.is_symlink()
assert not sudo('dpkg', '--audit').stdout.strip()
with tempfile.TemporaryDirectory(prefix='rocknix-package-interruption-') as temp:
    work = Path(temp)
    control = work / 'source/DEBIAN'
    control.mkdir(parents=True)
    (control/'control').write_text(f'Package: {name}\nVersion: 1.0\nArchitecture: all\n'
        'Maintainer: ROCKNIX Desktop Test <rocknix-desktop@localhost>\n'
        'Description: Disposable interrupted configuration probe\n')
    # The parent is dpkg, not the host updater or any user application. A marker
    # permits the next normal configure attempt to complete without another kill.
    (control/'postinst').write_text('#!/bin/sh\nset -eu\n'
        f'if [ "$1" = configure ] && [ ! -e {state} ]; then\n'
        f'  mkdir {state}\n  kill -KILL "$PPID"\nfi\n')
    (control/'postrm').write_text('#!/bin/sh\nset -eu\n'
        f'if [ "$1" = purge ] && [ -d {state} ]; then rmdir {state}; fi\n')
    for script in ('postinst', 'postrm'): (control/script).chmod(0o755)
    package = work / (name + '.deb')
    subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(control.parent),
                    str(package)], check=True, timeout=30)
    plan = output('apt-get', '--simulate', '--no-remove', 'install', str(package))
    assert [line.split()[1] for line in plan.splitlines()
            if line.startswith(('Inst ', 'Remv '))] == [name], plan
    try:
        interrupted = sudo('apt-get', '-y', '--no-remove', 'install', str(package), check=False)
        assert interrupted.returncode != 0, 'dpkg was not interrupted'
        status = output('dpkg-query', '-W', '-f=${db:Status-Status}', name)
        assert status == 'half-configured', status
        assert name in sudo('dpkg', '--audit').stdout
        sudo('dpkg', '--configure', name)
        assert output('dpkg-query', '-W', '-f=${db:Status-Status}', name) == 'installed'
        assert not sudo('dpkg', '--audit').stdout.strip()
    finally:
        if any(line.split()[0] == name for line in inventory().splitlines()):
            sudo('dpkg', '--purge', name)
assert inventory() == before
assert output('apt-mark', 'showauto') == automatic
assert not state.exists()
assert not sudo('dpkg', '--audit').stdout.strip()
print(json.dumps({'interrupted_state': status, 'targeted_configure_recovered': True,
    'package_inventory_restored': True, 'automatic_marks_restored': True,
    'dpkg_audit_clean': True}))
''')
print(result.stdout, result.stderr, flush=True)
assert result.returncode == 0
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest
           for p, digest in accounts.items())
print('PASS: native account databases unchanged')
