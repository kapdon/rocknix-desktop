#!/usr/bin/python3
"""RP6-only real mount cleanup check, while Desktop is stopped in Gaming.

Usage: check-early-setup.py /tmp/rocknix-bwrap-candidate remount|home
Runs candidate setup with a deliberate failure, without launching applications
or changing the production home. No native config or device ACL is granted.
"""
import importlib.machinery
import importlib.util
from pathlib import Path
import subprocess
import sys

candidate, stage = sys.argv[1:]
assert stage in ('remount', 'home')
def active(unit):
    return subprocess.run(['systemctl', 'is-active', '--quiet', unit]).returncode == 0
assert active('essway.service') and not active('xfce-desktop.service')
assert not Path('/run/rocknix-bwrap-state').exists()
before = set(Path('/run').glob('rocknix-bwrap-*'))
loader = importlib.machinery.SourceFileLoader('candidate_runtime', candidate)
spec = importlib.util.spec_from_loader(loader.name, loader)
runtime = importlib.util.module_from_spec(spec)
loader.exec_module(runtime)
class InjectedFailure(RuntimeError):
    pass
real_run = subprocess.run
def run(args, **kwargs):
    if stage == 'remount' and 'remount,bind,ro' in args:
        raise InjectedFailure('before readonly remount')
    return real_run(args, **kwargs)
def migrate(home):
    raise InjectedFailure('before home migration')
runtime.subprocess.run = run
runtime.migrate_home = migrate
sys.argv = [candidate, '--desktop', '--', '/bin/true']
try:
    runtime.main()
except InjectedFailure:
    pass
else:
    raise AssertionError('expected setup failure was not reached')
assert set(Path('/run').glob('rocknix-bwrap-*')) == before
assert not Path('/run/rocknix-bwrap-state').exists()
assert active('essway.service') and not active('xfce-desktop.service')
print(f'PASS: {stage} failure after real rootfs bind leaves no runtime or ACL journal; Gaming stays active')
