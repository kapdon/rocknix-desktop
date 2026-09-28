#!/usr/bin/python3
"""Exercise the real packager with a tiny Docker-export fixture, without Docker."""
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="rocknix-package-test-") as temp:
    work = Path(temp)
    export = work / "export.tar"
    with tarfile.open(export, "w") as archive:
        def add(name, data=b"", mode=0o755, uid=0, gid=0, directory=False):
            item = tarfile.TarInfo(name)
            item.uid, item.gid, item.mode = uid, gid, mode
            item.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
            item.size = 0 if directory else len(data)
            archive.addfile(item, None if directory else io.BytesIO(data))
        for directory in ("dev", "proc", "run", "sys", "tmp", "etc", "var/lib/service"):
            add(directory, directory=True, uid=101 if directory == "var/lib/service" else 0)
        required = "bwrap setfacl mount dbus-run-session firefox-esr foot fuzzel glmark2-wayland waybar".split()
        for name in required:
            add("usr/bin/" + name, b"fixture")
        for name in "wvkbd-rocknix rocknix-launcher rocknix-status rocknix-window-switcher rocknix-sway-session".split():
            add("usr/local/bin/" + name, b"fixture")
        add("opt/ffmpeg-rpi-7.1.5/bin/ffmpeg", b"fixture")
        add("etc/rocknix-xfce-release", b"ROCKNIX_SWAY_RUNTIME=1\n", 0o644)
        add("usr/bin/setuid-fixture", b"fixture", 0o4755)
        add("var/lib/service/data", b"service", 0o640, 101, 102)
    mock = work / "bin"
    mock.mkdir()
    docker = mock / "docker"
    docker.write_text('#!/bin/sh\n[ "$1" = export ] || exit 1\nexec cat "$EXPORT_FIXTURE"\n')
    docker.chmod(0o755)
    stage = work / "stage"
    (stage / "rootfs").mkdir(parents=True)
    output = work / "bundle.tar.xz"
    env = dict(os.environ, PATH=str(mock) + ":" + os.environ["PATH"], EXPORT_FIXTURE=str(export))
    subprocess.run(["fakeroot", "--", "bash", str(PROJECT / "scripts/package-rootfs.sh"),
                    "fixture", str(PROJECT), str(stage), "sha256:fixture", "test-revision", str(output)],
                   env=env, check=True)
    with tarfile.open(output) as archive:
        def metadata(name):
            item = archive.getmember("./" + name)
            return item.uid, item.gid, item.mode
        assert metadata("rootfs/usr/bin/setuid-fixture") == (0, 0, 0o4755)
        assert metadata("rootfs/var/lib/service/data") == (101, 102, 0o640)
        assert metadata("rootfs/tmp") == (0, 0, 0o1777)
        for name in ("payload/bin/rocknix-bwrap", "install-device.sh", "build-info", "rootfs/etc/rocknix-xfce-build-info"):
            assert metadata(name)[:2] == (0, 0), name
print("PASS: package preserves service ownership and setuid modes; host payload is root-owned")
