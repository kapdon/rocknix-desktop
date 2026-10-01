#!/usr/bin/python3
"""Offline policy tests, separate from actual RP6 connection-save checks."""
import importlib.machinery
import importlib.util
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'payload/bin/rocknix-network'
loader = importlib.machinery.SourceFileLoader('network', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
network = importlib.util.module_from_spec(spec)
loader.exec_module(network)
runtime = network.load_runtime()
root, work = Path('/private/rootfs'), Path('/private')
proxy = network.proxy_command(runtime, root, work, 8)
editor = network.editor_command(runtime, root, work, 9)
for args in (proxy, editor):
    assert args[args.index('--uid') + 1] == '65534'
    assert '--cap-drop' in args and '--unshare-pid' in args
    assert '--clearenv' in args and '--unshare-user' in args
    assert '/storage/roms' not in args and '/storage/scripts' not in args
    assert '/run/rocknix-desktop' not in args and '/dev/input' not in args
    assert not any('sway-ipc' in arg or 'wayland-1' in arg for arg in args)
assert '--filter' in proxy and '--talk=org.freedesktop.NetworkManager' in proxy
assert '/run/dbus/system_bus_socket' in proxy
assert '/run/dbus/system_bus_socket' not in editor
assert '/run/host-system-bus' not in editor
assert 'unix:path=/run/network-bus' in editor
assert editor[-1] == '/usr/bin/nm-connection-editor'
assert '--setenv' in editor and 'WAYLAND_SOCKET' in editor
# Theme parity is packaged, not achieved by exposing the writable guest home.
project = path.parents[2]
recipe = (project / 'build-support/lxc/Dockerfile.host-tools').read_text()
assert 'fonts-roboto adwaita-icon-theme' in recipe
assert 'COPY rootfs-overlay/etc/gtk-3.0/settings.ini /etc/gtk-3.0/settings.ini' in recipe
assert 'COPY rootfs-overlay/usr/share/themes/ROCKNIX/ /usr/share/themes/ROCKNIX/' in recipe
assert not any('/data/home' in arg or '/data/rootfs' in arg for arg in editor)
assert 'G_RESOURCE_OVERLAYS' not in editor  # Use the standard upstream editor UI.
# Cleanup fails closed around a live mount, never traversing it.
with patch.object(network, 'WORK') as work, patch.object(network.shutil, 'rmtree') as remove:
    work.exists.return_value = True
    work.is_symlink.return_value = False
    work.is_dir.return_value = True
    work.stat.return_value.st_uid = 0
    target = work.__truediv__.return_value
    target.exists.return_value = True
    target.is_symlink.return_value = False
    with patch.object(network.os.path, 'ismount', return_value=True):
        try:
            network.cleanup_work()
            raise AssertionError('live mount accepted')
        except RuntimeError:
            pass
    remove.assert_not_called()
print('PASS: isolated network editor/proxy arguments and fail-closed orphan cleanup')
