#!/usr/bin/python3
"""Check the maintenance boundary without running privileged operations."""
import importlib.machinery
import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'payload/bin/rocknix-maintenance'
loader = importlib.machinery.SourceFileLoader('maintenance', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
args = module.command(Path('/runtime'), Path('/private/policy'), ['apt-get', 'check'])
assert args[-3:] == ['--', 'apt-get', 'check']
assert '--clearenv' in args and '--new-session' in args
assert '--unshare-pid' in args and '--unshare-ipc' in args
assert 'CAP_SYS_ADMIN' not in args and 'CAP_MKNOD' not in args
assert '/run/dbus/system_bus_socket' not in args and '/storage/roms' not in args
for directory in ('/run', '/tmp', '/home', '/root', '/storage', '/sys'):
    assert any(args[i:i+2] == ['--tmpfs', directory] for i in range(len(args)))
assert '--dev' in args and '--dev-bind' not in args
assert '/usr/sbin/policy-rc.d' in args
print('PASS: maintenance private filesystem and capability contracts')
