#!/usr/bin/python3
"""Versioned component publication stays draft until all installer assets exist."""
import json
import hashlib
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch

P = runpy.run_path('scripts/publish-versioned-components.py')
with tempfile.TemporaryDirectory() as temporary:
    work = Path(temporary)
    manifest = work / 'release.json'
    manifest.write_text(json.dumps({'built_at': '2026-10-03T00:00:00Z'}))
    (work / 'CHANGELOG.md').write_text('## Highlights since v0.1.0\n\n- Fit games to the desktop.\n\n'
        '<!-- development-changelog:start -->\n## Changes since v0.1.0\n\n- A change.\n'
        '<!-- development-changelog:end -->\n')
    calls = []
    pointer = None
    collision = False
    remote_mismatch = False
    fail_pointer = False
    previous = None
    wrong_draft = False
    def output(args, **kwargs):
        if 'rev-parse' in args:
            return 'a' * 40
        if '--heads' in args:
            return ('b' if remote_mismatch else 'a') * 40 + '\trefs/heads/dev'
        if '--tags' in args:
            return 'existing' if collision else ''
        if args[:3] == ('gh', 'release', 'view'):
            return json.dumps({'databaseId': 123, 'isDraft': True,
                               'targetCommitish': ('b' if wrong_draft else 'a') * 40})
        assert args[:2] == ('gh', 'api')
        if '--paginate' in args:
            return json.dumps([[{'tag_name': 'unrelated', 'draft': True}], [previous] if previous else []])
        # Draft assets must be looked up by release ID, never by unpublished tag.
        assert args[2] == 'repos/owner/repo/releases/123'
        return json.dumps({'assets': [{'name': name, 'size': len(data), 'state': 'uploaded',
            'digest': 'sha256:' + ('0' * 64 if fail_pointer else hashlib.sha256(data).hexdigest())}
            for name, data in [('bundle.tar', b'bundle'), ('bundle.tar.sha256', b'checksum')]]})
    def run(args, **kwargs):
        if args[1:3] == ['release', 'create']:
            notes = Path(args[args.index('--notes-file') + 1]).read_text()
            tag = args[3]
            assert '## Highlights since v0.1.0' in notes
            assert 'Fit games to the desktop.' in notes
            assert f'https://github.com/owner/repo/blob/{tag}/CHANGELOG.md' in notes
            assert '/blob/dev/' not in notes
            assert f'--release {tag}' in notes
        calls.append(args)
    def dependencies(*args, **kwargs):
        assert kwargs == {'components_only': True}
        calls.append(['dependencies'])
    def prepare(manifest, store, scratch, tag):
        candidate = scratch / 'manifest.json'; candidate.write_bytes(manifest.read_bytes())
        bundle = scratch / 'bundle.tar'; bundle.write_bytes(b'bundle')
        checksum = scratch / 'bundle.tar.sha256'; checksum.write_bytes(b'checksum')
        return json.loads(manifest.read_text()), bundle, checksum
    with patch.dict(P['publish'].__globals__, PROJECT=work), \
         patch.dict(P['P'], publish=dependencies, prepare_release=prepare), patch.dict(P['C'], release=lambda x: x), \
         patch('subprocess.check_output', side_effect=output), patch('subprocess.run', side_effect=run):
        for tag in ('v0.2.0', 'v0.2.0-beta.1'):
            calls.clear()
            P['publish'](tag, manifest, work, 'owner/repo')
            assert calls[0] == ['dependencies']
            create, edit = calls[1:]
            assert '--draft' in create and create[1:3] == ['release', 'create']
            assert '--draft=false' in edit and edit[1:3] == ['release', 'edit']
            assert ('--prerelease' in create) == ('-' in tag)
            assert ('--latest=false' in edit) == ('-' in tag)
        previous = {'tag_name': 'v0.2.0', 'draft': True}
        calls.clear()
        P['publish']('v0.2.0', manifest, work, 'owner/repo')
        assert calls[0] == ['dependencies']
        assert calls[1][1:5] == ['release', 'delete', 'v0.2.0', '--yes']
        assert calls[2][1:3] == ['release', 'create']
        assert calls[3][1:3] == ['release', 'edit']
        previous = None
        for case in ('tag', 'remote', 'pointer', 'syntax', 'published', 'draft-source'):
            previous = {'tag_name': 'v0.2.0', 'draft': False} if case == 'published' else None
            wrong_draft = case == 'draft-source'
            calls.clear()
            collision, remote_mismatch, fail_pointer = case == 'tag', case == 'remote', case == 'pointer'
            try:
                P['publish']('bad' if case == 'syntax' else 'v0.2.0', manifest, work, 'owner/repo')
                raise AssertionError('publication guard failed')
            except RuntimeError:
                pass
            assert not any('--draft=false' in call for call in calls)
            if case not in ('pointer', 'draft-source'):
                assert not calls
print('PASS: versioned component publication order, source/tag guards, draft-only retry and upload failure isolation')
