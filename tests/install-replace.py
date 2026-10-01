#!/usr/bin/python3
"""Test confirmed replacement using real isolated filesystem trees."""
import os
from pathlib import Path
import runpy
import stat
import tempfile

replace = runpy.run_path('payload/bin/rocknix-install-replace')['replace']


def safe(path):
    # Validate test-owned paths; /tmp ancestry deliberately excluded.
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise RuntimeError('unsafe fixture path')


for scenario in ('complete', 'partial', 'linked-data', 'custom-unit', 'mounted', 'guard-link'):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project = root / 'project'
        shared = root / 'shared'
        shared.mkdir()
        (shared / 'keep').write_text('personal')
        (project / 'managed/host').mkdir(parents=True)
        (project / 'data/home').mkdir(parents=True)
        (project / 'data/home/profile').write_text('desktop profile')
        (project / 'data/home/external').symlink_to(shared, target_is_directory=True)
        (project / 'install.sh').write_text('keep installer')
        staging = project / 'install.test/bundle'
        staging.mkdir(parents=True)
        (staging / 'candidate').write_text('keep candidate')
        guard = project / '.fresh-install.json'
        guard.write_text('partial transaction')
        native = root / 'native'
        native.mkdir()
        unit = native / 'desktop.service'
        unit.write_bytes(b'known service')
        targets = {unit: b'known service', native / 'missing-hook': b'hook'}
        if scenario == 'partial':
            unit.unlink()
        if scenario == 'linked-data':
            (project / 'data').rename(root / 'held')
            (project / 'data').symlink_to(root / 'held')
        if scenario == 'custom-unit':
            unit.write_text('personal service')
        if scenario == 'guard-link':
            guard.unlink()
            guard.symlink_to(shared / 'keep')
        def no_mounts(path):
            if scenario == 'mounted':
                raise RuntimeError('live mount')
        valid = scenario in ('complete', 'partial')
        try:
            replace(project, targets, safe, no_mounts)
            assert valid
            assert not (project / 'managed').exists() and not (project / 'data').exists()
            assert not guard.exists() and not unit.exists()
            # Re-running after an interrupted/complete deletion is ordinary Install.
            replace(project, targets, safe, no_mounts)
        except RuntimeError:
            assert not valid
            assert (project / 'managed/host').exists()
        assert (shared / 'keep').read_text() == 'personal'
        assert (project / 'install.sh').exists() and (staging / 'candidate').exists()
print('PASS: exact Desktop replacement, retry, shared-data preservation and pre-deletion refusal')
