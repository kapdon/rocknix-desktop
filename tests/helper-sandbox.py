#!/usr/bin/python3
"""Trusted helper sandbox contract; not a second Desktop runtime."""
from pathlib import Path
import runpy

api = runpy.run_path('payload/bin/rocknix-helper-sandbox')
args = api['sandbox_command'](Path('/trusted/tools'), Path('/run/helper'), ['/bin/true'])
assert args[args.index('--uid') + 1] == '65534'
for flag in ('--unshare-user', '--unshare-pid', '--unshare-ipc', '--unshare-uts',
             '--die-with-parent', '--clearenv', '--cap-drop'):
    assert flag in args
assert args[args.index('--ro-bind') + 1:args.index('--ro-bind') + 3] == ['/trusted/tools', '/']
assert not any(value.startswith('/dev/dri') or value.startswith('/dev/input') for value in args)
assert '/run/0-runtime-dir/wayland-1' not in args
assert args[-4:] == ['--', '/usr/bin/dbus-run-session', '--', '/bin/true']
assert not any(name in api for name in ('main', 'migrate_home', 'restore_access'))
print('PASS: trusted helper sandbox has no alternate Desktop runtime')
