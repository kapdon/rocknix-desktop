#!/usr/bin/env python3
"""Bounded installed memory-accounting test, not a full-container OOM test."""
import json
import os
from pathlib import Path
import runpy
import selectors
import subprocess
import time

base = Path('/storage/rocknix-desktop/managed/host')
layout = runpy.run_path(str(base / 'bin/rocknix-lxc-upgrade'))
layout['configure_layout']()
paths = layout['configure_layout'].__globals__
base, rootfs = paths['BASE'], paths['ROOTFS']
runtime = runpy.run_path(str(base / 'bin/rocknix-lxc'))['Runtime'](
    base / 'host-tools', rootfs)
scope = Path('/sys/fs/cgroup/unified/rocknix-lxc')
before = int((scope / 'memory.current').read_text())
events_before = (scope / 'memory.events').read_text()
assert int((scope / 'memory.max').read_text()) == 4 * 1024**3
assert before < 512 * 1024**2, 'Reserve this test for an idle Desktop'
probe = r'''
import os, signal, sys
assert os.getuid() == 1000
signal.alarm(20)
block = bytearray(128 * 1024**2)
for offset in range(0, len(block), 4096):
    block[offset] = 42
print('allocated', flush=True)
assert sys.stdin.readline() == 'release\n'
del block
print('released', flush=True)
'''
command = runtime.command('lxc-attach', '-P', runtime.configs, '-n', runtime.name,
    '--clear-env', '--', '/usr/sbin/runuser', '-u', 'rocknix', '--',
    '/usr/bin/python3', '-c', probe)
process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True)
try:
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    assert selector.select(15), 'Allocation did not report readiness'
    assert process.stdout.readline().strip() == 'allocated'
    selector.close()
    during = int((scope / 'memory.current').read_text())
    assert during - before >= 120 * 1024**2, (before, during)
    stdout, stderr = process.communicate('release\n', timeout=10)
    assert process.returncode == 0 and stdout.strip() == 'released', (stdout, stderr)
    deadline = time.monotonic() + 5
    while True:
        after = int((scope / 'memory.current').read_text())
        if during - after >= 120 * 1024**2 or time.monotonic() >= deadline:
            break
        time.sleep(.1)
    assert during - after >= 120 * 1024**2, (during, after)
    assert (scope / 'memory.events').read_text() == events_before
    result = runtime.attach('/bin/systemctl', 'is-active', 'rocknix-desktop-session.service')
    assert result.returncode == 0
    print(json.dumps({'allocation_bytes': 128 * 1024**2, 'before': before,
                      'during': during, 'after': after, 'memory_events_unchanged': True,
                      'desktop_active': True}), flush=True)
finally:
    if process.poll() is None:
        # Closing stdin releases the guest wait; its own alarm is a second bound.
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        try:
            process.wait(timeout=22)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
