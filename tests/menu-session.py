#!/usr/bin/env python3
"""Real process/pipe ownership tests, without Wayland or an RP6 claim."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

owner = Path('rootfs-overlay/usr/local/bin/rocknix-menu-session').resolve()


def until(check):
    deadline = time.monotonic() + 5
    while not check():
        assert time.monotonic() < deadline, 'menu process transition timed out'
        time.sleep(.01)


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    helper = root / 'rocknix-games'
    helper.write_text('#!/usr/bin/python3\nimport os,time\nfrom pathlib import Path\n'
                      'Path(os.environ["MARKER"]).write_text(str(os.getpid()))\n'
                      'time.sleep(30)\n')
    helper.chmod(0o755)
    parent = root / 'parent.py'
    parent.write_text('import os,subprocess,sys\n'
                      'subprocess.Popen([sys.argv[1], "--launch", sys.argv[2]], '
                      'pass_fds=(int(os.environ["ROCKNIX_MENU_FD"]),))\n')
    owners = []
    try:
        # The initial launcher exits. Its selected menu survives, keeping the
        # owner alive through the handoff without a sleep/grace-period policy.
        for family in ('apps', 'settings'):
            env = dict(os.environ, XDG_RUNTIME_DIR=tmp, MARKER=str(root / family))
            owners.append(subprocess.Popen([str(owner), family, sys.executable,
                                             str(parent), str(owner), str(helper)], env=env))
            until(lambda: (root / family).exists())
            assert owners[-1].poll() is None
        subprocess.run([str(owner), 'apps', '/bin/false'], env=env, check=True)
        assert owners[0].wait(timeout=5) == 0
        assert owners[1].poll() is None, 'Apps dismissal killed Settings'
        subprocess.run([str(owner), 'settings', '/bin/false'], env=env, check=True)
        assert owners[1].wait(timeout=5) == 0
        assert not list((root / 'rocknix-menus').glob('*.sock'))

        # A normal selected application closes ownership and leaves the menu
        # group before exec. Closing/reopening menus cannot kill that app.
        ordinary = root / 'ordinary-app'
        ordinary.write_text(helper.read_text())
        ordinary.chmod(0o755)
        env['MARKER'] = str(root / 'ordinary')
        process = subprocess.Popen([str(owner), 'apps', sys.executable,
                                    str(parent), str(owner), str(ordinary)], env=env)
        owners.append(process)
        until(lambda: (root / 'ordinary').exists())
        assert process.wait(timeout=5) == 0
        pid = int((root / 'ordinary').read_text())
        os.kill(pid, 0)
        assert os.getpgid(pid) == pid
        os.kill(pid, signal.SIGTERM)

        # A fast-failing application may open an error menu immediately. It
        # must not interpret its predecessor's still-closing owner as a toggle.
        error_app = root / 'error-app'
        error_app.write_text('#!/usr/bin/python3\nimport os,sys\n'
                             'os.execv(sys.argv[1], sys.argv[1:])\n')
        error_app.chmod(0o755)
        delayed = root / 'delayed.py'
        delayed.write_text('import os,subprocess,sys,time\n'
                           'subprocess.Popen(sys.argv[1:], pass_fds=(int(os.environ["ROCKNIX_MENU_FD"]),))\n'
                           'time.sleep(.2)\n')
        marker = root / 'error-opened'
        command = [str(owner), 'apps', sys.executable, str(delayed), str(owner),
                   '--launch', str(error_app), str(owner), 'apps', '/usr/bin/touch', str(marker)]
        process = subprocess.Popen(command, env=env)
        owners.append(process)
        assert process.wait(timeout=5) == 0
        until(marker.exists)

        # Unexpected client exit and stale socket recovery leave no stuck owner.
        subprocess.run([str(owner), 'apps', '/bin/true'], env=env, check=True)
        assert not (root / 'rocknix-menus/apps.sock').exists()
    finally:
        for process in owners:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
print('PASS: descendant lifetime, family dismissal, app detachment and crash cleanup')
