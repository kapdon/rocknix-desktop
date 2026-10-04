#!/usr/bin/python3
"""Optional real user-systemd fixture; no compositor, Wine or FEX hardware claim."""
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tempfile
import time
import unittest


class Lifetime(unittest.TestCase):
    def test_detached_children_and_unrelated_process(self):
        runtime = Path(f'/run/user/{os.getuid()}')
        if not (runtime / 'bus').exists():
            self.skipTest('requires a running user systemd manager')
        with tempfile.TemporaryDirectory(prefix='gamescope-lifetime-', dir=runtime) as directory:
            root = Path(directory)
            helper = root / 'session'
            helper.write_text(Path('rootfs-overlay/usr/local/bin/rocknix-gamescope-session').read_text().replace(
                "HELPER = '/usr/local/bin/rocknix-gamescope-session'", f'HELPER = {str(helper)!r}'))
            helper.chmod(0o755)
            api = runpy.run_path(str(helper))
            compositor = root / 'compositor.py'
            compositor.write_text('''import os, resource, signal, subprocess, sys, time
mode, marker = sys.argv[1:3]
app = subprocess.Popen(sys.argv[3:])
if mode == 'crash':
 while not os.path.exists(marker): time.sleep(.01)
 resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
 os.kill(os.getpid(), signal.SIGABRT)
sys.exit(app.wait())
''')
            daemon = root / 'detached.py'
            daemon.write_text('''import os, signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
open(sys.argv[1], 'w').write(str(os.getpid()))
while True: time.sleep(1)
''')
            app = root / 'app.py'
            app.write_text('''import os, subprocess, sys, time
subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]], start_new_session=True)
while not os.path.exists(sys.argv[2]): time.sleep(.01)
if sys.argv[3] == 'crash':
 while True: time.sleep(1)
''')
            # Models a shared provider outside the launch service. It is not FEX.
            unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(90)'])
            try:
                for mode, expected in [('normal', 0), ('crash', 134)]:
                    with self.subTest(mode=mode):
                        marker = root / (mode + '.pid')
                        code = api['launch']([sys.executable, str(compositor), mode, str(marker)],
                            [sys.executable, str(app), str(daemon), str(marker), mode],
                            dict(os.environ, XDG_STATE_HOME=directory))
                        self.assertEqual(code, expected)
                        pid = int(marker.read_text())
                        for _ in range(100):
                            if not Path(f'/proc/{pid}').exists(): break
                            time.sleep(.02)
                        self.assertFalse(Path(f'/proc/{pid}').exists(), f'detached child {pid} survived')
                        self.assertIsNone(unrelated.poll())
                results = [json.loads(p.read_text()) for p in
                    root.glob('rocknix-desktop/gamescope-sessions/*.json')]
                self.assertEqual(len(results), 2)
                self.assertTrue(all(r['cleanup_complete'] and r['service']['ControlGroup'] == '' for r in results))
                normal = next(r for r in results if r['application'] == 0)
                self.assertEqual(normal['service']['Result'], 'timeout')
                crashed = next(r for r in results if r['compositor'] == -signal.SIGABRT)
                self.assertIn(crashed['service']['Result'], ('exit-code', 'timeout'))
            finally:
                unrelated.terminate()
                unrelated.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
