#!/usr/bin/python3
"""Bounded RP6 network editor prototype, without host account or ACL changes.

Closes the test editor after 90 seconds. Do not edit the active network during
this experiment. This is not wired into Desktop Mode yet.
"""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import pwd
import shutil
import signal
import socket
import subprocess
import tempfile

loader = importlib.machinery.SourceFileLoader('runtime', '/storage/.local/share/rocknix-xfce/bin/rocknix-bwrap')
spec = importlib.util.spec_from_loader(loader.name, loader)
runtime = importlib.util.module_from_spec(spec)
loader.exec_module(runtime)
assert pwd.getpwuid(65534).pw_name == 'nobody'
runtime.PROBE_UID = 65534
os.unshare(os.CLONE_NEWNS)
subprocess.run(['mount', '--make-rprivate', '/'], check=True)
work = Path(tempfile.mkdtemp(prefix='rocknix-network-editor-', dir='/run'))
work.chmod(0o755)
root = work / 'rootfs'
root.mkdir()
subprocess.run(['mount', '--bind', runtime.DEFAULT_ROOT, str(root)], check=True)
subprocess.run(['mount', '-o', 'remount,bind,ro', str(root)], check=True)
proxy = editor = None
wayland = socket.socket(socket.AF_UNIX)
parent, child = socket.socketpair()
try:
    for name in ('home', 'runtime', 'proxy'):
        (work / name).mkdir(mode=0o700)
        os.chown(work / name, 65534, 65534)
    (work / 'passwd').write_text('root:x:0:0:root:/root:/bin/sh\nrocknix:x:65534:65534:Network settings:/home/rocknix:/bin/sh\n')
    (work / 'group').write_text('root:x:0:\nrocknix:x:65534:\n')
    for name in ('passwd', 'group'):
        (work / name).chmod(0o644)
    proxy = subprocess.Popen(runtime.debian_command(root, '/usr/bin/xdg-dbus-proxy',
        f'--fd={child.fileno()}', 'unix:path=/run/dbus/system_bus_socket', str(work / 'proxy/bus'),
        '--filter', '--talk=org.freedesktop.NetworkManager'), pass_fds=(child.fileno(),),
        preexec_fn=runtime.drop_privileges)
    child.close()
    parent.settimeout(5)
    assert parent.recv(1), 'proxy exited before readiness'
    # Supply one already-connected Wayland fd. No general host socket mount,
    # no temporary ACL grant to the shared nobody identity, no host Sway IPC.
    wayland.connect('/var/run/0-runtime-dir/wayland-1')
    args = runtime.sandbox_command(root, work, ['/usr/bin/nm-connection-editor'])
    separator = args.index('--')
    args[separator:separator] = [
        '--ro-bind', str(work / 'proxy/bus'), '/run/network-bus',
        '--setenv', 'DBUS_SYSTEM_BUS_ADDRESS', 'unix:path=/run/network-bus',
        '--setenv', 'WAYLAND_SOCKET', str(wayland.fileno()), '--setenv', 'GDK_BACKEND', 'wayland',
        '--setenv', 'NO_AT_BRIDGE', '1',
    ]
    editor = subprocess.Popen(args, pass_fds=(wayland.fileno(),), preexec_fn=runtime.drop_privileges,
                              env={'PATH': '/usr/bin:/bin'}, start_new_session=True)
    print(f'Editor bubblewrap host PID {editor.pid}; proxy PID {proxy.pid}', flush=True)
    try:
        result = editor.wait(timeout=90)
        print('Editor exit:', result, flush=True)
        if result != 0:
            raise RuntimeError(f'network editor failed: {result}')
    except subprocess.TimeoutExpired:
        print('Bounded editor test ended', flush=True)
finally:
    if editor is not None and editor.poll() is None:
        os.killpg(editor.pid, signal.SIGKILL)
        editor.wait()
    wayland.close()
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
