#!/usr/bin/python3
from pathlib import Path
import runpy
import tempfile

repair = runpy.run_path('rootfs-overlay/usr/local/bin/rocknix-container-hostname')['repair']
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'etc').mkdir()
    hostname, hosts = root / 'etc/hostname', root / 'etc/hosts'
    hostname.write_text('personal-handheld\n')
    original = '127.0.0.1 localhost\n10.0.0.5 my-server # custom'
    hosts.write_text(original)
    assert repair(root)
    assert hosts.read_text() == original + '\n127.0.1.1 personal-handheld\n'
    assert not repair(root)
    hosts.write_text('127.0.1.1 custom personal-handheld # keep\n')
    assert not repair(root)
    hostname.write_text('invalid name\n')
    try:
        repair(root)
    except RuntimeError:
        pass
    else:
        raise AssertionError('invalid hostname accepted')
print('PASS: hostname alias is idempotent and preserves guest customization')
