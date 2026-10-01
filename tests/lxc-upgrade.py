#!/usr/bin/python3
"""Host bundle selection and archive-link safety; no device mutations."""
import hashlib
import errno
import io
from pathlib import Path
import runpy
import tarfile
import tempfile
import stat
from types import SimpleNamespace
from unittest.mock import patch

api = runpy.run_path('payload/bin/rocknix-lxc-upgrade')
with tempfile.TemporaryDirectory() as directory:
    host = Path(directory) / 'bin'
    host.mkdir()
    (host / 'current').write_text('keep')
    (host / 'retired').write_text('remove')
    outside = Path(directory) / 'user-data'
    outside.write_text('untouched')
    (host / 'redirect').symlink_to(outside)
    try:
        api['prune_host_files'](host, {'current'})
    except RuntimeError:
        pass
    else:
        raise AssertionError('unsafe payload accepted')
    assert (host / 'retired').exists()  # Validate all removals before touching any.
    (host / 'redirect').unlink()
    api['prune_host_files'](host, {'current'})
    assert sorted(path.name for path in host.iterdir()) == ['current']
    assert outside.read_text() == 'untouched'
print('PASS: retired host payload files removed without following redirects')
extract = api['extract']
metadata = 'commit=' + 'a' * 40 + '\narchitecture=arm64\n'

def add(archive, name, data):
    member = tarfile.TarInfo(name)
    member.size = len(data)
    archive.addfile(member, io.BytesIO(data))

integration = io.BytesIO()
with tarfile.open(fileobj=integration, mode='w:gz') as archive:
    add(archive, 'etc/rocknix-desktop-release', b'ROCKNIX_LXC_RUNTIME=1\n')
    add(archive, 'etc/rocknix-desktop-build-info', metadata.encode())

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    for case in ('valid', 'missing-paths', 'symlink-parent', 'hardlink-symlink'):
        bundle = base / (case + '.tar.xz')
        target = base / case
        target.mkdir()
        with tarfile.open(bundle, 'w:xz') as archive:
            add(archive, 'build-info', metadata.encode())
            add(archive, 'desktop-integration.tar.gz', integration.getvalue())
            add(archive, 'rootfs/do-not-extract', b'guest rootfs')
            add(archive, 'payload/bin/test', b'host launcher')
            if case != 'missing-paths':
                add(archive, 'payload/bin/rocknix-desktop-paths', b'canonical paths')
            add(archive, 'host-tools/usr/lib/test', b'host library')
            link = tarfile.TarInfo('host-tools/lib')
            link.type = tarfile.SYMTYPE
            link.linkname = '/usr/lib'
            archive.addfile(link)
            if case == 'symlink-parent':
                add(archive, 'host-tools/lib/escape', b'bad')
            if case == 'hardlink-symlink':
                hard = tarfile.TarInfo('host-tools/evil')
                hard.type = tarfile.LNKTYPE
                hard.linkname = 'host-tools/lib'
                archive.addfile(hard)
        digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
        with patch.dict(extract.__globals__, safe_directory=lambda path: None):
            if case == 'valid':
                assert extract(bundle, digest, target) == 'a' * 40
                assert not (target / 'rootfs').exists()
                assert (target / 'payload/bin/test').read_bytes() == b'host launcher'
                try:
                    extract(bundle, '0' * 64, target)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('wrong checksum accepted')
            else:
                try:
                    extract(bundle, digest, target)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('unsafe link graph accepted')
print('PASS: LXC host update excludes replacement rootfs and rejects checksum/link attacks')

# A low-space refusal must precede extraction, leaving the candidate empty.
space_check = api['check_staging_space']
member = tarfile.TarInfo('payload/bin/probe'); member.size = 4097
required = api['UPDATE_RESERVE'] + 8192
with patch.object(api['shutil'], 'disk_usage', return_value=SimpleNamespace(free=required)):
    space_check(Path('/fixture'), [member])
