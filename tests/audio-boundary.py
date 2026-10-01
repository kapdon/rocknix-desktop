#!/usr/bin/python3
from pathlib import Path
import runpy
import subprocess
import sys
import stat
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

base = Path(__file__).resolve().parents[1] / 'payload/bin'
api = runpy.run_path(str(base / 'rocknix-audio'))
bwrap = runpy.run_path(str(base / 'rocknix-helper-sandbox'))
bwrap['sandbox_command'].__globals__['PROBE_UID'] = api['UID']
args = api['command'](bwrap, Path('/trusted/tools'), Path('/run/rocknix-audio'))
assert '--unshare-net' in args and '--unshare-pid' in args
assert args[args.index('--uid') + 1] == '65534'
assert '--disallow-module-loading=yes' in args and '--disallow-exit=yes' in args
assert '--clearenv' in args and '--cap-drop' in args
assert '/storage/rocknix-desktop/data/rootfs' not in ' '.join(args)
config = api['configuration']()
assert 'module-native-protocol-unix socket=/run/audio/pulse' in config
assert config.count('server=unix:/run/native-pulse') == 2
assert 'module-tunnel-sink-new' in config and 'module-tunnel-source-new' in config
desktop = (base / 'rocknix-lxc-desktop').read_text()
assert '/run/0-runtime-dir/pulse/native' not in desktop
assert "self.audio = AUDIO['AudioBridge'](self.tools)" in desktop
assert 'self.audio.close()' in desktop
assert 'runtime.desktop.audio.child.poll()' in (base / 'rocknix-lxc').read_text()

# Apply real irreversible rlimits in a disposable child, never the test runner.
subprocess.run([sys.executable, '-c', '''
import resource, runpy, sys
api = runpy.run_path(sys.argv[1])
dropped = []
api['prepare_child'](lambda: dropped.append(True))
assert dropped == [True]
assert resource.getrlimit(resource.RLIMIT_AS) == (1024**3, 1024**3)
assert resource.getrlimit(resource.RLIMIT_NPROC) == (64, 64)
assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
''', str(base / 'rocknix-audio')], check=True)

bridge = api['AudioBridge']
with tempfile.TemporaryDirectory() as directory:
    work = Path(directory) / 'audio'
    work.mkdir()
    (work / 'state').write_text('test')
    globals_ = bridge.recover.__globals__
    real_lstat = Path.lstat
    def owned(path):
        if path == work:
            return SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_uid=0)
        return real_lstat(path)
    with patch.dict(globals_, WORK=work), patch.object(Path, 'lstat', owned):
        # A live owner's lock must prevent a second recovery from deleting state.
        with patch.object(bridge, 'acquire_lock', side_effect=BlockingIOError):
            try:
                bridge.recover()
                raise AssertionError('live audio owner was ignored')
            except BlockingIOError:
                pass
            assert (work / 'state').exists()
        # Even with exclusive ownership, mounted data is never recursively deleted.
        with patch.object(Path, 'read_text', return_value=f'1 0 0:1 / {work}/native-pulse rw - tmpfs tmpfs rw'):
            try:
                bridge.recover(locked=True)
                raise AssertionError('mounted audio state deleted')
            except RuntimeError:
                pass
            assert work.exists()
        # Exercise orphan cleanup, but use real lstat for shutil's safety checks.
        with patch.object(globals_['shutil'], 'rmtree') as remove:
            bridge.recover(locked=True)
            remove.assert_called_once_with(work)
item = bridge('/trusted/tools')
with patch.object(bridge, 'recover', side_effect=AssertionError('unowned cleanup')):
    item.close()
print('PASS: trusted non-root audio sandbox, fixed tunnels, module/exit denial and isolated network/PID namespaces')
