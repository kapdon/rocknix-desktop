#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'rootfs-overlay/usr/local/bin/rocknix-display-metrics').read_text()
keys = ('LOGICAL_WIDTH LOGICAL_HEIGHT BAR_HEIGHT BAR_FONT_SIZE STATUS_FONT_SIZE '
        'BAR_PADDING KEYBOARD_HEIGHT KEYBOARD_FONT_SIZE LAUNCHER_FONT_SIZE '
        'LAUNCHER_LINE_HEIGHT LAUNCHER_HORIZONTAL_PAD LAUNCHER_VERTICAL_PAD').split()
valid = {key: 20 for key in keys}
valid.update(LOGICAL_WIDTH=1920, LOGICAL_HEIGHT=1080, OUTPUT_NAME='DSI-1')
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'metrics.json'
    script = source.replace('/run/rocknix-desktop/display-metrics.json', str(path))
    script += '\nload_display_metrics || exit 7\nprintf "%s/%s" "$ROCKNIX_LOGICAL_WIDTH" "$ROCKNIX_OUTPUT_NAME"\n'
    path.write_text(json.dumps(valid))
    result = subprocess.run(['bash', '-c', script], capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout == '1920/DSI-1'
    for key, value in [('LOGICAL_WIDTH', '$(touch /tmp/unsafe-display-test)'),
                       ('KEYBOARD_HEIGHT', -1), ('BAR_HEIGHT', True),
                       ('OUTPUT_NAME', 'DSI-1\nPATH=/tmp'), ('OUTPUT_NAME', '*')]:
        path.write_text(json.dumps({**valid, key: value}))
        result = subprocess.run(['bash', '-c', script], capture_output=True, text=True)
        assert result.returncode == 7 and result.stdout == '', (key, result)
    path.write_text('{"OUTPUT_NAME":"DSI-1"}')
    result = subprocess.run(['bash', '-c', script], capture_output=True)
    assert result.returncode == 7
print('PASS: live metrics load atomically as validated values, never shell code')
