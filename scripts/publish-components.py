#!/usr/bin/python3
"""Publish the CI-built tarball and checksum, then retire old rolling assets."""
import argparse
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
B = runpy.run_path(str(PROJECT / 'scripts/build-components.py'))
C = B['C']


class Publisher:
    def __init__(self, repository, revision):
        self.repository, self.revision = repository, revision
        self.known = {}

    def gh(self, *args, **kwargs):
        return subprocess.run(['gh', *map(str, args)], check=True, **kwargs)

    def assets(self, tag):
        if tag not in self.known:
            result = subprocess.run(['gh', 'api', f'repos/{self.repository}/releases/tags/{tag}'],
                                    capture_output=True, text=True)
            if result.returncode:
                if '(HTTP 404)' not in result.stderr:
                    raise RuntimeError('cannot inspect release: ' + result.stderr)
                self.gh('release', 'create', tag, '--repo', self.repository, '--target', self.revision,
                        '--prerelease', '--latest=false', '--title', tag,
                        '--notes', 'ROCKNIX Desktop installation bundles.')
                self.known[tag] = {}
            else:
                self.known[tag] = {item['name']: item for item in json.loads(result.stdout)['assets']}
        return self.known[tag]

    def upload(self, tag, name, digest, size, source=None):
        assets = self.assets(tag)
        if name in assets:
            item = assets[name]
            if item['state'] == 'uploaded' and item['size'] == size and item.get('digest') == 'sha256:' + digest:
                return False
            if tag != 'development':
                raise RuntimeError('immutable asset collision or incomplete upload: ' + name)
        if len(assets) >= 990:
            raise RuntimeError('release is full; retire old development bundles before publishing')
        if source is None or not source.is_file() or C['digest'](source) != digest or source.stat().st_size != size:
            raise RuntimeError('missing verified local artifact: ' + name)
        if source.name != name:
            raise RuntimeError('asset filename mismatch')
        self.gh('release', 'upload', tag, source, '--repo', self.repository,
                *(['--clobber'] if tag == 'development' else []))
        self.known.pop(tag)
        item = self.assets(tag).get(name)
        if not item or item.get('digest') != 'sha256:' + digest or item['size'] != size or item['state'] != 'uploaded':
            raise RuntimeError('uploaded artifact verification failed: ' + name)
        return True


def prepare_release(manifest, store, destination, tag):
    """Validate and assemble once in CI, preserving owners in one fakeroot session."""
    value = C['release'](json.loads(manifest.read_text()))
    revision = value['commit']
    bundle = destination / 'system.tar.xz'
    prefix = [] if os.geteuid() == 0 else ['fakeroot', '--']
    subprocess.run([*prefix, 'python3', PROJECT / 'scripts/package-components.py',
                    '--manifest', manifest, '--store', store, '--output', bundle], check=True)
    if bundle.stat().st_size >= 2 * 1024**3:
        raise RuntimeError('bundle exceeds release asset limit')
    bundle_sha = C['digest'](bundle)
    bundle = bundle.rename(destination / 'rocknix-desktop-rp6-arm64.tar.xz')
    checksum = destination / (bundle.name + '.sha256')
    checksum.write_text(f'{bundle_sha}  {bundle.name}\n')
    return value, bundle, checksum


def publish(manifest, store, repository, components_only=False):
    value = C['release'](json.loads(manifest.read_text()))
    revision = subprocess.check_output(['git', '-C', PROJECT, 'rev-parse', 'HEAD'], text=True).strip()
    if value['commit'] != revision or value.get('local_override') or subprocess.check_output(
            ['git', '-C', PROJECT, 'status', '--porcelain'], text=True).strip():
        raise RuntimeError('publication requires a clean exact commit and the locked native package build')
    keys, _ = B['input_keys']()
    if any(spec['input_key'] != keys[role] for role, spec in value['components'].items()):
        raise RuntimeError('build inputs changed after the component build')
    publisher = Publisher(repository, revision)
    with tempfile.TemporaryDirectory(prefix='component-publication-') as scratch:
        scratch = Path(scratch)
        # Generate release highlights and the full changelog before publication.
        # Record the latter on dev after the assets, notes and tag all succeed.
        notes = manifest.parent / 'development-notes.md'
        if not components_only:
            with notes.open('w') as stream:
                subprocess.run(['python3', PROJECT / 'scripts/development-release-notes.py',
                                revision, value['built_at'], '--repository', repository,
                                '--changelog', manifest.parent / 'CHANGELOG.md'],
                               check=True, stdout=stream)
        if components_only:
            print('Build validated; benchmark leaves all releases unchanged.')
            return
        value, bundle, checksum = prepare_release(manifest, store, scratch, 'development')
        for artifact in (bundle, checksum):
            publisher.upload('development', artifact.name, C['digest'](artifact), artifact.stat().st_size, artifact)
        publisher.gh('release', 'edit', 'development', '--repo', repository, '--prerelease', '--latest=false',
                     '--title', 'Rolling development build', '--notes-file', notes)
        # Only the current tarball and checksum remain on the rolling release.
        # New uploads are verified before deleting any superseded asset.
        for name, asset in publisher.assets('development').items():
            if name not in (bundle.name, checksum.name):
                publisher.gh('api', f'repos/{repository}/releases/assets/{asset["id"]}', '--method', 'DELETE')
        tag = publisher.gh('api', f'repos/{repository}/git/tags', '--method', 'POST',
                           '-f', 'tag=development', '-f', f'object={revision}', '-f', 'type=commit',
                           '-f', f'message=Rolling development components ({revision})', '--jq', '.sha',
                           capture_output=True, text=True).stdout.strip()
        publisher.gh('api', f'repos/{repository}/git/refs/tags/development', '--method', 'PATCH',
                     '-f', f'sha={tag}', '-F', 'force=true')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=PROJECT / 'dist/components/release.json')
    parser.add_argument('--store', type=Path, default=PROJECT / 'build/component-store')
    parser.add_argument('--repository', default='kapdon/rocknix-desktop')
    parser.add_argument('--components-only', action='store_true',
                        help='validate the build without publishing or changing any channel pointer or tag')
    args = parser.parse_args()
    publish(args.manifest, args.store, args.repository, args.components_only)
