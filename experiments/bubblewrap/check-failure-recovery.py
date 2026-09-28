#!/usr/bin/python3
"""RP6 destructive-to-session test: kill one desktop component, verify recovery.

Closes the desktop's applications. Run only on a device reserved for testing.
Restarts Desktop Mode after successful checks; leaves Gaming on test failure.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('component', choices=['wvkbd-rocknix', 'waybar', 'return-ui'])
args = parser.parse_args()

def output(*command):
    return subprocess.check_output(command, text=True).strip()

def active(unit):
    return subprocess.run(['systemctl', 'is-active', '--quiet', unit]).returncode == 0

def desktop_processes():
    found = []
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            status = (path / 'status').read_text()
            uid = next(line for line in status.splitlines() if line.startswith('Uid:')).split()[1]
            if uid == '62000':
                found.append((int(path.name), (path / 'comm').read_text().strip()))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return found

assert active('xfce-desktop.service') and active('sway.service')
pid = None
if args.component != 'return-ui':
    targets = [pid for pid, name in desktop_processes() if name == args.component]
    assert len(targets) == 1, targets
    pid = targets[0]
    assert 'xfce-desktop.service' in Path(f'/proc/{pid}/cgroup').read_text()
sway = output('systemctl', 'show', 'sway.service', '-p', 'MainPID', '--value')
record = json.loads(Path('/run/rocknix-bwrap-state/socket.json').read_text())
started = time.monotonic()
if args.component == 'return-ui':
    # Explicit RP6 1920x1080 fixture, keyboard hidden. Real panel/UI input,
    # never writing directly to the return-control FIFO.
    subprocess.run(['python3', '/tmp/rp6-fresh-qa.py', 'click', '1780', '1040'], check=True)
    subprocess.run(['python3', '/tmp/rp6-fresh-qa.py', 'key', 'KEY_DOWN', 'KEY_ENTER'], check=True)
else:
    os.kill(pid, signal.SIGKILL)
deadline = started + 50
while time.monotonic() < deadline:
    if active('essway.service') and not active('xfce-desktop.service') and not desktop_processes():
        break
    time.sleep(0.25)
else:
    raise RuntimeError('Desktop component failure did not fully restore Gaming within 50s')
assert active('sway.service')
assert output('systemctl', 'show', 'sway.service', '-p', 'MainPID', '--value') == sway
assert not Path('/run/rocknix-bwrap-state').exists()
assert not Path(record['work']).exists()
root = Path('/storage/.local/share/rocknix-xfce/rootfs')
lib = root / 'usr/lib/aarch64-linux-gnu'
acl = subprocess.check_output([str(lib / 'ld-linux-aarch64.so.1'), '--library-path', str(lib),
    str(root / 'usr/bin/getfacl'), '-p', record['path']], text=True)
assert acl == record['acl'], (acl, record['acl'])
for grant in record.get('devices', []):
    actual = subprocess.check_output([str(lib / 'ld-linux-aarch64.so.1'), '--library-path', str(lib),
        str(root / 'usr/bin/getfacl'), '-p', grant['path']], text=True)
    assert actual == grant['acl'], (actual, grant['acl'])
print(json.dumps({'component': args.component, 'killed_pid': pid,
                  'gaming_recovered_seconds': round(time.monotonic() - started, 2),
                  'sway_pid_unchanged': sway, 'apps_remaining': desktop_processes(),
                  'acl_restored': True, 'runtime_removed': True}), flush=True)
if subprocess.run(['systemctl', 'is-failed', '--quiet', 'xfce-desktop.service']).returncode == 0:
    subprocess.run(['systemctl', 'reset-failed', 'xfce-desktop.service'], check=True)
subprocess.run(['systemctl', 'start', 'xfce-desktop.service'], check=True)
deadline = time.monotonic() + 20
while time.monotonic() < deadline:
    names = [name for _, name in desktop_processes()]
    if active('xfce-desktop.service') and 'waybar' in names and 'wvkbd-rocknix' in names:
        print('PASS: Desktop reopened with non-root panel and keyboard', flush=True)
        break
    time.sleep(0.25)
else:
    raise RuntimeError('Desktop restart did not become ready')
