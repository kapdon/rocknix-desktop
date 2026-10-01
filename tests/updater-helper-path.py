#!/usr/bin/python3
"""Exercise actual copied-updater helper resolution under fakeroot."""
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch

source = Path('payload/bin/rocknix-lxc-upgrade').read_bytes()
for layout in ('bundle', 'installed', 'payload'):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        directory = root / ('payload/bin' if layout == 'bundle' else 'bin')
        directory.mkdir(parents=True)
        script = directory / 'rocknix-lxc-upgrade' if layout == 'payload' else root / 'upgrade-lxc.py'
        script.write_bytes(source)
        helper = directory / 'rocknix-install-power'
        helper.write_text('fixture')
        helper.chmod(0o644)
        api = runpy.run_path(str(script))
        locate = api['helper_path']
        # Fixture ancestry is /tmp, unlike root-owned production /storage.
        with patch.dict(locate.__globals__, safe_directory=lambda p: None):
            assert locate('rocknix-install-power') == helper
            helper.chmod(0o666)
            try:
                locate('rocknix-install-power')
                raise AssertionError('writable helper accepted')
            except RuntimeError:
                pass
            helper.unlink()
            helper.symlink_to('/usr/bin/python3')
            try:
                locate('rocknix-install-power')
                raise AssertionError('linked helper accepted')
            except RuntimeError:
                pass
print('PASS: bundled, installed and payload updater helper paths; unsafe helper refusal')
