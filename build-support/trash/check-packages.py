#!/usr/bin/env python3
"""Read candidate .deb metadata/payloads without installing or executing them."""
import argparse
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

VERSIONS = {'glib2.0': '2.84.4-3~deb13u5+rocknix1',
            'gvfs': '1.57.2-2+deb13u1+rocknix1'}
REQUIRED = {
    'libglib2.0-0t64': {'usr/lib/aarch64-linux-gnu/libgio-2.0.so.0.8400.4'},
    'libglib2.0-bin': {'usr/bin/gio'},
    'gvfs': {'usr/lib/aarch64-linux-gnu/gio/modules/libgvfsdbus.so'},
    'gvfs-daemons': {'usr/libexec/gvfsd', 'usr/libexec/gvfsd-trash',
                     'usr/libexec/gvfsd-metadata',
                     'usr/share/gvfs/mounts/trash.mount'},
    'gvfs-libs': set(),
    'gvfs-backends': {'usr/libexec/gvfsd-' + suffix for suffix in (
        'admin', 'afc', 'afp', 'afp-browse', 'archive', 'cdda', 'dav', 'dnssd',
        'ftp', 'google', 'gphoto2', 'http', 'mtp', 'network', 'nfs', 'onedrive',
        'recent', 'sftp', 'smb', 'smb-browse', 'wsdd')},
}


def source_name(package, field):
    # Debian may omit Source when the binary and source names are identical.
    return (field or package).split()[0]


def audit_payload(archive, required=()):
    paths = set()
    elves = 0
    for member in archive:
        path = PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError(f'unsafe package path: {member.name}')
        name = str(path)
        if name in paths:
            raise ValueError(f'duplicate package path: {name}')
        paths.add(name)
        if member.uid != 0 or member.gid != 0:
            raise ValueError(f'non-root package owner: {name}')
        if path.parts and path.parts[0] in ('opt', 'storage', 'home', 'root'):
            raise ValueError(f'unexpected private/project payload: {name}')
        if name.startswith(('etc/apt/', 'etc/ld.so.conf.d/')):
            raise ValueError(f'unexpected package/loader override: {name}')
        if name in required and not member.isfile():
            raise ValueError(f'required payload is not a regular file: {name}')
        if member.isfile():
            with archive.extractfile(member) as stream:
                header = stream.read(20)
            if name in required and not name.endswith('.mount') and not header.startswith(b'\x7fELF'):
                raise ValueError(f'required library/program is not ELF: {name}')
            if header.startswith(b'\x7fELF'):
                if len(header) < 20 or header[4:6] != b'\x02\x01' or \
                        int.from_bytes(header[18:20], 'little') != 183:
                    raise ValueError(f'non-AArch64 ELF: {name}')
                elves += 1
    return paths, elves


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    packages = {}
    for package in sorted(args.directory.glob('*.deb')):
        def field(name):
            return subprocess.check_output(['dpkg-deb', '-f', str(package), name],
                                           text=True).strip()
        name, version, arch = field('Package'), field('Version'), field('Architecture')
        source = source_name(name, field('Source'))
        if source not in VERSIONS or version != VERSIONS[source]:
            raise ValueError(f'unexpected package provenance: {package}')
        if arch not in ('arm64', 'all') or name in packages:
            raise ValueError(f'wrong architecture or duplicate package: {package}')
        process = subprocess.Popen(['dpkg-deb', '--fsys-tarfile', str(package)],
                                   stdout=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
                paths, elves = audit_payload(archive, REQUIRED.get(name, set()))
            # Drain tar padding before waiting for the producer.
            process.stdout.read()
            if process.wait() != 0:
                raise ValueError(f'cannot read payload: {package}')
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.kill()
            process.wait()
        if arch == 'all' and elves:
            raise ValueError(f'architecture-independent package contains ELF: {package}')
        missing = REQUIRED.get(name, set()) - paths
        if missing:
            raise ValueError(f'{name} missing required features: {sorted(missing)}')
        packages[name] = version
        print(f'PASS {name} {version} {arch}: {elves} AArch64 ELF files')
    if REQUIRED.keys() - packages.keys():
        raise ValueError(f'missing packages: {sorted(REQUIRED.keys() - packages.keys())}')
    print('PASS: candidate package identities, paths, ELF architecture and required GVfs backends')


if __name__ == '__main__':
    main()
