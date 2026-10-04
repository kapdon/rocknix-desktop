#!/usr/bin/python3
"""Exercise real primary/compositor exit paths and transient-service requests."""
import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SOURCE = Path('rootfs-overlay/usr/local/bin/rocknix-gamescope-session')


class Session(unittest.TestCase):
    def test_real_process_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            helper = root / 'helper'
            helper.write_text(SOURCE.read_text().replace("HELPER = '/usr/local/bin/rocknix-gamescope-session'", f'HELPER = {str(helper)!r}'))
            helper.chmod(0o755)
            compositor = root / 'compositor.py'
            compositor.write_text('''import os, resource, signal, subprocess, sys, time
mode = sys.argv[1]
if mode in ('crash', 'clean-close'):
 if mode == 'clean-close': sys.exit(0)

 resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
 os.kill(os.getpid(), signal.SIGABRT)
if mode == 'hang': signal.signal(signal.SIGTERM, signal.SIG_IGN)
code = subprocess.run(sys.argv[2:]).returncode
if mode == 'crash-after-app':
 resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
 os.kill(os.getpid(), signal.SIGABRT)
if mode == 'hang':
 while True: time.sleep(.1)
sys.exit(code)
''')
            for mode, app_code, expected in [('normal',0,0), ('normal',7,7), ('hang',0,0), ('crash',0,134), ('clean-close',0,0), ('crash-after-app',0,134)]:
                with self.subTest(mode=mode, app_code=app_code):
                    (root / 'application.json').unlink(missing_ok=True)
                    result = root / 'result.json'
                    request = root / 'request.json'
                    request.write_text(json.dumps({'prefix':[sys.executable,str(compositor),mode],
                        'command':[sys.executable,'-c',f'raise SystemExit({app_code})'],
                        'env':dict(os.environ), 'cwd':directory, 'result':str(result)}))
                    process = subprocess.run([str(helper),'--session',str(request)], capture_output=True, timeout=10)
                    self.assertEqual(process.returncode, expected, process.stderr.decode())
                    outcome = json.loads(result.read_text())
                    self.assertEqual(outcome['application'], None if mode in ('crash', 'clean-close') else app_code)
                    self.assertEqual(outcome['forced_compositor_stop'], mode == 'hang')
                    if mode in ('crash', 'crash-after-app'):
                        self.assertEqual(outcome['compositor'], -signal.SIGABRT)

    def test_service_preserves_arguments_environment_and_cleans_own_unit(self):
        api = runpy.run_path(str(SOURCE))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bus').touch()
            control = {'XDG_RUNTIME_DIR':directory, 'DBUS_SESSION_BUS_ADDRESS':'unix:path=manager-bus'}
            environment = dict(os.environ, XDG_STATE_HOME=directory, DBUS_SESSION_BUS_ADDRESS='unix:path=desktop-bus')
            command = ['wine','/a game.exe','$LITERAL','%literal']
            recorded = {'application':0, 'compositor':-15, 'signal':0,
                        'compositor_stop_requested':True}
            def start(argv, **kwargs):
                request = json.loads(Path(argv[-1]).read_text())
                self.assertEqual(request['command'], command)
                self.assertEqual(request['env'], environment)
                self.assertEqual(request['cwd'], os.getcwd())
                self.assertEqual(kwargs['env'], control)
                self.assertEqual(Path(argv[-1]).stat().st_mode & 0o777, 0o600)
                Path(request['result']).write_text(json.dumps(recorded))
                return Mock(wait=Mock(return_value=1))
            with patch.dict(api['launch'].__globals__, manager_env=lambda:control), \
                    patch('subprocess.Popen', side_effect=start) as popen, patch('subprocess.run') as run, \
                    patch.dict(api['launch'].__globals__, service_state=lambda *args:{'ActiveState':'failed','ControlGroup':'','Result':'timeout'}):
                self.assertEqual(api['launch'](['gamescope','--'], command, environment), 0)
                argv = popen.call_args.args[0]
                for flag in ['--wait','--pipe','--expand-environment=no',
                             '--property=KillMode=control-group','--property=SendSIGKILL=yes',
                             '--property=TimeoutStopSec=5s']:
                    self.assertIn(flag, argv)
                unit = next(x.split('=',1)[1] for x in argv if x.startswith('--unit='))
                self.assertEqual(run.call_args_list[0].args[0], ['systemctl','--user','stop',unit])
                self.assertFalse(list(root.glob('rocknix-gamescope-*')))
                # Cleanup escalation must never erase a recorded compositor fault.
                recorded['compositor'] = -signal.SIGABRT
                self.assertEqual(api['launch'](['gamescope','--'], command, environment), 134)
                recorded.update(application=None, compositor=0, compositor_stop_requested=False)
                self.assertEqual(api['launch'](['gamescope','--'], command, environment), 0)

    def test_exit_classification_preserves_faults(self):
        classify = runpy.run_path(str(SOURCE))['exit_status']
        for app, compositor, requested, forced, stop, expected in [
                (None, 0, False, False, 0, 0),
                (0, -6, True, False, 0, 134),
                (None, -6, False, False, 0, 134),
                (0, -15, False, False, 0, 143),
                (7, -15, True, False, 0, 7),
                (0, -9, True, False, 0, 137),
                (0, -9, True, True, 0, 0),
                (0, 0, True, False, 15, 143)]:
            with self.subTest(app=app, compositor=compositor, requested=requested, forced=forced):
                self.assertEqual(classify(dict(application=app, compositor=compositor,
                    compositor_stop_requested=requested, forced_compositor_stop=forced,
                    signal=stop)), expected)

    def test_cleanup_requires_an_empty_inactive_service(self):
        api = runpy.run_path(str(SOURCE))
        for output in ('', 'ActiveState=active\nControlGroup=/live\n',
                       'ActiveState=failed\nControlGroup=/leftovers\n'):
            with patch('subprocess.run', return_value=Mock(stdout=output)):
                with self.assertRaisesRegex(RuntimeError, 'could not be confirmed'):
                    api['service_state']('test.service', {})

    def test_missing_manager_fails_before_launch(self):
        api = runpy.run_path(str(SOURCE))
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(api['launch'].__globals__, manager_env=lambda:{'XDG_RUNTIME_DIR':directory}), \
                patch('subprocess.Popen') as popen:
            with self.assertRaisesRegex(RuntimeError, 'user manager'):
                api['launch'](['gamescope'], ['true'], dict(os.environ))
            popen.assert_not_called()


if __name__ == '__main__': unittest.main()
