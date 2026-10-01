#!/usr/bin/python3
"""Run under fakeroot: classifier ownership and unsafe-path boundaries."""
import os
from pathlib import Path
import runpy
import tempfile

api = runpy.run_path('payload/bin/rocknix-install-state')
with tempfile.TemporaryDirectory() as directory:
    project = Path(directory) / 'project'
    checked = []
    def probe(root):
        checked.append(root)
        return None
    def state():
        return api['classify'](project, probe)['status']
    assert state() == 'absent'
    project.mkdir()
    (project / 'install.sh').write_text('installer')
    assert state() == 'absent'
    host = project / 'managed/host'
    host.mkdir(parents=True)
    assert state() == 'invalid' and not checked
    for path in (host / 'state', project / 'data', host / 'bin', host / 'input',
                 host / 'integration', host / 'host-tools'):
        path.mkdir()
    for name, owner in (('rootfs', 200000), ('home', 201000)):
        path = project / 'data' / name
        path.mkdir()
        os.chown(path, owner, owner)
    for name in api['HOST_FILES']:
        path = host / name
        path.write_text('fixture')
        path.chmod(0o755)
    (host / 'build-info').write_text('commit=' + 'a' * 40 + '\narchitecture=arm64\n')
    assert state() == 'healthy' and len(checked) == 1
    assert api['classify'](project, lambda root: 'guest failed boot')['status'] == 'invalid'
    guard = project / '.fresh-install.json'
    guard.write_text('interrupted')
    assert state() == 'invalid'
    guard.unlink()
    target = host / 'bin/rocknix-lxc'
    target.unlink()
    assert state() == 'invalid'
    target.symlink_to('/usr/bin/python3')
    try:
        state()
        raise AssertionError('linked privileged executable accepted')
    except RuntimeError:
        pass
    target.unlink()
    target.write_text('fixture')
    target.chmod(0o777)
    try:
        state()
        raise AssertionError('writable privileged executable accepted')
    except RuntimeError:
        pass
print('PASS: absent/partial/healthy distinction, mandatory guest probe and unsafe-path refusal')
