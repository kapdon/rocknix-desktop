#!/usr/bin/python3
"""Default credentials initialize once; updates preserve chosen/locked hashes."""
from pathlib import Path
import runpy

project = Path(__file__).resolve().parents[1]
api = runpy.run_path(str(project / 'rootfs-overlay/usr/local/bin/rocknix-default-password'))
for value in ('', '!', '!!', '*', '$y$chosen', '!$y$locked', '!!$6$locked', '*disabled*'):
    calls = []
    changed = api['initialize']('root:!:0:0:0:0:::\nrocknix:' + value + ':0:0:0:0:::\n',
                                lambda *args, **kwargs: calls.append((args, kwargs)))
    assert changed == (value in ('', '!', '!!', '*'))
    assert len(calls) == int(changed)
    if changed:
        assert calls[0] == ((['/usr/sbin/chpasswd'],),
                            dict(input='rocknix:rocknix\n', text=True, check=True))
print('PASS: default container credentials and preserved chosen/locked passwords')
