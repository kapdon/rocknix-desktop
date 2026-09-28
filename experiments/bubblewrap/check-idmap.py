#!/usr/bin/python3
"""RP6 bounded idmapped-mount check. Removes only its own temporary data."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path('/storage/.local/share/rocknix-xfce/rootfs')
lib = root / 'usr/lib/aarch64-linux-gnu'
mount = [str(lib / 'ld-linux-aarch64.so.1'), '--library-path', str(lib),
         str(root / 'usr/bin/mount')]
os.unshare(os.CLONE_NEWNS)
subprocess.run(['mount', '--make-rprivate', '/'], check=True)
base = Path(tempfile.mkdtemp(prefix='.bwrap-idmap-test-', dir='/storage/rocknix-desktop'))
os.chmod(base, 0o755)
source = base / 'source'
target = base / 'target'
source.mkdir(mode=0o755)
target.mkdir(mode=0o755)
(source / 'existing').write_text('original')
mounted = False
try:
    subprocess.run(mount + ['--bind', '-o', 'X-mount.idmap=b:0:62000:1',
                           str(source), str(target)], check=True)
    mounted = True
    print('source UID:', (source / 'existing').stat().st_uid, flush=True)
    print('mapped UID:', (target / 'existing').stat().st_uid, flush=True)
    assert (target / 'existing').stat().st_uid == 62000
    pid = os.fork()
    if pid == 0:
        os.setgroups([])
        os.setgid(62000)
        os.setuid(62000)
        (target / 'existing').write_text('edited')
        (target / 'new').write_text('created non-root')
        os._exit(0)
    assert os.waitpid(pid, 0)[1] == 0
    assert (source / 'new').stat().st_uid == 0
    assert (source / 'existing').read_text() == 'edited'
    assert (source / 'existing').stat().st_uid == 0
    print('PASS: non-root edits and creates; host ownership stays root', flush=True)
finally:
    if mounted:
        subprocess.run(['umount', str(target)], check=True)
    shutil.rmtree(base)
