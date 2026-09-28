#!/usr/bin/env python3
"""Exercise the actual jq selection and IPC request without a compositor."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

script = Path('payload/bin/rocknix-close-window').resolve()
def leaf(id=7, **extra):
    return dict(type='con', id=id, focused=True, shell='xdg_shell',
                nodes=[], floating_nodes=[], **extra)

def tree(nodes=(), floating=(), name='98:Desktop'):
    return dict(type='workspace', name=name, nodes=list(nodes),
                floating_nodes=list(floating))

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    stub = root / 'swaymsg'
    stub.write_text('''#!/bin/sh
if [ "$1" = -r ]; then
  printf '%s' "$TREE"
  exit "${TREE_STATUS:-0}"
fi
printf '%s' "$*" >"$REQUEST"
''')
    stub.chmod(0o755)
    cases = [
        (tree([leaf()]), '[con_id=7] kill'),
        (tree(floating=[leaf(8)]), '[con_id=8] kill'),
        (tree([dict(leaf(9), shell='xwayland')]), '[con_id=9] kill'),
        (tree(), ''),
        (tree([dict(leaf(), focused=False)]), ''),
        (tree([leaf()], name='Gaming'), ''),
        (tree([dict(leaf(), shell=None, nodes=[dict(leaf(8), focused=False)])]), ''),
        (tree([leaf(0)]), ''),
        (tree([leaf('7; exit')]), ''),
        (tree([leaf(), leaf(8)]), ''),
        ('invalid JSON', ''),
    ]
    for value, expected in cases:
        request = root / 'request'
        request.unlink(missing_ok=True)
        subprocess.run(['sh', str(script)], check=True, env={**os.environ,
            'PATH': directory + ':' + os.environ['PATH'],
            'TREE': json.dumps(value), 'REQUEST': str(request)}, timeout=5)
        actual = request.read_text() if request.exists() else ''
        assert actual == expected, (value, actual, expected)
    # Even valid-looking output is not trusted when the IPC query fails.
    request.unlink(missing_ok=True)
    subprocess.run(['sh', str(script)], check=True, env={**os.environ,
        'PATH': directory + ':' + os.environ['PATH'],
        'TREE': json.dumps(tree([leaf()])), 'TREE_STATUS': '1',
        'REQUEST': str(request)}, timeout=5)
    assert not request.exists()
print('PASS: close targets one Desktop leaf; empty, parent, foreign and malformed targets are safe')
