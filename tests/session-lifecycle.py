#!/usr/bin/python3
"""Run the real session shell with isolated paths and long-lived mock clients."""
import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'rootfs-overlay/usr/local/bin/rocknix-sway-session').read_text()

for mode, expected in [('return', 0), ('invalid', 1), ('term', 143), ('waybar', 1)]:
    with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile() as log:
        home = Path(directory) / 'home'
        home.mkdir()
        fifo = Path(directory) / 'control'
        os.mkfifo(fifo)
        # Override only machine-specific paths; execute production lifecycle code.
        script = SOURCE.replace('export HOME=/home/rocknix',
                                f'export HOME={shlex.quote(str(home))}')
        script = script.replace('CONTROL_FIFO=/run/rocknix-xfce/control',
                                f'CONTROL_FIFO={shlex.quote(str(fifo))}')
        script = script.replace('source /usr/local/bin/rocknix-home-integration', ':')
        script = script.replace('refresh_home_integration /home/rocknix-default "$HOME"', ':')
        bar = 'sleep 0.2; return 1' if mode == 'waybar' else 'exec sleep 600'
        mocks = f'waybar() {{ {bar}; }}\nthunar() {{ exec sleep 600; }}\n'
        proc = subprocess.Popen(['bash', '-c', mocks + script],
                                stdout=log, stderr=log, start_new_session=True)
        try:
            if mode in ('return', 'invalid'):
                deadline = time.monotonic() + 3
                while True:
                    try:
                        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise AssertionError('session did not read FIFO')
                        time.sleep(0.02)
                os.write(fd, b'return\n' if mode == 'return' else b'invalid\n')
                os.close(fd)
            elif mode == 'term':
                time.sleep(0.2)
                proc.send_signal(signal.SIGTERM)
            assert proc.wait(timeout=3) == expected, mode
        finally:
            # Model systemd cgroup cleanup, including deliberately lingering apps.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
        print(f'PASS: session {mode} exits without waiting for application children')
