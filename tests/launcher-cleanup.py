#!/usr/bin/env python3
"""Run actual launcher cleanup after its process-substitution logger exits."""
from pathlib import Path
import subprocess

source = (Path(__file__).resolve().parents[1] / 'payload/bin/launch-sway-desktop').read_text()
cleanup = source[source.index('cleanup() {'):source.index('trap cleanup EXIT')]
for code, ignore_pipe in ((code, ignored) for code in (0, 1, 130, 143) for ignored in (False, True)):
    script = ("trap '' PIPE\n" if ignore_pipe else '') + r'''
set -Eeuo pipefail
HOST_CONTROL_PID='' WINDOW_WATCH_PID='' NETWORK_WATCH_PID=''
SWAY_STYLE_MARKER=/nonexistent/rocknix-cleanup-test
BINDING_INSTALLED=0
RUNTIME_DIR=/nonexistent/rocknix-cleanup-test
HOST_CONTROL_FIFO=$RUNTIME_DIR/host-control
CONTROL_FIFO=$RUNTIME_DIR/control
rm() { :; }
rmdir() { :; }
exec {SESSION_STDOUT}>&1 {SESSION_STDERR}>&2
# A service stop kills tee along with the other cgroup members. Reproduce a
# logger that has exited, rather than substituting a healthy output stream.
exec > >(exit 0) 2>&1
wait "$!"
''' + cleanup + '\ntrap cleanup EXIT\nexit ' + str(code)
    result = subprocess.run(['bash', '-c', script], capture_output=True, text=True)
    assert result.returncode == code, (code, result.returncode, result.stdout, result.stderr)
    assert f'session ended with status {code}' in result.stdout
assert source.index('exec {SESSION_STDOUT}>&1 {SESSION_STDERR}>&2') < source.index('exec > >(tee')
print('PASS: terminated logger cannot replace normal, signal or failure exit status')
