#!/usr/bin/python3
"""Check path assignment without creating or mounting host /storage."""
from pathlib import Path
import os
import subprocess
import tempfile
import fcntl

helper = Path('payload/bin/rocknix-desktop-paths').resolve()
project = '/storage/rocknix-desktop'
host = project + '/managed/host'
script = '''
set -eu
# Substitute only host-location discovery; exercise the shipped assignment and
# rejection logic unchanged. No filesystem mutations and no real /storage.
cd() { :; }
pwd() { printf '%s\\n' "$TEST_HOST_LOCATION"; }
source "$1"
printf '%s\\n' "$BASE" "$ROOTFS" "$HOME_SOURCE" "$LOG_DIR" \
  "$HOST_TOOLS" "$UPGRADE_GUARD"
'''
for location, expected in (
    (host, [host, project+'/data/rootfs', project+'/data/home', project+'/managed/logs',
        host+'/host-tools', host+'/state/upgrade-in-progress.json']),
    ('/tmp/untrusted-install', None)):
    result = subprocess.run(['bash', '-c', script, 'paths-test', str(helper)],
        env={**os.environ, 'TEST_HOST_LOCATION': location}, capture_output=True, text=True)
    if expected is None:
        assert result.returncode != 0 and not result.stdout
    else:
        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == expected, result.stdout

preflight = Path('payload/bin/preflight').read_text()
assert '[ -L "$UPGRADE_GUARD" ]' in preflight
assert "Path(sys.argv[2])" in preflight and "Path(sys.argv[3])" in preflight
for name in ('preflight', 'launch-sway-desktop', 'restore-emulationstation', 'configure-input'):
    source = Path('payload/bin', name).read_text()
    assert '/rocknix-desktop-paths"' in source
print('PASS: canonical host paths, separate persistent data, unsupported location refusal and update guards')

launcher = Path('payload/bin/launch-sway-desktop').read_text()
assert launcher.index('flock -n -s 9') < launcher.index('"${BASE}/bin/preflight"')
with tempfile.TemporaryFile() as lock:
    fcntl.flock(lock, fcntl.LOCK_SH)
    # Open a separate file description; inherited descriptors share the lock.
    path = f'/proc/{os.getpid()}/fd/{lock.fileno()}'
    assert subprocess.run(['flock', '-n', '-x', path, 'true']).returncode != 0
    fcntl.flock(lock, fcntl.LOCK_UN)
    assert subprocess.run(['flock', '-n', '-x', path, 'true']).returncode == 0
print('PASS: launcher lifetime shared lock precedes preflight and excludes maintenance')
