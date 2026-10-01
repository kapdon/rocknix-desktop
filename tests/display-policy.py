#!/usr/bin/env python3
import copy
from pathlib import Path
import runpy

api = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'payload/bin/rocknix-display-policy'))
mode = {'width': 1080, 'height': 1920, 'refresh': 120000}
output = {'name': 'DSI-1', 'active': True, 'scale': 1.25,
          'transform': '270', 'current_mode': mode, 'modes': [mode, {**mode, 'refresh': 60000}]}
events, preferences, now = [], [], [10]
t = api['Transaction'](lambda s: events.append(('journal', s)),
                       lambda c: events.append(('apply', c)),
                       lambda: now[0], preferences.append)
t.begin(output)
assert events[0][0] == 'journal' and events[1][0] == 'apply'
assert events[1][1].endswith('scale 1')
token = t.preview({**output, 'scale': 1.0}, scale=1.5)
assert events[-2][0] == 'journal' and events[-1][1].endswith('scale 1.5')
t.keep(token)
assert preferences[-1]['scale'] == 1.5
t.restore()
assert events[-2][1].endswith('scale 1.25'), events
assert t.state == {'original': {}, 'pending': None}

token = t.preview(output, selected_mode={**mode, 'refresh': 60000})
assert '60.000Hz' in events[-1][1]
now[0] += 15
t.tick()
assert t.state['pending'] is None and '120.000Hz' in events[-2][1]
try:
    t.keep(token)
    raise AssertionError('expired confirmation accepted')
except ValueError:
    pass

def rejected(fn):
    before = copy.deepcopy(events)
    try:
        fn()
    except (ValueError, KeyError):
        assert before == events, 'invalid request mutated display/journal'
    else:
        raise AssertionError('invalid display request accepted')

for scale in (0, -1, 1.1, 3, True, float('nan'), float('inf'), '1; exec bad'):
    rejected(lambda: t.preview(output, scale=scale))
for name in ('*', '-', 'DSI-1; exec bad', 'DSI-1\nreload', '"DSI-1"'):
    rejected(lambda: t.preview({**output, 'name': name}, scale=1.5))
rejected(lambda: t.preview(output, selected_mode={**mode, 'width': 1920}))
rejected(lambda: t.preview({**output, 'active': False}, scale=1.5))
rejected(lambda: t.preview({**output, 'transform': 'normal'}, scale=2))
token = t.preview(output, scale=1.5)
rejected(lambda: t.preview(output, scale=2))
rejected(lambda: t.keep('wrong-token'))
t.revert()
assert t.state['pending'] is None

# Apply failure retains the original snapshot and rolls back the preview.
calls = []
def fail_once(c):
    calls.append(c)
    if len(calls) == 1:
        raise RuntimeError('mode rejected by compositor')
f = api['Transaction'](lambda s: None, fail_once, lambda: 0, lambda s: None)
try:
    f.preview(output, scale=1.5)
except RuntimeError:
    pass
assert len(calls) == 2 and calls[-1].endswith('scale 1.25')
assert f.state['pending'] is None and 'DSI-1' in f.state['original']

# A failed journal must not let a later retry skip durable intent.
attempts, mutations = [], []
def fail_journal(s):
    attempts.append(s)
    raise OSError('storage unavailable')
f = api['Transaction'](fail_journal, mutations.append, lambda: 0, lambda s: None)
for _ in range(2):
    try:
        f.begin(output)
    except OSError:
        pass
assert len(attempts) == 2 and not mutations and not f.state['original']
print('PASS: default 1.0, journal-before-mutation, advertised modes, preview timeout, keep/revert and native restore')
print('PASS: invalid scales, injection names, stale confirmations and unusable logical sizes rejected')
