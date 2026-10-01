#!/usr/bin/python3
"""Run under fakeroot: ownership, setuid and hardlink initialization contracts."""
import os
from pathlib import Path
import runpy
import stat
import tempfile

assert os.geteuid() == 0, 'run under fakeroot'
api = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'payload/bin/rocknix-lxc-storage'))
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    root = base / 'rootfs'
    root.mkdir()
    sudo = root / 'sudo'
    sudo.write_text('fixture')
    sudo.chmod(0o4755)
    os.link(sudo, root / 'sudo-link')
    service = root / 'service'
    service.write_text('service')
    os.chown(service, 100, 101)
    outside = base / 'outside'
    outside.write_text('keep')
    (root / 'redirect').symlink_to(outside)
    api['shift_rootfs'](root)
    assert (sudo.stat().st_uid, sudo.stat().st_gid) == (200000, 200000)
    assert stat.S_IMODE(sudo.stat().st_mode) == 0o4755
    assert (service.stat().st_uid, service.stat().st_gid) == (200100, 200101)
    assert outside.stat().st_uid == 0
    api['shift_rootfs'](root)
    assert sudo.stat().st_uid == 200000
    os.link(outside, root / 'external-hardlink')
    try:
        api['shift_rootfs'](root)
    except RuntimeError:
        pass
    else:
        raise AssertionError('external hardlink accepted')
    assert outside.stat().st_uid == 0
print('PASS: fresh LXC rootfs initialization preserves service IDs, setuid and internal hardlinks')

with tempfile.TemporaryDirectory() as directory:
    data = Path(directory)
    (data / 'rootfs').mkdir()
    (data / 'home').mkdir()
    application = data / 'rootfs/application'
    application.write_text('application')
    profile = data / 'home/profile'
    profile.write_text('existing profile')
    os.chown(profile, 200000, 200000)  # Legitimate guest-root home file, not fresh data.
    try:
        api['initialize_storage'](data)
    except RuntimeError:
        pass
    else:
        raise AssertionError('used home accepted for initial ownership setup')
    assert application.stat().st_uid == 0, 'rootfs changed before home validation'
    assert profile.stat().st_uid == 200000
    profile.unlink()
    api['initialize_storage'](data)
    assert application.stat().st_uid == 200000
    assert (data / 'home').stat().st_uid == 201000
    api['initialize_storage'](data)  # Interrupted initialization may repeat.
    assert application.stat().st_uid == 200000
print('PASS: fresh ownership initialization rejects used home before mutation and supports resume')
