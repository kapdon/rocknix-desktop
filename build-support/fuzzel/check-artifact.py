#!/usr/bin/env python3
"""Fail the build if the launcher artifact loses its private ARM64 library."""
from pathlib import Path
import subprocess
import sys


def check(root):
    root = Path(root).resolve()
    binary = root / 'bin/fuzzel'
    library = root / 'lib/libpixman-1.so.0'
    for path in (binary, library):
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise ValueError(f'artifact dependency escapes private directory: {path}')
        header = resolved.read_bytes()[:20]
        if (header[:6] != b'\x7fELF\x02\x01' or
                int.from_bytes(header[18:20], 'little') != 183):
            raise ValueError(f'not little-endian ARM64 ELF: {path}')
    if not binary.stat().st_mode & 0o111:
        raise ValueError('launcher is not executable')
    dynamic = subprocess.check_output(['readelf', '-d', str(binary)], text=True)
    paths = [line for line in dynamic.splitlines()
             if '(RUNPATH)' in line or '(RPATH)' in line]
    if len(paths) != 1 or paths[0].split('[', 1)[-1].split(']', 1)[0] != '/opt/rocknix-fuzzel/lib':
        raise ValueError('launcher must resolve its private library without global environment changes')
    if '(NEEDED)' not in dynamic or '[libpixman-1.so.0]' not in dynamic:
        raise ValueError('launcher does not declare the expected Pixman dependency')
    for name in ('fuzzel.tar.gz', 'pixman.tar.gz', 'protocols.tar.xz',
                 'check-input.py', 'pointer-enter.patch', 'aarch64.ini', 'build.Dockerfile', 'check-artifact.py', 'pixman-COPYING'):
        if not (root / 'share/source' / name).is_file():
            raise ValueError(f'missing build provenance: {name}')
    if not (root / 'share/doc/fuzzel/LICENSE').is_file():
        raise ValueError('missing upstream launcher license')


if __name__ == '__main__':
    check(sys.argv[1])
    print('PASS: ARM64 launcher, private Pixman, isolated RUNPATH and source/license provenance')
