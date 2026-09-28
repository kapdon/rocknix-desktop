#!/usr/bin/python3
"""RP6 test: singleton, live privilege boundary, proxy loss and reopen.

Requires Desktop active, keyboard hidden, no network editor already open, and
the 1920x1080 QA fixture. Makes no NetworkManager configuration changes.
"""
from pathlib import Path
import os
import signal
import subprocess
import time

def active():
    return subprocess.run(['systemctl', 'is-active', '--quiet', 'xfce-desktop.service']).returncode == 0

def clients():
    result = {}
    for item in Path('/proc').iterdir():
        if not item.name.isdecimal():
            continue
        try:
            name = (item / 'comm').read_text().strip()
            if name in ('xdg-dbus-proxy', 'nm-connection-e') and 'xfce-desktop.service' in (item / 'cgroup').read_text():
                result.setdefault(name, []).append(int(item.name))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return result

def qa(*args):
    subprocess.run(['python3', '/tmp/rp6-fresh-qa.py', *args], check=True)

def open_editor():
    qa('click', '1100', '1040')
    qa('key', 'KEY_DOWN', 'KEY_ENTER')
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        found = clients()
        if all(len(found.get(name, [])) == 1 for name in ('xdg-dbus-proxy', 'nm-connection-e')):
            return found
        time.sleep(.2)
    raise RuntimeError(f'network editor did not start: {clients()}')

assert active() and not clients()
first = open_editor()
for name, values in first.items():
    pid = values[0]
    proc = Path(f'/proc/{pid}')
    status = dict(line.split(':', 1) for line in (proc / 'status').read_text().splitlines() if ':' in line)
    assert status['Uid'].split() == ['65534'] * 4
    assert int(status['CapEff'], 16) == 0 and int(status['CapBnd'], 16) == 0
    assert status['NoNewPrivs'].strip() == '1'
    assert os.readlink(proc / 'ns/pid') != os.readlink('/proc/1/ns/pid')
    assert not (proc / 'root/storage/roms').exists()
    assert not (proc / 'root/run/rocknix-xfce').exists()
    if name == 'nm-connection-e':
        assert not (proc / 'root/run/host-system-bus').exists()
        assert not (proc / 'root/run/dbus/system_bus_socket').exists()
    print(f'PASS: {name} PID {pid} non-root, cap-free, private PID namespace', flush=True)
second = open_editor()
assert second == first, (first, second)
print('PASS: repeated Settings action retains exactly one editor/proxy pair', flush=True)
os.kill(first['xdg-dbus-proxy'][0], signal.SIGKILL)
deadline = time.monotonic() + 10
while time.monotonic() < deadline:
    if not clients() and not Path('/run/rocknix-network').exists():
        break
    time.sleep(.2)
else:
    raise RuntimeError('proxy loss left editor or runtime behind')
assert active()
print('PASS: proxy loss closes only network settings and cleans its runtime', flush=True)
open_editor()
qa('key', 'KEY_F15')
deadline = time.monotonic() + 10
while time.monotonic() < deadline:
    if not clients() and not Path('/run/rocknix-network').exists():
        break
    time.sleep(.2)
else:
    raise RuntimeError('R3 close did not clean reopened editor')
assert active()
print('PASS: editor reopened after proxy failure; R3 closed it cleanly', flush=True)
