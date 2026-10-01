#!/usr/bin/env python3
"""Bounded real ENOSPC checks of installed updater primitives on RP6.

Only a private 4 MiB tmpfs is filled. Does not run a bundle update, fill shared
storage, alter the installed journal, or establish power-loss recovery.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import tarfile
import tempfile


def main():
    assert os.geteuid() == 0
    host = Path('/storage/rocknix-desktop/managed/host')
    updater = host / 'bin/rocknix-lxc-upgrade'
    assert not updater.is_symlink() and updater.stat().st_uid == 0
    api = runpy.run_path(str(updater))
    control_paths = [updater, host / 'build-info',
                     host / 'state/upgrade-in-progress.json']
    def hashes():
        return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() if p.exists()
                else None for p in control_paths}
    before = hashes()
    os.unshare(os.CLONE_NEWNS)
    subprocess.run(['mount', '--make-rprivate', '/'], check=True)
    target = Path(tempfile.mkdtemp(prefix='rocknix-space-check-', dir='/run'))
    mounted = False
    try:
        subprocess.run(['mount', '-t', 'tmpfs', '-o', 'size=4m,mode=0700,nosuid,nodev,noexec',
                        'rocknix-space-check', str(target)], check=True)
        mounted = True
        item = tarfile.TarInfo('payload/bin/fixture'); item.size = 4096
        try:
            api['check_staging_space'](target, [item])
        except RuntimeError as error:
            assert 'insufficient update staging space' in str(error), error
        else:
            raise AssertionError('bounded low-space filesystem was accepted')
        assert not list(target.iterdir()), 'preflight wrote into its target'
        tested = []
        for name in ('launcher', 'upgrade-in-progress.json'):
            path = target / name
            original = b'original test control data\n'
            api['atomic'](path, original, 0o600)
            try:
                api['atomic'](path, b'x' * (8 * 1024**2), 0o600)
            except OSError as error:
                assert error.errno == errno.ENOSPC, error
            else:
                raise AssertionError('oversized write did not encounter ENOSPC')
            assert path.read_bytes() == original
            assert path.stat().st_mode & 0o777 == 0o600
            assert not list(target.glob('.rocknix-update-*'))
            # Retry the same primitive after failed-write cleanup freed space.
            api['atomic'](path, b'retry succeeded\n', 0o600)
            assert path.read_bytes() == b'retry succeeded\n'
            tested.append(name)
        assert hashes() == before, 'installed control data changed'
        print(json.dumps({'private_tmpfs_bytes': 4 * 1024**2,
            'low_space_rejected': True, 'real_enospc_preserves_old_files': tested,
            'temporary_files_cleaned': True, 'retry_succeeds': True,
            'installed_control_hashes_unchanged': True}), flush=True)
    finally:
        if mounted:
            subprocess.run(['umount', str(target)], check=True)
        target.rmdir()


if __name__ == '__main__':
    main()
