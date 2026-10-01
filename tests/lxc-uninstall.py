#!/usr/bin/python3
"""Isolated retained-uninstall transaction tests; run under fakeroot."""
import json
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch

remove = runpy.run_path('payload/bin/rocknix-lxc-uninstall')['remove_integration']
api = runpy.run_path('payload/bin/rocknix-lxc-upgrade')
# Only bypass native-root ancestor checks for the /tmp fixture. Exercise the
# real atomic file replacement, permissions and fsync implementation.
api['atomic'].__globals__['safe_directory'] = lambda path: None
api['safe_directory'] = lambda path: None

for scenario in ('normal', 'interrupted', 'changed', 'symlink', 'customized'):
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        host = base / 'host'
        host.mkdir()
        data = base / 'data'
        (data / 'rootfs').mkdir(parents=True)
        (data / 'home').mkdir()
        app = data / 'rootfs/application'
        app.write_text('installed application')
        profile = data / 'home/profile'
        profile.write_text('personal settings')
        before = [(p.stat().st_ino, p.read_bytes()) for p in (app, profile)]
        targets = {base / 'hook': b'hook', base / 'entry': b'entry', base / 'unit': None}
        for path, content in targets.items():
            path.write_bytes(content or (
                f'ExecStart=/usr/bin/unshare --mount --propagation private -- {host}/bin/launch-sway-desktop\n'
                f'ExecStopPost={host}/bin/restore-emulationstation\n').encode())
        marker = host / 'state/uninstalled.json'
        with patch('subprocess.run'):
            remove(host, targets, api, check=True)
            assert not marker.exists() and all(p.exists() for p in targets)
            if scenario == 'customized':
                (base / 'entry').write_text('personal replacement')
                try:
                    remove(host, targets, api)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('customized entry removed')
                assert not marker.exists() and all(p.exists() for p in targets)
            else:
                if scenario != 'normal':
                    original = Path.unlink
                    def interrupted(path, *args, **kwargs):
                        assert marker.exists(), 'removal began without journal'
                        if path == base / 'entry':
                            raise OSError('simulated interruption')
                        return original(path, *args, **kwargs)
                    with patch.object(Path, 'unlink', interrupted):
                        try:
                            remove(host, targets, api)
                        except OSError:
                            pass
                        else:
                            raise AssertionError('fault not exercised')
                    assert not (base / 'hook').exists()
                    assert json.loads(marker.read_text())['phase'] == 'removing'
                if scenario in ('changed', 'symlink'):
                    (base / 'entry').write_text('changed')
                    if scenario == 'symlink':
                        (base / 'entry').unlink()
                        (base / 'entry').symlink_to(profile)
                    try:
                        remove(host, targets, api)
                    except RuntimeError:
                        pass
                    else:
                        raise AssertionError('changed integration accepted')
                    assert (base / 'unit').exists()
                else:
                    remove(host, targets, api)
                    assert not any(p.exists() for p in targets)
                    assert json.loads(marker.read_text())['phase'] == 'removed'
                    remove(host, targets, api)  # idempotent completed uninstall
        assert before == [(p.stat().st_ino, p.read_bytes()) for p in (app, profile)]
print('PASS: retained uninstall checks, resume, collision refusal and unchanged apps/home')

retained = api['retained_marker']
with tempfile.TemporaryDirectory() as directory:
    host = Path(directory)
    (host / 'state').mkdir()
    marker = host / 'state/uninstalled.json'
    hook, entry, unit = [host / name for name in ('hook', 'entry', 'unit')]
    record = {'format': 1, 'phase': 'removed',
              'files': {str(p): 'a' * 64 for p in (hook, entry, unit)}}
    with patch.dict(retained.__globals__, HOOK=hook, ENTRY=entry, UNIT=unit,
                    GUARD=host / 'upgrade-guard', safe_directory=lambda p: None):
        assert retained(host) is None
        api['atomic'](marker, json.dumps(record).encode(), 0o600)
        assert retained(host) == marker
        for scenario in ('incomplete', 'malformed', 'collision', 'symlink'):
            candidate = dict(record)
            if scenario == 'incomplete':
                candidate['phase'] = 'removing'
            elif scenario == 'malformed':
                candidate['files'] = {}
            elif scenario == 'collision':
                hook.write_text('user replacement')
            else:
                hook.symlink_to(host / 'missing')
            api['atomic'](marker, json.dumps(candidate).encode(), 0o600)
            try:
                retained(host)
            except RuntimeError:
                pass
            else:
                raise AssertionError('unsafe reinstall accepted: ' + scenario)
            hook.unlink(missing_ok=True)
print('PASS: reinstall requires complete uninstall and refuses replacement integration')