with patch.object(api['shutil'], 'disk_usage', return_value=SimpleNamespace(free=required - 1)):
    try:
        space_check(Path('/fixture'), [member])
    except RuntimeError as error:
        assert 'insufficient update staging space' in str(error)
    else:
        raise AssertionError('rounded staging threshold ignored')
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    bundle = base / 'candidate.tar.xz'
    target = base / 'stage'; target.mkdir()
    with tarfile.open(bundle, 'w:xz') as archive:
        add(archive, 'payload/bin/probe', b'candidate')
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    with patch.object(api['shutil'], 'disk_usage', return_value=SimpleNamespace(free=0)):
        try:
            extract(bundle, digest, target)
        except RuntimeError as error:
            assert 'insufficient update staging space' in str(error)
        else:
            raise AssertionError('low-space candidate accepted')
    assert not list(target.iterdir())

# Simulate ENOSPC at the durable-write boundary: old control files and guards
# must survive, and the incomplete atomic temporary must be removed.
atomic = api['atomic']
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    for name in ('launcher', 'upgrade-in-progress.json'):
        target = base / name
        target.write_bytes(b'previous trusted content')
        with patch.dict(atomic.__globals__, safe_directory=lambda _: None), \
             patch.object(api['os'], 'fsync', side_effect=OSError(errno.ENOSPC, 'test storage full')):
            try:
                atomic(target, b'new candidate')
            except OSError as error:
                assert error.errno == errno.ENOSPC
            else:
                raise AssertionError('ENOSPC ignored')
        assert target.read_bytes() == b'previous trusted content'
        assert not list(base.glob('.rocknix-update-*'))
print('PASS: low-space staging refusal and ENOSPC atomic-file preservation')

validate = api['validate_existing_storage']
base = Path('/fixture')
for bad in (None, 'rootfs', 'home', 'symlink'):
    def fake_stat(path):
        assert path in (base / 'rootfs', base / 'home'), 'must not traverse guest descendants'
        owner = 200000 if path.name == 'rootfs' else 201000
        if path.name == bad:
            owner = 0
        mode = stat.S_IFLNK if bad == 'symlink' else stat.S_IFDIR
        return SimpleNamespace(st_uid=owner, st_gid=owner, st_mode=mode | 0o755)
    with patch.dict(validate.__globals__, safe_directory=lambda path: None), \
            patch.object(Path, 'lstat', fake_stat), \
            patch('os.chown', side_effect=AssertionError('updates must never chown guest data')):
        try:
            validate(base)
        except RuntimeError:
            assert bad is not None
        else:
            assert bad is None
source = Path('payload/bin/rocknix-lxc-upgrade').read_text()
assert 'shift_rootfs' not in source and 'migrate_home' not in source
print('PASS: LXC updates validate mapped roots without traversing or re-owning guest data')

select = api['select_layout']
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for case in ('absent', 'new', 'partial', 'fresh', 'fresh-link'):
        project = root / case
        project.mkdir()
        host = project / 'managed/host'
        if case != 'absent':
            (host / 'state').mkdir(parents=True)
            (project / 'data/rootfs').mkdir(parents=True)
            if case != 'partial':
                (project / 'data/home').mkdir()
        if case == 'fresh':
            (project / '.fresh-install.json').write_text('{}')
        elif case == 'fresh-link':
            (project / '.fresh-install.json').symlink_to('/nonexistent')
        try:
            selected = select(project)
        except RuntimeError:
            assert case != 'new'
        else:
            assert case == 'new'
            assert selected == (host, project / 'data', host / 'state', host / 'state/upgrade-in-progress.json')
    source = root / 'template'
    source.write_text('ConditionPathIsDirectory=/storage/rocknix-desktop/data/rootfs\n'
                      'ExecStart=/storage/rocknix-desktop/managed/host/bin/launch-sway-desktop\n')
    render = api['integration_bytes']
    with patch.dict(render.__globals__, BASE=Path('/fixture/managed/host'),
                    ROOTFS=Path('/fixture/data/rootfs')):
        assert render(source).decode() == (
            'ConditionPathIsDirectory=/fixture/data/rootfs\n'
            'ExecStart=/fixture/managed/host/bin/launch-sway-desktop\n')
print('PASS: updater requires complete separated storage and renders current native integration')
