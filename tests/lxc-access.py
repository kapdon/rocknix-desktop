#!/usr/bin/python3
"""Local lifecycle contracts for the host-owned LXC access journal."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import stat

project = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('lxc_access', str(project / 'payload/bin/rocknix-lxc-access'))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)

for path in ('/run/dbus/system_bus_socket', '/storage/scripts', '/dev/video1', '/dev/dri/card0'):
    with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=0, st_mode=stat.S_IFSOCK | 0o777)):
        try:
            module.AccessLease.validate(path)
            raise AssertionError(f'unlisted endpoint accepted: {path}')
        except RuntimeError:
            pass


def lease(directory, fail_grant=False):
    item = module.AccessLease.__new__(module.AccessLease)
    item.state = Path(directory) / 'state'
    item.state.mkdir(mode=0o700)
    item.validate = lambda path: SimpleNamespace(st_dev=1, st_ino=2)
    item.acl = 'original ACL'
    item.restores = 0
    def command(name, *args, input=None):
        if name == 'getfacl':
            return item.acl
        if args[0] == '-m':
            saved = json.loads((item.state / 'grants.json').read_text())
            assert saved[0]['acl'] == 'original ACL'  # Must precede mutation.
            if fail_grant:
                raise RuntimeError('injected setfacl failure')
            item.acl = 'temporary desktop ACL'
        else:
            assert args == ('--restore=-',)
            item.restores += 1
            item.acl = input
        return ''
    item.command = command
    return item


with tempfile.TemporaryDirectory(prefix='lxc-access-test-') as directory:
    item = lease(directory)
    item.grant('/run/0-runtime-dir/wayland-1')
    assert item.acl != 'original ACL'
    try:
        item.grant('/run/0-runtime-dir/wayland-1')
        raise AssertionError('duplicate grant accepted')
    except RuntimeError:
        pass
    item.restore()
    assert item.acl == 'original ACL' and not item.state.exists()

    item = lease(directory, fail_grant=True)
    try:
        item.grant('/run/0-runtime-dir/wayland-1')
        raise AssertionError('failure injection did not run')
    except RuntimeError:
        pass
    assert (item.state / 'grants.json').exists()
    item.restore()
    assert item.restores == 1 and not item.state.exists()

    item = lease(directory)
    item.grant('/run/0-runtime-dir/wayland-1')
    item.validate = lambda path: SimpleNamespace(st_dev=1, st_ino=999)
    try:
        item.restore()
        raise AssertionError('replacement inode accepted')
    except RuntimeError:
        pass
    assert item.restores == 0 and (item.state / 'grants.json').exists()

print('PASS: LXC ACL journal precedes grants, restores setup failures and rejects replaced endpoints')
