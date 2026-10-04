#!/usr/bin/python3
"""Publication ordering/collision guards without contacting GitHub."""
import hashlib
import json
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
P = runpy.run_path(str(PROJECT / 'scripts/publish-components.py'))


def rejects(fn, *args):
    try:
        fn(*args)
    except RuntimeError:
        return
    raise AssertionError('unsafe publication accepted')


with tempfile.TemporaryDirectory() as temporary:
    work = Path(temporary)
    payload = work / 'payload.tar.xz'; payload.write_bytes(b'verified artifact')
    sha, size = P['C']['digest'](payload), payload.stat().st_size
    remote, calls = {}, []
    publisher = P['Publisher']('owner/repo', 'a' * 40)
    def assets(tag):
        publisher.known[tag] = remote
        return remote
    def gh(*args, **kwargs):
        calls.append(args)
        assert args[:3] == ('release', 'upload', 'development')
        remote[Path(args[3]).name] = {'size': size, 'digest': 'sha256:' + sha, 'state': 'uploaded'}
    publisher.assets, publisher.gh = assets, gh
    assert publisher.upload('development', payload.name, sha, size, payload)
    assert len(calls) == 1
    assert not publisher.upload('development', payload.name, sha, size)
    assert len(calls) == 1
    remote[payload.name]['digest'] = 'sha256:' + '0' * 64
    assert publisher.upload('development', payload.name, sha, size, payload)
    assert len(calls) == 2
    remote.clear()
    rejects(publisher.upload, 'development', payload.name, sha, size)
    assert len(calls) == 2
    print('PASS: publisher skips verified existing assets and rejects mismatches or unavailable misses')

    C = P['C']; components = {}
    for role in C['ROLES']:
        components[role] = {'format': 1, 'id': role, 'input_key': 'b' * 64, 'sha256': sha,
                            'asset': sha + '.tar.xz', 'size': size, 'unpacked_size': 20,
                            'managed': {}}
    (work / (sha + '.tar.xz')).write_bytes(payload.read_bytes())
    manifest = work / 'release.json'
    value = {'format': 2, 'minimum_installer': 2, 'runtime_abi': C['ABI'], 'platform': 'linux/arm64',
             'commit': 'a' * 40, 'built_at': '2026-10-02T00:00:00Z', 'components': components}
    manifest.write_bytes(C['encoded'](value))
    events = []
    class FakePublisher:
        fail = False
        def __init__(self, *_):
            pass
        def upload(self, tag, name, digest, size, source):
            events.append(('upload', tag, name))
            if self.fail:
                raise RuntimeError('interrupted upload')
        def assets(self, tag):
            return {'obsolete.json': {'id': 123}, **{event[2]: {'id': 456} for event in events if event[0] == 'upload'}}
        def gh(self, *args, **kwargs):
            events.append(('gh', *args))
            return SimpleNamespace(stdout='c' * 40)
    state = P['publish'].__globals__
    def output(args, **kwargs):
        return '' if '--porcelain' in args else 'a' * 40
    def generate_notes(args, **kwargs):
        if '--output' in args:
            events.append(('package',))
            Path(args[args.index('--output') + 1]).write_bytes(b'assembled system fixture')
            return SimpleNamespace(returncode=0)
        events.append(('notes',))
        assert '--repository' in args and args[args.index('--repository') + 1] == 'owner/repo'
        assert '--changelog' in args
        Path(args[args.index('--changelog') + 1]).write_text('changelog fixture')
        kwargs['stdout'].write('notes fixture')
        return SimpleNamespace(returncode=0)
    with patch.dict(state, Publisher=FakePublisher), patch.dict(P['B'], input_keys=lambda: ({r: 'b' * 64 for r in C['ROLES']}, {})), \
         patch.object(state['subprocess'], 'check_output', output), patch.object(state['subprocess'], 'run', generate_notes):
        P['publish'](manifest, work, 'owner/repo')
        assert events[0] == ('notes',)
        assert (manifest.parent / 'CHANGELOG.md').read_text() == 'changelog fixture'
        uploads = [i for i, e in enumerate(events) if e[0] == 'upload']
        deletes = [i for i, e in enumerate(events) if '--method' in e and 'DELETE' in e]
        assert len(uploads) == 2 and len(deletes) == 1 and max(uploads) < deletes[0]
        assert not any('latest.json' in str(e) or '.py' in str(e) for e in events if e[0] == 'upload')
        events.clear()
        P['publish'](manifest, work, 'owner/repo', components_only=True)
        assert not events
        print('PASS: hosted benchmark validates without publishing any release assets')
        events.clear()
        def failed_notes(*args, **kwargs):
            raise RuntimeError('release comparison unavailable')
        with patch.object(state['subprocess'], 'run', failed_notes):
            rejects(P['publish'], manifest, work, 'owner/repo')
        assert not events
        print('PASS: changelog generation failure prevents all publication mutations')
        events.clear()
        def failed_package(*args, **kwargs):
            raise RuntimeError('invalid component composition')
        with patch.dict(state, prepare_release=failed_package):
            rejects(P['publish'], manifest, work, 'owner/repo')
        assert events == [('notes',)]
        print('PASS: packaging validation failure prevents release mutation')
        events.clear(); FakePublisher.fail = True
        rejects(P['publish'], manifest, work, 'owner/repo')
        assert not any(e[:3] == ('gh', 'release', 'upload') for e in events)
        value['local_override'] = True; manifest.write_bytes(C['encoded'](value)); events.clear()
        rejects(P['publish'], manifest, work, 'owner/repo')
        assert not events
    print('PASS: two verified uploads precede CI cleanup; failures cannot publish release notes or remove old assets')
