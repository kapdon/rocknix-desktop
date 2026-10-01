#!/usr/bin/env python3
"""Record the candidate Trash patch in a Debian quilt source package.

Build-container-only helper; never run against an installed rootfs. Exact
source versions and unmodified Debian packaging are prerequisites. No holds
or epoch overrides: a newer Debian revision must win over this local build.
"""
import os
from pathlib import Path
import subprocess
import sys


def run(*args, cwd=None, env=None):
    return subprocess.check_output(args, cwd=cwd, env=env, text=True).strip()


def main():
    kind, directory, expected = sys.argv[1:]
    source = {'glib': 'glib2.0', 'gvfs': 'gvfs'}[kind]
    tree = Path(directory).resolve(strict=True)
    version = run('dpkg-parsechangelog', '--show-field', 'Version', cwd=tree)
    name = run('dpkg-parsechangelog', '--show-field', 'Source', cwd=tree)
    if version != expected or name != source or '+rocknix' in version:
        raise SystemExit('unexpected or already-modified source package')
    if (tree / 'debian/source/format').read_text().strip() != '3.0 (quilt)':
        raise SystemExit('expected Debian quilt source package')
    patch = tree / 'debian/patches/rocknix-mount-aware-trash.patch'
    if patch.exists():
        raise SystemExit('candidate patch already exists')
    # Verify the upstream packaging state before editing source files.
    run('dpkg-source', '--before-build', str(tree))
    run(sys.executable, str(Path(__file__).with_name('patch-trash.py')),
        kind, str(tree))
    env = dict(os.environ, EDITOR='true', VISUAL='true',
               DEBFULLNAME='ROCKNIX Desktop',
               DEBEMAIL='rocknix-desktop@localhost')
    run('dpkg-source', '--commit', '.', patch.name, cwd=tree, env=env)
    run('dch', '--newversion', version + '+rocknix1', '--distribution', 'trixie',
        'ROCKNIX Desktop: mount-aware Trash for explicitly shared LXC binds; '
        'retain Debian build options and security patches.', cwd=tree, env=env)
    run('dpkg', '--compare-versions', version, 'lt', version + '+rocknix1')


if __name__ == '__main__':
    main()
