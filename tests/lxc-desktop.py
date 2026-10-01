#!/usr/bin/python3
"""Host-defined desktop surface contracts, without touching live mounts."""
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, Mock
import stat
import inspect

api = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'payload/bin/rocknix-lxc-desktop'))
arch = api['FEX_ARCH']
assert str(arch) == '/storage/.local/share/fex-emu/RootFS/ArchLinux'
with patch('os.path.lexists', return_value=False):
    assert api['fex_arch_source']() is None
for owner, mode, denied in ((1000, stat.S_IFDIR | 0o755, False),
                            (0, stat.S_IFDIR | 0o755, False),
                            (201000, stat.S_IFDIR | 0o755, True),
                            (1000, stat.S_IFDIR | 0o777, True),
                            (1000, stat.S_IFLNK | 0o755, True)):
    def fake_stat(path):
        return SimpleNamespace(st_uid=owner if path == arch else 0,
                               st_mode=mode if path == arch else stat.S_IFDIR | 0o755)
    with patch('os.path.lexists', return_value=True), patch.object(Path, 'lstat', fake_stat):
        try:
            assert api['fex_arch_source']() == arch
        except RuntimeError:
            assert denied
        else:
            assert not denied
assert 'scripts' not in api['SHARED']
assert 'roms' not in api['SHARED']
assert 'games-external' in api['SHARED'] and 'games-internal' in api['SHARED']
assert inspect.signature(api['DesktopMounts']).parameters['bridge'].default == Path('/run/rocknix-desktop')
source_root = Path(__file__).resolve().parents[1]
mount_source = (source_root / 'payload/bin/rocknix-lxc-desktop').read_text()
assert 'run/rocknix-desktop none bind,ro,create=dir' in mount_source
assert 'run/rocknix-desktop/bin/FEX' not in mount_source
assert 'remount,bind,ro,nosuid,nodev' in mount_source
assert 'run/rocknix-fex/ArchLinux none bind,ro,nosuid,nodev,create=dir' in mount_source
assert len(api['FEX_FILES']) == 3
resolver = api['fex_sources']
with patch.dict(resolver.__globals__, fex_arch_source=Mock(return_value=None),
                fex_host_file=Mock(side_effect=AssertionError('unneeded file lookup'))):
    assert resolver() is None
with patch.dict(resolver.__globals__, fex_arch_source=Mock(return_value=arch),
                fex_host_file=Mock(side_effect=FileNotFoundError)):
    assert resolver() is None
with patch.dict(resolver.__globals__, fex_arch_source=Mock(return_value=arch),
                fex_host_file=Mock(side_effect=RuntimeError('unsafe source'))):
    try:
        resolver()
        raise AssertionError('unsafe runtime silently accepted')
    except RuntimeError:
        pass
with patch.dict(resolver.__globals__, fex_arch_source=Mock(return_value=arch),
                fex_host_file=lambda source: Path(source)):
    resolved_arch, files = resolver()
    assert resolved_arch == arch
    assert files == [(Path(source), name, dest) for source, name, dest in api['FEX_FILES']]
native = Path('/usr/lib/libfmt.so.12.2.0')
for owner, mode, denied in ((0, stat.S_IFREG | 0o755, False),
                            (200000, stat.S_IFREG | 0o755, True),
                            (0, stat.S_IFREG | 0o775, True),
                            (0, stat.S_IFDIR | 0o755, True)):
    def native_stat(path):
        return SimpleNamespace(st_uid=owner if path == native else 0,
                               st_mode=mode if path == native else stat.S_IFDIR | 0o755)
    with patch.object(Path, 'resolve', return_value=native), \
         patch.object(Path, 'lstat', native_stat), patch.object(Path, 'stat', native_stat):
        try:
            assert api['fex_host_file']('/usr/lib/libfmt.so.12') == native
        except RuntimeError:
            assert denied
        else:
            assert not denied
assert {destination for _, _, destination in api['FEX_FILES']} == {'bin/FEX', 'bin/FEXServer', 'lib/libfmt.so.12'}
assert 'run/rocknix-fex/{destination} none bind,ro,nosuid,nodev,create=file' in mount_source
wrapper = (source_root / 'rootfs-overlay/usr/local/bin/rocknix-fex').read_text()
assert 'export FEX_ROOTFS="$runtime/ArchLinux"' in wrapper
assert 'export LD_LIBRARY_PATH="$runtime/lib"' in wrapper
assert 'exec "$runtime/bin/FEX" "$@"' in wrapper
updater = runpy.run_path(str(source_root / 'rootfs-overlay/usr/local/bin/rocknix-container-update'))
assert updater['allowed']('usr/local/bin/FEX')
assert not updater['allowed']('usr/bin/FEX')
assert not updater['allowed']('usr/local/bin/FEXServer')
for relative in ['rootfs-overlay/etc/systemd/system/rocknix-desktop-session.service',
                 'rootfs-overlay/usr/local/bin/rocknix-lxc-session',
                 'rootfs-overlay/usr/local/bin/rocknix-return']:
    assert '/run/rocknix-desktop/control' in (source_root / relative).read_text()
env = api['session_environment']({'ROCKNIX_OUTPUT_NAME': 'DSI-1', 'ROCKNIX_LOGICAL_WIDTH': '1920',
                                  'TZ': 'America/Los_Angeles',
                                  'LD_PRELOAD': '/evil', 'PATH': '/evil', 'ROCKNIX_UNKNOWN': 'x'})
assert 'ROCKNIX_OUTPUT_NAME=DSI-1\n' in env
assert 'ROCKNIX_LOGICAL_WIDTH=1920\n' in env
assert '/evil' not in env and 'UNKNOWN' not in env
assert 'TZ=America/Los_Angeles\n' in env
for values in ({'ROCKNIX_OUTPUT_NAME': 'DSI-1\nLD_PRELOAD=/evil'},
               {'ROCKNIX_KEYBOARD_HEIGHT': '-1'}, {'ROCKNIX_LOGICAL_WIDTH': 'abc'}):
    try:
        api['session_environment'](values)
        raise AssertionError('unsafe session environment accepted')
    except RuntimeError:
        pass

with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=201000, st_mode=stat.S_IFLNK | 0o777)):
    try:
        api['trusted_directory'](Path('/storage/desktop/home'), 201000)
        raise AssertionError('symlink home accepted')
    except RuntimeError:
        pass

with tempfile.TemporaryDirectory() as directory:
    state = Path(directory)
    stages = state / 'desktop-mounts'
    stages.mkdir()
    unrelated = stages / 'unexpected'
    unrelated.write_text('keep')
    try:
        api['DesktopMounts'].recover(Path('/unused'), state)
        raise AssertionError('unexpected staging file removed')
    except RuntimeError:
        pass
    assert unrelated.read_text() == 'keep'

print('PASS: LXC desktop mount allowlist, environment filtering and fail-closed staging cleanup')
