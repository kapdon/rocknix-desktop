#!/usr/bin/python3
"""Local fail-closed contracts; actual network isolation is tested on RP6."""
import io
from pathlib import Path
import runpy
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

api = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'payload/bin/rocknix-lxc-network'))
NetworkLease = api['NetworkLease']
with tempfile.TemporaryDirectory() as directory:
    source = Path(directory) / 'resolv.conf'
    source.write_text('nameserver 127.0.0.53\nnameserver ::1\nnameserver 0.0.0.0\n'
                      'nameserver 224.0.0.1\nnameserver 9.9.9.9\nnameserver 9.9.9.9\n')
    assert api['resolvers'](source) == 'nameserver 9.9.9.9\n'
    source.write_text('nameserver 127.0.0.53\n')
    try:
        api['resolvers'](source)
        raise AssertionError('host-loopback-only DNS accepted')
    except RuntimeError:
        pass

item = NetworkLease.__new__(NetworkLease)
item.pid = 123
def mapping(path):
    return '0 200000 65536\n'
with patch.object(Path, 'stat', return_value=SimpleNamespace(st_uid=200000)), \
        patch.object(Path, 'read_text', mapping), \
        patch('os.readlink', side_effect=['net:[1]', 'net:[1]']):
    try:
        item.verify_container()
        raise AssertionError('host network namespace accepted')
    except RuntimeError:
        pass
with patch.object(Path, 'stat', return_value=SimpleNamespace(st_uid=200000)), \
        patch.object(Path, 'read_text', return_value='0 0 65536\n'):
    try:
        item.verify_container()
        raise AssertionError('native root mapping accepted')
    except RuntimeError:
        pass

with tempfile.TemporaryDirectory() as directory:
    item.root = Path(directory) / 'helper'
    item.root.mkdir()
    item.log = io.StringIO()
    item.child = Mock()
    item.child.poll.return_value = None
    item.child.wait.side_effect = [subprocess.TimeoutExpired('helper', 5), 0]
    item.close()
    item.child.terminate.assert_called_once()
    item.child.kill.assert_called_once()
    assert item.root is None and item.log is None

print('PASS: LXC network DNS, namespace/mapping rejection and bounded helper cleanup')
