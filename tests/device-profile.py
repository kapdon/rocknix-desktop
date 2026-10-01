#!/usr/bin/python3
"""Device eligibility contracts; synthetic identities are not hardware tests."""
import json
import os
from pathlib import Path
import runpy
import stat
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

api = runpy.run_path('payload/bin/rocknix-device-profile')
require = api['require_identity']
with patch.dict(require.__globals__, identity=lambda: 'Untested handheld', consent=lambda model: False):
    try:
        require()
        raise AssertionError('untested hardware accepted without consent')
    except RuntimeError as error:
        assert 'confirm its device warning' in str(error)
    assert require(True) == 'Untested handheld'
with patch.dict(require.__globals__, identity=lambda: api['RP6'], consent=lambda model: False):
    assert require() == api['RP6']

node = Path('/dev/dri/renderD128')
endpoint = api['render_endpoint']
info = SimpleNamespace(st_uid=0, st_mode=stat.S_IFCHR | 0o660, st_rdev=os.makedev(226, 128))
with patch.object(Path, 'lstat', return_value=info):
    assert endpoint(node)[1] == 'msm'
    for bad in ('/dev/dri/card0', '/dev/video1', '/dev/dri/renderD129', '/tmp/renderD128'):
        try:
            endpoint(bad)
            raise AssertionError('non-render endpoint accepted')
        except RuntimeError:
            pass
    with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=0,
                st_mode=stat.S_IFCHR | 0o660, st_rdev=os.makedev(81, 0))):
        try:
            endpoint(node)
            raise AssertionError('wrong endpoint device identity accepted')
        except RuntimeError:
            pass

resolve = api['resolve']
def capability_text(path):
    return 'qcom-iris-decoder' if path.name == 'name' else '1000'
with patch.dict(resolve.__globals__, require_identity=lambda allow: 'Untested handheld',
                render_endpoint=lambda path: (info, 'msm')), \
        patch.object(Path, 'read_text', capability_text), \
        patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=0,
                          st_mode=stat.S_IFCHR | 0o660, st_rdev=os.makedev(81, 0))):
    profile = resolve(True)
    assert profile['render'] == str(node)
    assert profile['decoder'] == '/dev/video0' and profile['native_fex']
    assert profile['experimental'] and profile['gallium'] == 'freedreno'
    with patch.object(Path, 'read_text', return_value='camera'):
        try:
            resolve(True)
            raise AssertionError('non-decoder video endpoint accepted')
        except RuntimeError:
            pass

source = Path('install.sh').read_text()
assert source.index('device-profile.json') < source.index('detect_installation\n')
assert '--experimental-device' not in source
assert 'bundle is missing required Desktop integration' in source
assert source.index('confirm_untested_device "$DEVICE_MODEL"') < source.index('acquire_install_lock\n')
assert source.index('if [ "$check" = 1 ]') < source.index('confirm_untested_device "$DEVICE_MODEL"')
assert 'device-check.log' in source
for answer, accepted in (('y\n', True), ('YES\n', True), ('n\n', False), ('\n', False), ('', False)):
    result = subprocess.run(['bash', '-c', 'source ./install.sh; read_confirmation() { read -r "$1"; }; confirm_untested_device "Fixture handheld"'],
                            input=answer, text=True, capture_output=True)
    assert (result.returncode == 0) == accepted, result
    assert '[y/N]' in result.stdout and 'only been hardware-tested' in result.stdout
# Mock only the native preflight, not the public main flow: confirmation must
# happen before acquiring a lock/downloading, even with --yes or a release tag.
for release in ('development', 'v0.1.0'):
    result = subprocess.run(['bash', '-c', '''
source ./install.sh
read_confirmation() { read -r "$1"; }
check_device() { EXPERIMENTAL_DEVICE=1; DEVICE_MODEL='Fixture handheld'; }
acquire_install_lock() { echo 'UNEXPECTED LOCK'; exit 91; }
main --release "$1" --yes
''', 'fixture', release], input='n\n', text=True, capture_output=True)
    assert result.returncode == 0 and 'Cancelled.' in result.stdout, result
    assert 'UNEXPECTED LOCK' not in result.stdout
