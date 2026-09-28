#!/usr/bin/env python3
"""Offline profile contract checks; these do not emulate InputPlumber/uinput."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
profile = (root / 'payload/input/desktop.yaml').read_text()
# Deliberately inspect the profile's block-form mapping entries without adding a
# YAML runtime dependency to the shell-only CI. A shape change fails closed.
entries = re.split(r'^  - name: ', profile, flags=re.M)[1:]
assert len(entries) == 23, 'Review added/removed controller actions'
buttons = {}
for entry in entries:
    source, target = entry.split('    target_events:\n')
    match = re.search(r'^        button: (\w+)$', source, re.M)
    if match:
        button = match[1]
        assert button not in buttons, f'Duplicate source button: {button}'
        buttons[button] = target.strip()

expected = {
    'West': '- keyboard: KeyTab',
    'North': '- keyboard: KeyLeftShift\n      - keyboard: KeyTab',
    'South': '- keyboard: KeyEnter',
    'East': '- keyboard: KeyEsc',
    'Start': '- keyboard: KeyEsc',
    'Select': '- keyboard: KeyF14',
    'LeftStick': '- keyboard: KeyF13',
    'RightStick': '- keyboard: KeyF15',
    'Guide': '- dbus: ui_guide',
    'QuickAccess': '- dbus: ui_quick',
    'DPadUp': '- keyboard: KeyUp',
    'DPadDown': '- keyboard: KeyDown',
    'DPadLeft': '- keyboard: KeyLeft',
    'DPadRight': '- keyboard: KeyRight',
    'RightBumper': '- mouse:\n          wheel:\n            direction: up',
    'LeftBumper': '- mouse:\n          wheel:\n            direction: down',
}
# Strip comments outside the target list (the next action can have a preamble).
buttons = {key: '\n'.join(line for line in value.splitlines()
                         if not line.lstrip().startswith('#')).rstrip()
           for key, value in buttons.items()}
assert buttons == expected, f'Controller button contract changed: {buttons}'
for trigger, click in [('LeftTrigger', 'Left'), ('RightTrigger', 'Right')]:
    entry = next(e for e in entries if f'name: {trigger}\n' in e)
    assert 'deadzone: 0.2\n' in entry
    assert entry.split('    target_events:\n')[1].strip() == (
        f'- mouse:\n          button: {click}')
pointer = next(e for e in entries if e.startswith('Pointer\n'))
assert 'name: RightStick\n' in pointer and 'speed_pps: 800' in pointer
for direction, key in [('left', 'A'), ('right', 'D'), ('up', 'W'), ('down', 'S')]:
    entry = next(e for e in entries if f'direction: {direction}\n' in e)
    assert 'name: LeftStick\n' in entry and 'deadzone: 0.3\n' in entry
    assert entry.split('    target_events:\n')[1].strip() == f'- keyboard: Key{key}'
print('PASS: field-navigation chord order and all preserved controller actions')
