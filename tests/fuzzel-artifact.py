#!/usr/bin/env python3
"""Exercise artifact rejection independently of Docker and device access."""
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch

check = runpy.run_path('build-support/fuzzel/check-artifact.py')['check']
dynamic = (' (NEEDED) Shared library: [libpixman-1.so.0]\n'
           ' (RUNPATH) Library runpath: [/opt/rocknix-fuzzel/lib]\n')


def fixture(root):
    header = b'\x7fELF\x02\x01' + bytes(12) + (183).to_bytes(2, 'little')
    for name in ('bin/fuzzel', 'lib/libpixman-1.so.0.46.4'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(header)
        path.chmod(0o755)
    (root / 'lib/libpixman-1.so.0').symlink_to('libpixman-1.so.0.46.4')
    for name in ('fuzzel.tar.gz', 'pixman.tar.gz', 'protocols.tar.xz',
                 'aarch64.ini', 'build.Dockerfile', 'check-artifact.py', 'pixman-COPYING'):
        path = root / 'share/source' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    path = root / 'share/doc/fuzzel/LICENSE'
    path.parent.mkdir(parents=True)
    path.touch()


for case in ('valid', 'wrong-architecture', 'missing-library', 'escaping-library',
             'not-executable', 'missing-source', 'wrong-runpath', 'missing-needed'):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / 'private'
        fixture(root)
        output = dynamic
        if case == 'wrong-architecture':
            (root / 'bin/fuzzel').write_bytes(b'not ARM64')
        elif case in ('missing-library', 'escaping-library'):
            link = root / 'lib/libpixman-1.so.0'
            link.unlink()
            if case == 'escaping-library':
                outside = Path(directory) / 'outside.so'
                outside.write_bytes((root / 'lib/libpixman-1.so.0.46.4').read_bytes())
                link.symlink_to(outside)
        elif case == 'not-executable':
            (root / 'bin/fuzzel').chmod(0o644)
        elif case == 'missing-source':
            (root / 'share/source/fuzzel.tar.gz').unlink()
        elif case == 'wrong-runpath':
            output = output.replace('/opt/rocknix-fuzzel/lib', '/usr/lib')
        elif case == 'missing-needed':
            output = output.replace('[libpixman-1.so.0]', '[libother.so]')
        with patch('subprocess.check_output', return_value=output):
            try:
                check(root)
            except (ValueError, FileNotFoundError):
                assert case != 'valid', case
            else:
                assert case == 'valid', case
print('PASS: private launcher artifact accepts valid metadata and rejects seven broken forms')
