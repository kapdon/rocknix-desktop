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
    # Physical RP6 and narrow logical outputs, with keyboard space reserved.
    # Match Fuzzel's pixel geometry, not its default point interpretation.
    for width, height, bar, keyboard, row, pad in (
        (1920, 1080, 80, 378, 88, 19),
        (1280, 720, 53, 252, 59, 13),
        (960, 540, 40, 189, 44, 10),
        (800, 480, 40, 168, 38, 10),
    ):
        sizing = dict(env, ROCKNIX_LOGICAL_WIDTH=str(width),
                      ROCKNIX_LOGICAL_HEIGHT=str(height), ROCKNIX_BAR_HEIGHT=str(bar),
                      ROCKNIX_KEYBOARD_HEIGHT=str(keyboard), ROCKNIX_LAUNCHER_FONT_SIZE='20',
                      ROCKNIX_LAUNCHER_LINE_HEIGHT=str(row),
                      ROCKNIX_LAUNCHER_HORIZONTAL_PAD='12',
                      ROCKNIX_LAUNCHER_VERTICAL_PAD=str(pad))
        for mode in ('apps', 'settings', 'confirm-return'):
            subprocess.run(['bash', str(launcher), mode], env=sizing, check=True)
            args = (root / 'args').read_text().splitlines()
            assert f'--line-height={row}px' in args
            lines = int(next(a.split('=')[1] for a in args if a.startswith('--lines=')))
            assert lines >= 1
            assert (lines + 1) * row + 2 * pad + 6 <= height - bar - keyboard - 48
print('PASS: only app launches use the favorites/usage cache')
print('PASS: launcher rows and chrome fit keyboard-visible RP6 and narrow output budgets')
