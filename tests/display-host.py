#!/usr/bin/env python3
import copy
from pathlib import Path
import runpy

api = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'payload/bin/rocknix-display-settings'))
class Store:
    def __init__(self):
        self.files = {}
    def read(self, name, default):
        return copy.deepcopy(self.files.get(name, default))
    def write(self, name, value):
        self.files[name] = copy.deepcopy(value)

store, commands, clock = Store(), [], [0]
mode = {'width': 1080, 'height': 1920, 'refresh': 120000}
output = {'name': 'DSI-1', 'active': True, 'current_mode': mode,
          'modes': [mode], 'scale': 1.0, 'transform': '270'}
def host():
    return api['Host'](store, lambda: [output], commands.append, lambda: clock[0])
h = host()
h.begin('DSI-1')
token = h.request(['scale', 'DSI-1', '1.5'])
assert store.files['session.json']['pending']['token'] == token
# Simulate helper restart: durable journal still allows timeout rollback.
clock[0] = 16
host().transaction.tick()
assert commands[-1].endswith('scale 1')
token = host().request(['scale', 'DSI-1', '1.25'])
host().request(['keep', token])
assert store.files['preferences.json']['DSI-1']['scale'] == 1.25
host().transaction.restore()
host().begin('DSI-1')
assert commands[-1].endswith('scale 1.25')

for request in (['exec', 'bad'], ['scale', '*', '1.5'], ['scale', 'DSI-1', 'nan'],
                ['mode', 'DSI-1', '1', '1', '1'], ['keep', token], ['revert', token],
                ['scale', 'DSI-1', '1.5; exec bad'], ['scale', 'DSI-1', '2', 'extra']):
    before = list(commands)
    try:
        host().request(request)
    except (ValueError, KeyError):
        pass
    else:
        raise AssertionError(request)
    assert commands == before

host().transaction.restore()
store.files['preferences.json']['DSI-1']['mode'] = {'width': 800, 'height': 600, 'refresh': 60000}
host().begin('DSI-1')
assert commands[-1] == 'output DSI-1 mode 1080x1920@120.000Hz scale 1'

bad = copy.deepcopy(store.files['session.json'])
bad['original']['DSI-1']['name'] = '*; exec bad'
store.files['session.json'] = bad
try:
    host()
except ValueError:
    pass
else:
    raise AssertionError('unsafe restoration journal accepted')
print('PASS: fixed host request grammar, durable restart rollback, confirmed preferences and journal validation')
