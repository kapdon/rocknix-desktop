#!/usr/bin/env python3
"""Exercise menu routing with fixed host state; no compositor or FIFO writes."""
import runpy
from pathlib import Path

api = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                         'rootfs-overlay/usr/local/bin/rocknix-display-menu'))
g = api['main'].__globals__
mode = {'width': 1080, 'height': 1920, 'refresh': 120000}
output = {'name': 'DSI-1', 'scale': 1, 'scales': [1, 1.25, 1.5, 2],
          'transform': '270', 'mode': mode, 'modes': [mode]}
g['state'] = lambda: {'outputs': [output], 'pending': None}
requests = []
g['apply'] = requests.append
seen = []
answers = iter(['scale', '1.5'])
def choose(prompt, choices, seconds=None):
    seen.append((prompt, choices))
    return next(answers)
g['menu'] = choose
g['main']()
assert requests == [['scale', 'DSI-1', '1.5']]
assert any('Default' in label for label, value in seen[-1][1] if value == '1')
answers = iter(['mode', ['1080', '1920', '120000']])
g['main']()
assert requests[-1] == ['mode', 'DSI-1', '1080', '1920', '120000']
assert seen[-1][1][0][0] == '1920 × 1080 · 120 Hz · Current'
answers = iter([None])
before = list(requests)
g['main']()
assert requests == before
print('PASS: scale/default labels, rotated mode labels, fixed requests and menu dismissal')
