#!/usr/bin/env python3
"""Read installed placement and test a bounded 16-task guest child service.

Does not lower the Desktop/host limits or exhaust the complete container.
"""
import json
import os
from pathlib import Path
import runpy
import subprocess
import uuid

base = Path('/storage/rocknix-desktop/managed/host')
layout = runpy.run_path(str(base / 'bin/rocknix-lxc-upgrade'))
layout['configure_layout']()
paths = layout['configure_layout'].__globals__
base, rootfs = paths['BASE'], paths['ROOTFS']
api = runpy.run_path(str(base / 'bin/rocknix-lxc'))
runtime = api['Runtime'](base / 'host-tools', rootfs)
scope = Path('/sys/fs/cgroup/unified/rocknix-lxc')
pids = Path('/sys/fs/cgroup/pids/system.slice/rocknix-desktop.service/lxc.payload.rocknix-lxc')
assert (scope / 'memory.max').read_text().strip() == '4294967296'
assert (scope / 'memory.swap.max').read_text().strip() == '0'
assert (pids / 'pids.max').read_text().strip() == '1536'
assert (pids / 'system.slice/rocknix-desktop-session.service/pids.max').read_text().strip() == '1024'
checked = []
for process in Path('/proc').iterdir():
    if not process.name.isdecimal():
        continue
    try:
        uid = int(next(line for line in (process / 'status').read_text().splitlines()
                       if line.startswith('Uid:')).split()[1])
        if not 200000 <= uid < 265536:
            continue
        groups = (process / 'cgroup').read_text().splitlines()
        memory = next(line.split(':', 2)[2] for line in groups if line.startswith('0::'))
        tasks = next(line.split(':', 2)[2] for line in groups
                     if 'pids' in line.split(':', 2)[1].split(','))
        assert memory.startswith('/rocknix-lxc/lxc.payload.rocknix-lxc/'), (process, memory)
        assert tasks.startswith('/system.slice/rocknix-desktop.service/lxc.payload.rocknix-lxc/'), (process, tasks)
        checked.append(int(process.name))
    except (FileNotFoundError, ProcessLookupError):
        pass
assert checked
# Check the host-owned outer memory ceiling using both mapped identities. Open
# only: never write or truncate a cgroup control file, even on unexpected access.
for uid in (200000, 201000):
    probe = subprocess.run(['/usr/bin/python3', '-c', r'''
import errno, json, os, sys
uid = int(sys.argv[1])
os.setgroups([])
os.setgid(uid)
os.setuid(uid)
for path in sys.argv[2:]:
    try:
        fd = os.open(path, os.O_WRONLY)
    except OSError as error:
        assert error.errno in (errno.EROFS, errno.EACCES, errno.EPERM), error
    else:
        os.close(fd)
        raise RuntimeError('mapped identity can open outer memory control for write')
print(json.dumps({'mapped_uid': uid, 'outer_memory_controls_write_denied': True}))
''', str(uid), str(scope / 'memory.max'), str(scope / 'memory.swap.max')],
        text=True, capture_output=True, timeout=10)
    print(probe.stdout, probe.stderr, flush=True)
    assert probe.returncode == 0
boundary = runtime.attach('/usr/bin/python3', '-c', r'''
import errno, json, os
from pathlib import Path
assert os.getuid() == 0
assert Path('/proc/self/uid_map').read_text().split() == ['0', '200000', '65536']
path = '/sys/fs/cgroup/pids/pids.max'
assert Path(path).read_text().strip() == '1536'
try:
    fd = os.open(path, os.O_WRONLY)
except OSError as error:
    assert error.errno in (errno.EROFS, errno.EACCES, errno.EPERM), error
    print(json.dumps({'container_root_cannot_open_outer_pid_limit_for_write': True,
                      'errno': error.errno}))
else:
    os.close(fd)
    raise RuntimeError('Container root can open outer PID ceiling for write')
''')
print(boundary.stdout, boundary.stderr, flush=True)
assert boundary.returncode == 0
probe = r'''
import errno, json, os, signal, time
assert os.getuid() == 1000
children = []
limited = False
try:
    for _ in range(24):
        try:
            pid = os.fork()
        except OSError as error:
            assert error.errno == errno.EAGAIN, error
            limited = True
            break
        if pid == 0:
            time.sleep(10)
            os._exit(0)
        children.append(pid)
    assert limited and len(children) == 15, (limited, len(children))
    print(json.dumps({'guest_uid': os.getuid(), 'child_tasks': len(children),
                      'fork_denied_EAGAIN': limited}), flush=True)
finally:
    for pid in children:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for pid in children:
        os.waitpid(pid, 0)
'''
unit = 'rocknix-limit-probe-' + uuid.uuid4().hex[:12]
result = runtime.attach('/usr/bin/systemd-run', '--quiet', '--wait', '--pipe', '--collect',
    '--unit=' + unit, '-p', 'User=rocknix', '-p', 'TasksMax=16', '-p', 'RuntimeMaxSec=20',
    '/usr/bin/python3', '-c', probe, timeout=30)
print(result.stdout, result.stderr, flush=True)
assert result.returncode == 0
check = runtime.attach('/bin/systemctl', 'is-active', 'rocknix-desktop-session.service')
assert check.returncode == 0, check.stdout
assert not (pids / ('system.slice/' + unit + '.service')).exists()
print(json.dumps({'mapped_processes_verified': len(checked), 'memory_max': 4294967296,
                  'swap_max': 0, 'container_tasks_max': 1536, 'desktop_tasks_max': 1024,
                  'bounded_child_exhaustion_passed': True, 'desktop_still_active': True}), flush=True)
