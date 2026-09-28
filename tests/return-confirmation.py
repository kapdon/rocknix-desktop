#!/usr/bin/env python3
"""Exercise the exit gate without a compositor or a real Desktop session."""
import os
from pathlib import Path
import subprocess
import tempfile

source = Path('rootfs-overlay/usr/local/bin/rocknix-return').read_text()
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    fifo = root / 'control'
    os.mkfifo(fifo)
    reader = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    launcher = root / 'launcher'
    launcher.write_text('#!/bin/sh\nprintf "%s" "$ANSWER"\nexit "$RESULT"\n')
    launcher.chmod(0o755)
    script = root / 'return'
    script.write_text(source.replace('/run/rocknix-xfce', directory).replace(
        '/usr/local/bin/rocknix-launcher', str(launcher)))
    for answer, result, expected in [
        ('Cancel — stay in Desktop Mode', '0', b''),
        ('', '1', b''),
        ('Return to Gaming', '0', b''),
        ('Return to Gaming — close desktop apps', '1', b''),
        ('Return to Gaming — close desktop apps', '0', b'return\n'),
    ]:
        subprocess.run(['sh', str(script)], check=True, timeout=5,
                       env={**os.environ, 'ANSWER': answer, 'RESULT': result,
                            'XDG_RUNTIME_DIR': directory})
        try:
            actual = os.read(reader, 4096)
        except BlockingIOError:
            actual = b''
        assert actual == expected, (answer, result, actual)
    os.close(reader)
print('PASS: cancel, dismissal, failure and unexpected output cannot exit Desktop')
