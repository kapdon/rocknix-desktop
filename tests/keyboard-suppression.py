#!/usr/bin/env python3
"""Exercise production keyboard cleanup branches with command mocks only."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
launcher = (root / 'payload/bin/launch-sway-desktop').read_text()
restore = (root / 'payload/bin/restore-emulationstation').read_text()
assert "set_setting 'rocknix.touchscreen-keyboard.enabled' '0'" not in launcher
assert 'masked|masked-runtime) TOUCHKEYBOARD_MASK_OWNED=0' in launcher
assert launcher.index('mv -f "${SESSION_STATE}.new"') < launcher.index('systemctl mask --runtime')
assert 'TOUCHKEYBOARD_SETTING_CHANGED' not in restore
assert 'set_setting' not in restore
block = restore[restore.index('if [ "${TOUCHKEYBOARD_MASK_OWNED}" = 1 ]'):]
block = block[:block.index('STATE=$(systemctl is-system-running')]
for owned, target, expected in (
    (1, '/dev/null', ['systemctl unmask --runtime touchkeyboard.service']),
    (0, '/dev/null', []),  # Do not remove a pre-existing mask.
    (1, '/different', []),  # Do not remove a replaced runtime file.
):
    script = f'''
TOUCHKEYBOARD_MASK_OWNED={owned}
SESSION_STATE_PRESENT=1
readlink() {{ printf '%s' '{target}'; }}
systemctl() {{ printf 'systemctl %s\\n' "$*"; }}
set_setting() {{ printf 'setting %s\\n' "$*"; }}
''' + block
    result = subprocess.run(['bash', '-c', script], capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == expected, result.stdout
print('PASS: volatile keyboard mask ownership, native preferences unchanged')
