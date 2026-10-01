#!/usr/bin/python3
"""Local configuration-path/journal checks; full startup runs on RP6."""
import json
import os
from pathlib import Path
import runpy
import stat
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

api = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'payload/bin/rocknix-lxc'))
with patch('os.geteuid', return_value=0), \
        patch.dict(api['NETWORK'], {'trusted_tools': lambda path: path}):
    recovery = api['Runtime']('/trusted-tools', '/missing-guest-rootfs', recovery_only=True)
    try:
        recovery.start()
        raise AssertionError('recovery-only object can start a runtime')
    except RuntimeError:
        pass
for path in ('relative', '/tmp/root\nlxc.hook.start=/bin/false', '/tmp/root fs',
             '/tmp/../etc', '/tmp/root,ro', '/tmp/root\\fs'):
    try:
        api['safe_path'](path)
        raise AssertionError(f'unsafe LXC config path accepted: {path}')
    except RuntimeError:
        pass
assert api['safe_path']('/storage/rocknix-desktop/rootfs') == Path('/storage/rocknix-desktop/rootfs')

with tempfile.TemporaryDirectory() as directory:
    item = api['Runtime'].__new__(api['Runtime'])
    item.state = Path(directory)
    record = {'memory_enabled': True, 'scope_created': False}
    item.save(record)
    journal = item.state / 'resources.json'
    assert json.loads(journal.read_text()) == record
    assert stat.S_IMODE(journal.stat().st_mode) == 0o600
    assert not (item.state / 'resources.new').exists()
    record['scope_created'] = True
    item.save(record)
    assert json.loads(journal.read_text()) == record
    target = item.state / 'unrelated'
    target.write_text('keep')
    (item.state / 'resources.new').symlink_to(target)
    try:
        item.save(record)
        raise AssertionError('journal symlink followed')
    except FileExistsError:
        pass
    assert target.read_text() == 'keep'

    (item.state / 'resources.new').unlink()
    item.save({'owner': os.getpid(), 'identity': api['process_identity'](os.getpid())})
    item.close = Mock()
    def recovery_stat(path):
        mode = stat.S_IFDIR | 0o711 if path == item.state else stat.S_IFREG | 0o600
        return SimpleNamespace(st_uid=0, st_mode=mode)
    with patch.object(Path, 'lstat', recovery_stat):
        try:
            item.recover()
            raise AssertionError('recovery accepted a live supervisor')
        except RuntimeError:
            pass
        item.close.assert_not_called()
        item.save({'owner': 2147483647, 'identity': 'absent-process'})
        item.recover()
        item.close.assert_called_once()

print('PASS: LXC supervisor rejects config injection, protects journals and refuses live-owner recovery')
