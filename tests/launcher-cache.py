#!/usr/bin/env python3
"""Settings and confirmation must never overwrite application usage ordering."""
import os
from pathlib import Path
import subprocess
import tempfile

launcher = Path('rootfs-overlay/usr/local/bin/rocknix-launcher').resolve()
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    stub = root / 'fuzzel'
    stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >"$ARGS"\n')
    stub.chmod(0o755)
    env = {**os.environ, 'HOME': directory, 'XDG_CACHE_HOME': directory,
           'PATH': directory + ':' + os.environ['PATH'], 'ARGS': str(root / 'args')}
    for mode in ('apps', 'settings', 'confirm-return'):
        subprocess.run(['bash', str(launcher), mode], env=env, check=True)
        args = (root / 'args').read_text().splitlines()
        caches = [arg for arg in args if arg.startswith('--cache=')]
        expected = root / 'rocknix-fuzzel' if mode == 'apps' else '/dev/null'
        assert caches == [f'--cache={expected}'], (mode, caches)
        if mode == 'confirm-return':
            assert '--no-sort' in args
print('PASS: only app launches use the favorites/usage cache')
