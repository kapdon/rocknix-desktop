#!/usr/bin/env python3
"""Offline launch-contract tests; hardware results are documented separately."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import tempfile
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
