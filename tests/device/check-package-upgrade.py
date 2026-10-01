#!/usr/bin/env python3
"""Exercise authenticated container-only APT upgrades with two disposable packages.

Installed separated LXC layout only. Uses the public test password and does not
claim physical controller testing or validate upgrades of production libraries.
"""
import hashlib
from pathlib import Path
import runpy

base = Path('/storage/rocknix-desktop')
host = base / 'managed/host'
runtime = runpy.run_path(str(host / 'bin/rocknix-lxc'))['Runtime'](
    host / 'host-tools', base / 'data/rootfs')
accounts = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
            for path in ['/etc/passwd', '/etc/shadow', '/etc/group']}

result = runtime.attach('/usr/sbin/runuser', '-u', 'rocknix', '--', '/usr/bin/python3', '-',
    timeout=360, input=r'''
import json, os, subprocess, tempfile
from pathlib import Path

assert os.getuid() == 1000
assert Path('/proc/self/uid_map').read_text().split() == ['0', '200000', '65536']
assert Path('/proc/self/gid_map').read_text().split() == ['0', '200000', '65536']
name = 'rocknix-lxc-upgrade-probe'
program = Path('/usr/bin') / name

def output(*command):
    return subprocess.check_output(command, text=True, timeout=30).strip()

def sudo(*command):
    subprocess.run(['sudo', '-S', '-k', '-p', '', *command], input='rocknix\n',
                   text=True, check=True, timeout=90)

def inventory():
    return output('dpkg-query', '-W', '-f=${Package} ${Version} ${db:Status-Status}\n')

before = inventory()
assert not any(line.split()[0] == name for line in before.splitlines())
assert not program.exists() and not program.is_symlink()
assert not output('dpkg', '--audit')
versions = []
with tempfile.TemporaryDirectory(prefix='rocknix-apt-upgrade-') as directory:
    work = Path(directory)
    packages = []
    for version in ('1.0', '2.0'):
        root = work / ('source-' + version)
        (root / 'DEBIAN').mkdir(parents=True)
        (root / 'usr/bin').mkdir(parents=True)
        (root / 'DEBIAN/control').write_text(
            f'Package: {name}\nVersion: {version}\nArchitecture: all\n'
            'Maintainer: ROCKNIX Desktop Test <rocknix-desktop@localhost>\n'
            'Description: Disposable container APT upgrade validation fixture\n')
        executable = root / 'usr/bin' / name
        executable.write_text(f'#!/bin/sh\nprintf "%s\\n" "{version}"\n')
        executable.chmod(0o755)
        package = work / (name + '_' + version + '_all.deb')
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(root),
                        str(package)], check=True, timeout=30)
        packages.append(package)
    attempted = False
    try:
        for version, package in zip(('1.0', '2.0'), packages):
            simulation = output('apt-get', '--simulate', '--no-remove',
                                'install', str(package))
            changes = [line.split()[1] for line in simulation.splitlines()
                       if line.startswith(('Inst ', 'Remv '))]
            assert changes == [name], simulation
            attempted = True
            sudo('apt-get', '-y', '--no-remove', 'install', str(package))
            assert output('dpkg-query', '-W', '-f=${Version}', name) == version
            assert output(str(program)) == version
            assert not output('dpkg', '--audit')
            versions.append(version)
    finally:
        if attempted and any(line.split()[0] == name for line in inventory().splitlines()):
            simulation = output('apt-get', '--simulate', '--no-auto-remove', 'purge', name)
            removals = [line.split()[1] for line in simulation.splitlines()
                        if line.startswith(('Remv ', 'Purg '))]
            assert removals == [name], simulation
            sudo('apt-get', '-y', '--no-auto-remove', 'purge', name)
assert not program.exists()
assert inventory() == before
assert not output('dpkg', '--audit')
print(json.dumps({'guest_uid': os.getuid(), 'authenticated_apt_versions': versions,
                  'package_inventory_restored': True, 'dpkg_audit_clean': True}), flush=True)
''')
print(result.stdout, result.stderr, flush=True)
assert result.returncode == 0
assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
           for path, digest in accounts.items())
print('PASS: native account databases unchanged', flush=True)
