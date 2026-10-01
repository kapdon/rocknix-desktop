#!/usr/bin/python3
"""Maintenance must fail closed while Desktop starts or stops; no host actions."""
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

for script, function in (
        ('rocknix-lxc-upgrade', 'idle'),
        ('rocknix-desktop-maintenance', 'require_idle')):
    idle = runpy.run_path('payload/bin/' + script)[function]
    for state in ('inactive', 'active', 'activating', 'deactivating',
                  'reloading', 'failed', '', 'unknown'):
        def run(args, **kwargs):
            if args[1] == 'show':
                assert args == ['systemctl', 'show', '--property=ActiveState',
                                '--value', 'rocknix-desktop.service']
                assert kwargs == dict(capture_output=True, text=True, check=True)
                return SimpleNamespace(stdout=state + '\n', returncode=0)
            assert state == 'inactive', 'continued checks despite unsafe Desktop state'
            return SimpleNamespace(returncode=0)

        with patch('subprocess.run', side_effect=run), \
                patch.dict(idle.__globals__, no_mounts=lambda path: None), \
                patch('os.path.lexists', return_value=False), \
                patch.object(Path, 'glob', return_value=[]):
            try:
                idle()
            except RuntimeError:
                assert state != 'inactive'
            else:
                assert state == 'inactive', (script, state)

    with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'systemctl')):
        try:
            idle()
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError('systemctl failure was treated as idle')

print('LXC maintenance requires confirmed inactive Desktop: PASS')