result = subprocess.run(['bash', '-c', '''
source ./install.sh
check_device() { EXPERIMENTAL_DEVICE=1; DEVICE_MODEL='Fixture handheld'; }
main --check
'''], input='', text=True, capture_output=True)
assert result.returncode == 0 and 'Installation will require confirmation.' in result.stdout
assert '[y/N]' not in result.stdout
assert "profile['resolve']" in Path('payload/bin/rocknix-lxc-install').read_text()
assert "['require_identity']()" in Path('payload/bin/rocknix-lxc-uninstall').read_text()

desktop = runpy.run_path('payload/bin/rocknix-lxc-desktop')
environment = desktop['session_environment']({}, profile)
assert 'GALLIUM_DRIVER=freedreno' in environment
assert 'ROCKNIX_SOFTWARE_VIDEO' not in environment

identity = api['identity']
for chipset, eligible in (('SM8550', True), ('SM8250', False), ('RK3588', False)):
    release = f'OS_NAME="ROCKNIX"\nHW_DEVICE="{chipset}"\nDISTRO_DEVICE="{chipset}"\n'
    with patch.object(Path, 'read_bytes', return_value=b'Untested handheld\0'), \
            patch.object(Path, 'read_text', return_value=release), \
            patch('os.uname', return_value=SimpleNamespace(machine='aarch64')):
        try:
            assert identity() == 'Untested handheld'
        except RuntimeError:
            assert not eligible
        else:
            assert eligible

for release in ('OS_NAME="ROCKNIX"\nHW_DEVICE="SM8550"\n',
                'OS_NAME="ROCKNIX"\nHW_DEVICE="SM8550"\nDISTRO_DEVICE="SM8250"\n',
                'OS_NAME="Debian"\nHW_DEVICE="SM8550"\nDISTRO_DEVICE="SM8550"\n'):
    with patch.object(Path, 'read_bytes', return_value=b'Untested handheld\0'), \
            patch.object(Path, 'read_text', return_value=release), \
            patch('os.uname', return_value=SimpleNamespace(machine='aarch64')):
        try:
            identity()
            raise AssertionError('missing/mismatched native platform identity accepted')
        except RuntimeError:
            pass

written = []
api['save_consent'](profile, lambda *args: written.append(args), Path('/fixture/device.json'))
assert len(written) == 1 and written[0][2] == 0o600
record = json.loads(written[0][1])
assert record == {'format': 1, 'model': 'Untested handheld',
                  'architecture': 'aarch64', 'experimental': True}
api['save_consent']({**profile, 'experimental': False}, lambda *args: written.append(args))
assert len(written) == 1, 'RP6 must not acquire experimental consent'

# Consent is model-bound, host-owned and outside the writable container.
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'device.json'
    path.write_text(json.dumps({'format': 1, 'model': 'Untested handheld',
                               'architecture': 'aarch64', 'experimental': True}))
    real_stat = Path.lstat
    def fake_stat(item):
        value = real_stat(item)
        return SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o755) if item != path else \
            SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o600)
    with patch.object(Path, 'lstat', fake_stat):
        assert api['consent']('Untested handheld', path)
        assert not api['consent']('Different handheld', path)
        with patch.dict(require.__globals__, identity=lambda: 'Untested handheld',
                        consent=lambda model: api['consent'](model, path)):
            assert require() == 'Untested handheld', 'persisted consent must support normal launch/update/uninstall'
            with patch.dict(require.__globals__, identity=lambda: 'Different handheld'):
                try:
                    require()
                    raise AssertionError('consent transferred to a different device')
                except RuntimeError:
                    pass
    with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=201000, st_mode=stat.S_IFREG | 0o600)):
        try:
            api['consent']('Untested handheld', path)
            raise AssertionError('guest-owned consent accepted')
        except RuntimeError:
            pass
    for bad_mode in (stat.S_IFREG | 0o666, stat.S_IFLNK | 0o600):
        def unsafe_record(item):
            return SimpleNamespace(st_uid=0, st_mode=bad_mode if item == path else stat.S_IFDIR | 0o755)
        with patch.object(Path, 'lstat', unsafe_record):
            try:
                api['consent']('Untested handheld', path)
                raise AssertionError('writable/linked consent accepted')
            except RuntimeError:
                pass
print('PASS: automatic SM8550 warning/confirmation, strict GPU/decoder identity and model-bound host consent')
