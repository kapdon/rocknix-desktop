#!/usr/bin/python3
"""Offline launch contract; physical typing still needs device validation."""
from pathlib import Path
import shlex

source = Path('payload/bin/launch-sway-desktop').read_text()
command = source.split('/usr/bin/wvkbd-mobintl \\\n', 1)[1].split('\nWVKBD_PID=', 1)[0]
args = shlex.split(command.replace('\\\n', ' '))
for flag in ('-l', '--landscape-layers'):
    # ROCKNIX's patched "simple" is five rows, unlike upstream's four-row one.
    assert args[args.index(flag) + 1].split(',') == ['landscape', 'special', 'nav', 'full']
for flag in ('-H', '-L'):
    assert args[args.index(flag) + 1] == '${KEYBOARD_HEIGHT}'
assert '--hidden' in args
assert args[args.index('--output') + 1] == '${OUTPUT_NAME}'
assert args[args.index('-fn') + 1] == '${KEYBOARD_FONT_SIZE}'
print('PASS: four-row default in both orientations; secondary layers, adaptive height and visibility preserved')
