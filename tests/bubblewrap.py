#!/usr/bin/env python3
"""Offline launch-contract tests; hardware results are documented separately."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import tempfile
import subprocess
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "payload/bin/rocknix-bwrap"
loader = importlib.machinery.SourceFileLoader("runtime", str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
runtime = importlib.util.module_from_spec(spec)
loader.exec_module(runtime)

with patch.dict(os.environ, {"SWAYSOCK": "/host/root.sock",
                            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/host/bus",
                            "MOZ_DISABLE_CONTENT_SANDBOX": "1",
                            "ROCKNIX_BAR_HEIGHT": "80"}, clear=True):
    args = runtime.sandbox_command(Path("/test/root"), Path("/test/run"),
                                   ["/usr/local/bin/rocknix-sway-session"], True, True)
assert "--clearenv" in args
assert "--unshare-user" in args and "--unshare-pid" in args
assert "--cap-drop" in args
assert args[args.index("--uid") + 1] == "62000"
assert "/host/root.sock" not in args and "unix:path=/host/bus" not in args
assert "MOZ_DISABLE_CONTENT_SANDBOX" not in args
assert "--no-sandbox" not in args
assert "--disable-userns" not in args  # browsers need nested user namespaces
assert "--unshare-net" not in args  # explicit shared networking, not hidden NAT
assert "/dev/input" not in args and "/dev/dri/card0" not in args
assert "ROCKNIX_BAR_HEIGHT" in args
assert "/usr/bin/dbus-run-session" in args
assert args[args.index("--ro-bind") + 1:args.index("--ro-bind") + 3] == ["/test/root", "/"]
video_args = runtime.sandbox_command(Path('/test/root'), Path('/test/run'),
                                    ['/bin/true'], True, True, ['/dev/video0'])
assert video_args.count('/dev/video0') == 2
assert '/dev/video1' not in video_args
assert '/dev/video0' not in args

# Exercise a host where every shared directory, including scripts, exists.
# The allowlist must not grow simply because another host directory exists.
with patch.object(Path, 'is_dir', return_value=True):
    shared_args = runtime.sandbox_command(Path('/test/root'), Path('/test/run'),
                                         ['/bin/true'], True, True)
assert '/storage/scripts' not in shared_args
assert '/storage' not in [shared_args[i + 1] for i, value in enumerate(shared_args)
                         if value in ('--bind', '--ro-bind')]
for name in runtime.SHARED_DATA:
    assert '/storage/' + name in shared_args

with tempfile.TemporaryDirectory() as directory:
    home = Path(directory) / "home"
    home.mkdir()
    (home / "personal").write_text("preserve")
    (home / "outside-link").symlink_to("/storage/roms")
    with patch.object(runtime.os, "chown") as chown:
        runtime.migrate_home(home)
        assert chown.call_count == 3
        assert all(call.kwargs == {"follow_symlinks": False} for call in chown.call_args_list)
    os.link(home / "personal", Path(directory) / "outside-hardlink")
    with patch.object(runtime.os, "chown") as chown:
        try:
            runtime.migrate_home(home)
            raise AssertionError("external hardlink accepted")
        except RuntimeError:
            pass
        chown.assert_not_called()
print("PASS: bubblewrap identity, environment, mount policy and bounded home migration")

# Exercise failures before the graphical access journal exists. Never perform
# real mounts, privilege changes, signal changes or host lock operations here.
for failure in ("bind", "remount", "home"):
    with tempfile.TemporaryDirectory() as directory, ExitStack() as mocks:
        root = Path(directory) / "rootfs"
        (root / "etc").mkdir(parents=True)
        (root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/sh\n")
        (root / "usr/bin").mkdir(parents=True)
        for executable in ("bwrap", "dbus-run-session"):
            (root / "usr/bin" / executable).touch()
        work = Path(directory) / "rocknix-bwrap-test"
        calls = []
        def run(args, **kwargs):
            calls.append(args)
            if ((failure == "bind" and args[:2] == ["mount", "--bind"])
                    or (failure == "remount" and "remount,bind,ro" in args)):
                raise subprocess.CalledProcessError(1, args)
        mocks.enter_context(patch("sys.argv", [str(path), "--rootfs", str(root),
                                                "--desktop", "--", "/bin/true"]))
        mocks.enter_context(patch.object(runtime.os, "geteuid", return_value=0))
        real_open = os.open
        def open_file(name, *args, **kwargs):
            if name == "/run/rocknix-bwrap.lock":
                return 99
            return real_open(name, *args, **kwargs)
        mocks.enter_context(patch.object(runtime.os, "open", side_effect=open_file))
        mocks.enter_context(patch.object(runtime.fcntl, "flock"))
        mocks.enter_context(patch.object(runtime.pwd, "getpwuid", side_effect=KeyError))
        mocks.enter_context(patch.object(runtime.os, "unshare", create=True))
        mocks.enter_context(patch.object(runtime.os, "CLONE_NEWNS", 0, create=True))
        mocks.enter_context(patch.object(runtime.os, "chown"))
        mocks.enter_context(patch.object(runtime.signal, "signal"))
        mocks.enter_context(patch.object(runtime, "STATE", Path(directory) / "state"))
        mocks.enter_context(patch.object(runtime, "WORK_ROOT", Path(directory)))
        mocks.enter_context(patch.object(runtime.uuid, "uuid4", return_value=SimpleNamespace(hex="test")))
        mocks.enter_context(patch.object(runtime.tempfile, "mkdtemp", return_value=str(work)))
        mocks.enter_context(patch.object(runtime, "restore_access"))
        mocks.enter_context(patch.object(runtime, "migrate_home", side_effect=RuntimeError("home failure")))
        mocks.enter_context(patch.object(runtime.subprocess, "run", side_effect=run))
        try:
            runtime.main()
        except (subprocess.CalledProcessError, RuntimeError):
            pass
        else:
            raise AssertionError(f"{failure} failure was not injected")
        assert not work.exists(), (failure, calls)
        unmounts = [args for args in calls if args[0] == "umount"]
        assert unmounts == ([] if failure == "bind" else [["umount", str(work / "rootfs")]])
print("PASS: root bind, read-only remount and home setup failure cleanup")

with tempfile.TemporaryDirectory() as directory:
    state = Path(directory) / 'state'
    state.mkdir(mode=0o700)
    work = Path(directory) / 'rocknix-bwrap-test'
    work.mkdir()
    (work / 'rootfs').mkdir()
    (state / 'setup.json').write_text(runtime.json.dumps({'work': str(work)}))
    real_stat = Path.stat
    def root_stat(path, *args, **kwargs):
        fields = list(real_stat(path, *args, **kwargs))
        fields[4] = 0  # fixture represents a root-owned journal/runtime
        return os.stat_result(fields)
    with patch.object(runtime, 'STATE', state), patch.object(runtime, 'WORK_ROOT', Path(directory)), patch.object(Path, 'stat', root_stat):
        # A visible mounted-data lookalike must fail closed, preserving journal.
        (work / 'rootfs' / 'keep').touch()
        try:
            runtime.restore_access(Path('/unused'), cleanup_orphan=True)
        except RuntimeError:
            pass
        else:
            raise AssertionError('nonempty orphan rootfs accepted')
        assert (state / 'setup.json').exists() and (work / 'rootfs/keep').exists()
        (work / 'rootfs/keep').unlink()
        runtime.restore_access(Path('/unused'), cleanup_orphan=True)
        assert not state.exists() and not work.exists()
print('PASS: pre-display journal recovery removes only safe empty mountpoints')
