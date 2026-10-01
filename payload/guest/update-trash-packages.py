#!/usr/bin/python3
"""Receive package artifacts only inside mapped maintenance LXC."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile


def unpack(archive, destination):
    with tarfile.open(archive, 'r:') as source:
        members = source.getmembers()
        names = [m.name for m in members]
        if len(set(names)) != len(names) or sum(m.size for m in members) > 256 * 1024**2:
            raise RuntimeError('duplicate or oversized package payload')
        if not {'check-packages.py', 'install-image.py'} <= set(names):
            raise RuntimeError('package tools missing')
        for member in members:
            if (not member.isfile() or Path(member.name).name != member.name or
                    member.name.startswith('.') or
                    not (member.name in ('check-packages.py', 'install-image.py') or
                         member.name.endswith(('.deb', '.dsc', '.tar.xz', '.tar.gz', '.changes', '.buildinfo')))):
                raise RuntimeError('unexpected package payload member')
        for member in members:
            with source.extractfile(member) as incoming, (destination / member.name).open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)


def main():
    if os.geteuid() != 0 or any(Path('/proc/self/' + name).read_text().split() !=
                              ['0', '200000', '65536'] for name in ('uid_map', 'gid_map')):
        raise RuntimeError('refusing package update outside mapped container root')
    if subprocess.run(['systemctl', 'is-active', '--quiet', 'rocknix-desktop-session.service']).returncode == 0:
        raise RuntimeError('stop the Desktop session before package maintenance')
    if '/home/rocknix' in {line.split()[4] for line in Path('/proc/self/mountinfo').read_text().splitlines()}:
        raise RuntimeError('personal home must not be mounted during maintenance')
    # /proc/net follows the new network namespace; an inherited sysfs need not.
    interfaces = {line.split(':')[0].strip() for line in Path('/proc/net/dev').read_text().splitlines()[2:]}
    if interfaces != {'lo'}:
        raise RuntimeError('package maintenance requires a private offline network namespace')
    with tempfile.TemporaryDirectory(prefix='rocknix-package-update-') as temporary:
        directory = Path(temporary)
        unpack(Path(sys.argv[1]), directory)
        subprocess.run(['python3', str(directory / 'check-packages.py'), str(directory)], check=True)
        subprocess.run(['python3', str(directory / 'install-image.py'), str(directory), '--retained'], check=True)
        target = Path('/usr/local/share/rocknix-desktop/trash-source')
        if target.is_symlink():
            raise RuntimeError('source destination is a symlink')
        target.mkdir(parents=True, exist_ok=True)
        for path in directory.iterdir():
            if path.name.endswith(('.dsc', '.tar.xz', '.tar.gz', '.changes', '.buildinfo')):
                destination = target / path.name
                if destination.is_symlink():
                    raise RuntimeError('source artifact destination is a symlink')
                shutil.copyfile(path, destination)
    print('Package maintenance complete; personal home was not mounted.')


if __name__ == '__main__':
    main()
