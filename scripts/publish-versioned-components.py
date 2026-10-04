#!/usr/bin/python3
"""Publish a tested installation tarball as an immutable versioned release."""
import argparse
import json
from pathlib import Path
import re
import runpy
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
P = runpy.run_path(str(PROJECT / 'scripts/publish-components.py'))
C = P['C']
N = runpy.run_path(str(PROJECT / 'scripts/development-release-notes.py'))


def publish(tag, manifest, store, repository):
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?', tag):
        raise RuntimeError('invalid version tag')
    def output(*args):
        return subprocess.check_output(args, text=True).strip()
    revision = output('git', '-C', str(PROJECT), 'rev-parse', 'HEAD')
    remote = output('git', '-C', str(PROJECT), 'ls-remote', '--heads', 'origin', 'refs/heads/dev')
    if remote.split() != [revision, 'refs/heads/dev']:
        raise RuntimeError('release source must match remote dev')
    if output('git', '-C', str(PROJECT), 'ls-remote', '--tags', 'origin', 'refs/tags/' + tag):
        raise RuntimeError('version tag already exists')
    # The by-tag REST endpoint excludes drafts. List releases with the CI token
    # so an interrupted publication can replace only its unpublished draft.
    pages = json.loads(output('gh', 'api', '--paginate', '--slurp',
                              f'repos/{repository}/releases?per_page=100'))
    previous = next((item for page in pages for item in page if item['tag_name'] == tag), None)
    if previous and not previous['draft']:
        raise RuntimeError('version release already published')
    # This validates clean/exact source without publishing intermediate artifacts.
    # It never advances the development pointer or tag.
    P['publish'](manifest, store, repository, components_only=True)
    def gh(*args):
        subprocess.run(['gh', *map(str, args), '--repo', repository], check=True)
    with tempfile.TemporaryDirectory(prefix='versioned-components-') as scratch:
        scratch = Path(scratch)
        value, bundle, checksum = P['prepare_release'](manifest, store, scratch, tag)
        notes = scratch / 'notes.md'
        changelog = (PROJECT / 'CHANGELOG.md').read_text()
        _, details, _ = N['changelog_section'](changelog)
        notes.write_text(N['release_summary'](details, changelog, repository, tag)
                         + f'\nInstall with `--release {tag}`.\n')
        prerelease = '-' in tag
        flags = ['--prerelease'] if prerelease else []
        if previous:
            gh('release', 'delete', tag, '--yes')
        gh('release', 'create', tag, bundle, checksum, '--target', revision,
           '--draft', *flags, '--title', 'ROCKNIX Desktop ' + tag, '--notes-file', notes)
        draft = json.loads(output('gh', 'release', 'view', tag, '--repo', repository,
                                  '--json', 'databaseId,isDraft,targetCommitish'))
        if not draft['isDraft'] or draft['targetCommitish'] != revision:
            raise RuntimeError('release draft does not match source')
        assets = json.loads(output('gh', 'api',
                            f'repos/{repository}/releases/{draft["databaseId"]}'))['assets']
        for artifact in (bundle, checksum):
            item = next((a for a in assets if a['name'] == artifact.name), None)
            if (not item or item['state'] != 'uploaded' or item['size'] != artifact.stat().st_size
                    or item.get('digest') != 'sha256:' + C['digest'](artifact)):
                raise RuntimeError('release upload verification failed')
        gh('release', 'edit', tag, '--draft=false', '--latest=' + ('false' if prerelease else 'true'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag')
    parser.add_argument('--manifest', type=Path, default=PROJECT / 'dist/components/release.json')
    parser.add_argument('--store', type=Path, default=PROJECT / 'build/component-store')
    parser.add_argument('--repository', default='kapdon/rocknix-desktop')
    args = parser.parse_args()
    publish(args.tag, args.manifest, args.store, args.repository)
