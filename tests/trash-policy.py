#!/usr/bin/env python3
"""Pure policy tests: no host fstab, package or mount changes."""
from pathlib import Path
import runpy
from types import SimpleNamespace
from unittest.mock import patch

repo = Path(__file__).resolve().parents[1]
api = runpy.run_path(str(repo / 'rootfs-overlay/usr/local/bin/rocknix-trash-policy'))
render = api['render']
shares = set(api['SHARES'])
original = '# personal comment\nUUID=example /data ext4 defaults 0 2\n'
enabled = render(original, shares, True)
assert enabled.startswith(original)
assert enabled.count('x-gvfs-trash ') == 5
assert enabled.count('noauto,x-gvfs-trash ') == 5
auto_mount = enabled.replace('noauto,', '')
assert render(auto_mount, shares, True) == enabled
assert render(auto_mount, set(), False) == original
assert render(enabled, shares, True) == enabled
disabled = render(enabled, shares, False)
assert 'x-gvfs-trash ' not in disabled
assert disabled.count('x-gvfs-notrash ') == 5
assert disabled.count('noauto,x-gvfs-notrash ') == 5
assert render(disabled, shares, True) == enabled
assert render(enabled, set(), True) == original
assert '/storage/roms' not in enabled and '/storage/scripts' not in enabled
user = original + 'none /storage/Desktop none x-gvfs-notrash 0 0\n'
assert render(user, shares, True).startswith(user)
assert render(user, shares, True).count('/storage/Desktop') == 1
for text in (api['START'], api['END'], enabled + enabled,
             api['START'] + 'personal data\n' + api['END'],
             api['START'] + 'none /storage/personal none defaults 0 0\n' + api['END']):
    try:
        render(text, shares, True)
    except RuntimeError:
        pass
    else:
        raise AssertionError('malformed managed block accepted')
supported = api['supported']
def query(command, **kwargs):
    return SimpleNamespace(returncode=0, stdout='install ok installed ' + api['EXPECTED'][command[-1]])
with patch.object(api['subprocess'], 'run', side_effect=query):
    assert supported()
for output, status in [('install ok installed 999.0', 0), ('', 1),
                       ('deinstall ok config-files 2.84.4-3~deb13u5+rocknix1', 0)]:
    with patch.object(api['subprocess'], 'run', return_value=SimpleNamespace(returncode=status, stdout=output)):
        assert not supported()
service = (repo / 'rootfs-overlay/etc/systemd/system/rocknix-desktop-session.service').read_text()
assert 'ExecStartPre=+/usr/bin/python3 /usr/local/bin/rocknix-trash-policy' in service
hook = (repo / 'rootfs-overlay/etc/apt/apt.conf.d/99rocknix-trash-policy').read_text()
assert '--apt --disable' in hook and 'DPkg::Post-Invoke' in hook
assert hook.count('|| true') == 2
assert api['mapped']() is False
print('PASS: narrow mount opt-in, exact package compatibility, update disable/reenable, user records and malformed-block refusal')
