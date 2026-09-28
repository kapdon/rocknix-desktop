#!/usr/bin/python3
"""Offline launch contract; physical typing still needs device validation."""
from pathlib import Path
import shlex

source = Path('rootfs-overlay/usr/local/bin/rocknix-sway-session').read_text()
command = source.split('wvkbd-rocknix \\\n', 1)[1].split('\nWVKBD_PID=', 1)[0]
args = shlex.split(command.replace('\\\n', ' '))
for flag in ('-l', '--landscape-layers'):
    assert args[args.index(flag) + 1].split(',') == ['simple', 'special']
for flag in ('-H', '-L'):
    assert args[args.index(flag) + 1] == '${ROCKNIX_KEYBOARD_HEIGHT}'
assert '--hidden' in args
assert args[args.index('--output') + 1] == '${ROCKNIX_OUTPUT_NAME}'
assert args[args.index('-fn') + 1] == 'Roboto ${ROCKNIX_KEYBOARD_FONT_SIZE}'
for flag, value in {'-fg':'222222', '-fg-sp':'111111', '-bg':'000000', '-press':'444444', '--press-sp':'444444', '-R':'0'}.items():
    assert args[args.index(flag) + 1] == value
symbols = Path('experiments/wvkbd/symbols.h').read_text()
assert symbols.count('EndRow') == 3
assert all('KEY_' + key not in symbols for key in ('UP', 'DOWN', 'LEFT,', 'RIGHT,'))
assert 'BackLayer' in symbols
print('PASS: four-row default in both orientations; secondary layers, adaptive height and visibility preserved')
