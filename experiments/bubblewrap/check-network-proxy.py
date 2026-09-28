#!/usr/bin/python3
"""Bounded RP6 probe: non-root NetworkManager access, no host bus mutations."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

loader = importlib.machinery.SourceFileLoader('runtime', '/storage/.local/share/rocknix-xfce/bin/rocknix-bwrap')
spec = importlib.util.spec_from_loader(loader.name, loader)
runtime = importlib.util.module_from_spec(spec)
loader.exec_module(runtime)
os.unshare(os.CLONE_NEWNS)
subprocess.run(['mount', '--make-rprivate', '/'], check=True)
work = Path(tempfile.mkdtemp(prefix='rocknix-network-probe-', dir='/run'))
work.chmod(0o755)
root = work / 'rootfs'
root.mkdir()
subprocess.run(['mount', '--bind', runtime.DEFAULT_ROOT, str(root)], check=True)
subprocess.run(['mount', '-o', 'remount,bind,ro', str(root)], check=True)
endpoint = work / 'proxy'
endpoint.mkdir(mode=0o700)
os.chown(endpoint, runtime.PROBE_UID, runtime.PROBE_UID)
parent, child = socket.socketpair()
proxy = None
try:
    proxy = subprocess.Popen(runtime.debian_command(root, '/usr/bin/xdg-dbus-proxy',
        f'--fd={child.fileno()}', 'unix:path=/run/dbus/system_bus_socket', str(endpoint / 'bus'),
        '--filter', '--talk=org.freedesktop.NetworkManager'), pass_fds=(child.fileno(),),
        preexec_fn=runtime.drop_privileges)
    child.close()
    parent.settimeout(5)
    assert parent.recv(1), 'proxy closed before readiness'
    def call(destination, path, method):
        return subprocess.run(runtime.debian_command(root, '/usr/bin/dbus-send',
            '--bus=unix:path=' + str(endpoint / 'bus'), '--print-reply', '--dest=' + destination,
            path, method), preexec_fn=runtime.drop_privileges,
            text=True, capture_output=True, timeout=10)
    permissions = call('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager',
                       'org.freedesktop.NetworkManager.GetPermissions')
    print('NetworkManager permissions:', permissions.returncode, permissions.stdout, permissions.stderr)
    if permissions.returncode != 0:
        # Separate proxy filtering from host authentication/account lookup.
        for uid in (runtime.PROBE_UID, 65534):
            def drop(uid=uid):
                os.setgroups([])
                os.setgid(uid)
                os.setuid(uid)
            direct = subprocess.run(runtime.debian_command(root, '/usr/bin/dbus-send',
                '--system', '--print-reply', '--dest=org.freedesktop.NetworkManager',
                '/org/freedesktop/NetworkManager', 'org.freedesktop.NetworkManager.GetPermissions'),
                preexec_fn=drop, capture_output=True, text=True, timeout=10)
            print('Direct host bus UID', uid, ':', direct.returncode, direct.stdout, direct.stderr)
        raise RuntimeError('non-root proxy access failed; diagnostic only, not parity')
    blocked = call('org.freedesktop.systemd1', '/org/freedesktop/systemd1',
                   'org.freedesktop.DBus.Peer.Ping')
    print('systemd denied:', blocked.returncode, blocked.stderr)
    assert blocked.returncode != 0
    print('PASS: non-root filtered NetworkManager access; systemd not reachable')
finally:
    parent.close()
    child.close()
    if proxy is not None:
        try:
            proxy.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proxy.kill()
            proxy.wait()
    subprocess.run(['umount', str(root)], check=True)
    shutil.rmtree(work)
