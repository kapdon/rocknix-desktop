#!/usr/bin/python3
"""Exercise a built gamescopereaper: pass its executable, optionally behind QEMU."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

command = sys.argv[1:]
if not command:
    raise SystemExit('usage: gamescope-reaper.py [qemu-aarch64] /path/to/gamescopereaper')
with tempfile.TemporaryDirectory(prefix='reaper-test-') as directory:
    root = Path(directory)
    daemon = root / 'daemon.py'
    daemon.write_text('''import os, signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
open(sys.argv[1], 'w').write(str(os.getpid()))
while True: time.sleep(1)
''')
    app = root / 'app.py'
    app.write_text('''import os, signal, subprocess, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]], start_new_session=True)
while not os.path.exists(sys.argv[2]): time.sleep(.01)
open(sys.argv[3], 'w').write(str(os.getpid()))
if sys.argv[4] != 'exit':
 while True: time.sleep(1)
''')
    shared = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    try:
        for mode in ('exit', 'term', 'respawn-term'):
            marker, ready = root / (mode + '.pid'), root / (mode + '.ready')
            options = ['--respawn'] if mode == 'respawn-term' else []
            started = time.monotonic()
            process = subprocess.Popen([*command, *options, '--', sys.executable,
                str(app), str(daemon), str(marker), str(ready), mode])
            try:
                deadline = time.monotonic() + 10
                while not ready.exists():
                    assert process.poll() is None, f'reaper exited before ready: {process.returncode}'
                    assert time.monotonic() < deadline, 'primary did not become ready'
                    time.sleep(.01)
                if mode != 'exit':
                    process.terminate()
                assert process.wait(timeout=8) == 0
                for path in (marker, ready):
                    pid = int(path.read_text())
                    assert not Path(f'/proc/{pid}').exists(), f'{mode}: child {pid} survived'
                assert shared.poll() is None, 'unrelated process was killed'
                print(f'PASS: {mode}: descendants gone, unrelated process alive, {time.monotonic()-started:.2f}s', flush=True)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                for path in (marker, ready):
                    if path.exists():
                        try: os.kill(int(path.read_text()), signal.SIGKILL)
                        except ProcessLookupError: pass
    finally:
        shared.terminate()
        shared.wait(timeout=5)
