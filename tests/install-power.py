#!/usr/bin/python3
from pathlib import Path
import runpy
import tempfile

root = Path(__file__).resolve().parents[1]
check = runpy.run_path(str(root / 'payload/bin/rocknix-install-power'))['require_power']
with tempfile.TemporaryDirectory() as directory:
    battery = Path(directory)
    (battery / 'type').write_text('Battery\n')
    for value in ('10', '100', '50'):
        (battery / 'capacity').write_text(value)
        assert check(battery) == int(value)
    for value in ('0', '9', '-1', '101', 'unknown', '', '5.0'):
        (battery / 'capacity').write_text(value)
        (battery / 'status').write_text('Charging')
        try: check(battery)
        except RuntimeError: pass
        else: raise AssertionError(value)
    (battery / 'capacity').unlink()
    try: check(battery)
    except RuntimeError: pass
    else: raise AssertionError('missing telemetry accepted')
print('PASS: main battery threshold, charging no-bypass, invalid and unavailable telemetry refusal')
