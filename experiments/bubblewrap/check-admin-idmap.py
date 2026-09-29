#!/usr/bin/python3
"""RP6 namespace-root ownership probe; never writes the installed Debian rootfs.

Run as host root. Uses a private mount namespace and disposable storage fixture.
This is an experiment, not an application-install endpoint.
"""
import os
from pathlib import Path
import pwd
import grp
import shutil
import subprocess
import tempfile

BASE_UID = 200000
COUNT = 65536
ROOT = Path('/storage/.local/share/rocknix-xfce/rootfs')


def main():
    assert os.geteuid() == 0
    assert not any(BASE_UID <= p.pw_uid < BASE_UID + COUNT for p in pwd.getpwall())
    assert not any(BASE_UID <= g.gr_gid < BASE_UID + COUNT for g in grp.getgrall())
    os.unshare(os.CLONE_NEWNS)
    subprocess.run(['mount', '--make-rprivate', '/'], check=True)
    base = Path(tempfile.mkdtemp(prefix='.admin-idmap-probe-', dir='/storage/rocknix-desktop'))
    base.chmod(0o755)
    source, mapped, runtime = (base / name for name in ('source', 'mapped', 'runtime'))
    for path in (source, mapped, runtime):
        path.mkdir(mode=0o755)
    package = source / 'package-source'
    (package / 'DEBIAN').mkdir(parents=True)
    (package / 'usr/share/rocknix-admin-probe').mkdir(parents=True)
    (package / 'DEBIAN/control').write_text(
        'Package: rocknix-admin-probe\nVersion: 1.0\nArchitecture: all\n'
        'Maintainer: ROCKNIX Desktop test <test@example.invalid>\n'
        'Description: Disposable namespace-root package transaction fixture\n')
    (package / 'usr/share/rocknix-admin-probe/data').write_text('package payload\n')
    postinst = package / 'DEBIAN/postinst'
    postinst.write_text('#!/bin/sh\nset -eu\n'
                       'test "$(id -u)" = 0\n'
                       'test "$DPKG_ROOT" = /tmp/admin-fixture/install\n'
                       'chown 101:102 "$DPKG_ROOT/usr/share/rocknix-admin-probe/data"\n'
                       'printf "configured\\n" > "$DPKG_ROOT/maintainer-script-ran"\n')
    postinst.chmod(0o755)
    mounts = []
    child = None
    try:
        lib = ROOT / 'usr/lib/aarch64-linux-gnu'
        mount = [str(lib / 'ld-linux-aarch64.so.1'), '--library-path', str(lib),
                 str(ROOT / 'usr/bin/mount')]
        subprocess.run(mount + ['--bind', '-o', f'X-mount.idmap=b:0:{BASE_UID}:{COUNT}',
                                str(source), str(mapped)], check=True)
        mounts.append(mapped)
        subprocess.run(['mount', '--bind', str(ROOT), str(runtime)], check=True)
        mounts.append(runtime)
        subprocess.run(['mount', '-o', 'remount,bind,ro', str(runtime)], check=True)
        ready_r, ready_w = os.pipe()
        go_r, go_w = os.pipe()
        child = os.fork()
        if child == 0:
            try:
                os.close(ready_r)
                os.close(go_w)
                os.setgroups([])
                os.unshare(os.CLONE_NEWUSER)
                os.write(ready_w, b'R')
                assert os.read(go_r, 1) == b'G'
                os.setresgid(0, 0, 0)
                os.setresuid(0, 0, 0)
                os.write(ready_w, b'I')
                assert os.read(go_r, 1) == b'G'
                lib = runtime / 'usr/lib/aarch64-linux-gnu'
                args = [str(lib / 'ld-linux-aarch64.so.1'), '--library-path', str(lib),
                        str(runtime / 'usr/bin/bwrap'), '--unshare-pid', '--unshare-ipc',
                        '--unshare-uts', '--unshare-net', '--die-with-parent', '--new-session',
                        '--ro-bind', str(runtime), '/', '--proc', '/proc', '--dev', '/dev',
                        '--tmpfs', '/tmp', '--tmpfs', '/run', '--tmpfs', '/home',
                        '--tmpfs', '/root', '--tmpfs', '/storage', '--tmpfs', '/sys',
                        '--bind', str(mapped), '/tmp/admin-fixture', '--cap-drop', 'ALL',
                        '--cap-add', 'CAP_CHOWN', '--cap-add', 'CAP_FOWNER',
                        '--cap-add', 'CAP_FSETID',
                        '--clearenv', '--setenv', 'PATH', '/usr/sbin:/usr/bin:/sbin:/bin', '--chdir', '/',
                        '--', '/bin/sh', '-eu', '-c', '''
test "$(id -u)" = 0
test ! -e /storage/roms
test ! -e /run/dbus/system_bus_socket
test ! -e /dev/dri
! touch /etc/rocknix-admin-probe
touch /tmp/admin-fixture/package-file
chown 101:102 /tmp/admin-fixture/package-file
test "$(stat -c %u:%g /tmp/admin-fixture/package-file)" = 101:102
touch /tmp/admin-fixture/root-file
test "$(stat -c %u:%g /tmp/admin-fixture/root-file)" = 0:0
cat /proc/self/uid_map
grep '^NoNewPrivs:' /proc/self/status
dpkg-deb --build /tmp/admin-fixture/package-source /tmp/admin-fixture/probe.deb
mkdir /tmp/admin-fixture/install
dpkg --root=/tmp/admin-fixture/install --log=/tmp/admin-fixture/dpkg.log \
    --force-script-chrootless --install /tmp/admin-fixture/probe.deb
test "$(cat /tmp/admin-fixture/install/maintainer-script-ran)" = configured
test "$(stat -c %u:%g /tmp/admin-fixture/install/usr/share/rocknix-admin-probe/data)" = 101:102
test "$(dpkg-query --admindir=/tmp/admin-fixture/install/var/lib/dpkg \
    -W -f='${Status}' rocknix-admin-probe)" = 'install ok installed'
# Leave a copy of the installed file for host-side ownership verification.
cp -p /tmp/admin-fixture/install/usr/share/rocknix-admin-probe/data /tmp/admin-fixture/installed-proof
dpkg --root=/tmp/admin-fixture/install --log=/tmp/admin-fixture/dpkg.log \
    --force-script-chrootless --purge rocknix-admin-probe
test ! -e /tmp/admin-fixture/install/usr/share/rocknix-admin-probe/data
echo 'PASS: dpkg install, maintainer script, service ownership and purge'
''']
                os.execve(args[0], args, {'PATH': '/usr/bin:/bin'})
            except BaseException:
                import traceback
                traceback.print_exc()
                os._exit(1)
        os.close(ready_w)
        os.close(go_r)
        assert os.read(ready_r, 1) == b'R'
        proc = Path('/proc') / str(child)
        (proc / 'uid_map').write_text(f'0 {BASE_UID} {COUNT}\n')
        (proc / 'gid_map').write_text(f'0 {BASE_UID} {COUNT}\n')
        os.write(go_w, b'G')
        assert os.read(ready_r, 1) == b'I'
        status = dict(line.split(':', 1) for line in (proc / 'status').read_text().splitlines())
        assert status['Uid'].split() == [str(BASE_UID)] * 4
        assert status['Gid'].split() == [str(BASE_UID)] * 4
        print(f'Host observes administrator UID/GID {BASE_UID}, not root', flush=True)
        os.write(go_w, b'G')
        _, result = os.waitpid(child, 0)
        child = None
        assert result == 0, result
        assert (source / 'package-file').stat().st_uid == 101
        assert (source / 'package-file').stat().st_gid == 102
        assert (source / 'root-file').stat().st_uid == 0
        assert (source / 'installed-proof').stat().st_uid == 101
        assert (source / 'installed-proof').stat().st_gid == 102
        print('PASS: namespace root preserves Debian root/service ownership through idmap', flush=True)
    finally:
        if child is not None:
            os.kill(child, 9)
            os.waitpid(child, 0)
        for target in reversed(mounts):
            subprocess.run(['umount', str(target)], check=True)
        shutil.rmtree(base)


if __name__ == '__main__':
    main()
