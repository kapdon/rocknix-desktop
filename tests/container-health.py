#!/usr/bin/python3
from pathlib import Path
import runpy
import stat
from types import SimpleNamespace
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
api = runpy.run_path(str(root / 'payload/guest/check-container.py'))
with patch('os.geteuid', return_value=0):
    for mapping in ('0 200000 65536', '0 0 4294967295', '0 200000 1'):
        with patch.object(Path, 'read_text', return_value=mapping):
            try:
                api['check_mapping']()
                assert mapping == '0 200000 65536'
            except RuntimeError:
                assert mapping != '0 200000 65536'
user = SimpleNamespace(pw_uid=1000, pw_gid=1000, pw_dir='/home/rocknix')
with patch('pwd.getpwnam', return_value=user), \
     patch('grp.getgrgid', return_value=SimpleNamespace(gr_name='rocknix')), \
     patch('grp.getgrnam', return_value=SimpleNamespace(gr_mem=['rocknix'])):
    for owner, mode, valid in ((0, stat.S_IFREG | 0o4755, True),
                               (0, stat.S_IFREG | 0o755, False),
                               (1000, stat.S_IFREG | 0o4755, False)):
        with patch.object(Path, 'stat', return_value=SimpleNamespace(st_uid=owner, st_mode=mode)):
            try:
                api['check_user']()
                assert valid
            except RuntimeError:
                assert not valid
for broken in ('', 'package', 'audit', 'sudo'):
    def run(*args):
        if args[0] == 'dpkg-query':
            return 'install ok unpacked' if broken == 'package' else 'install ok installed'
        if args == ('dpkg', '--audit'):
            return 'pending package' if broken == 'audit' else ''
        if args[0] == 'sudo' and broken == 'sudo':
            raise RuntimeError('sudo denied')
        return ''
    with patch.dict(api['check_packages'].__globals__, run=run):
        try:
            api['check_packages']()
            assert not broken
        except RuntimeError:
            assert broken
print('PASS: container health refuses host root, broken identity/sudo and incomplete packages')
