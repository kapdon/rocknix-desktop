#!/usr/bin/env python3
"""Install audited runtime candidates during the disposable rootfs image build."""
import argparse
from pathlib import Path
import subprocess

VERSIONS = {'glib': '2.84.4-3~deb13u5+rocknix1', 'gvfs': '1.57.2-2+deb13u1+rocknix1'}
PACKAGES = ('gir1.2-glib-2.0', 'libglib2.0-0t64', 'libglib2.0-bin',
            'libglib2.0-data', 'gvfs', 'gvfs-backends', 'gvfs-common',
            'gvfs-daemons', 'gvfs-libs')


def runtime_paths(directory):
    result = []
    for name in PACKAGES:
        version = VERSIONS['gvfs' if name.startswith('gvfs') else 'glib']
        arch = 'all' if name in ('gvfs-common', 'libglib2.0-data') else 'arm64'
        path = directory / f'{name}_{version}_{arch}.deb'
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f'missing regular runtime package: {path}')
        result.append(str(path))
    return result


def validate_plan(output, allowed=PACKAGES):
    changed = set()
    for line in output.splitlines():
        if line.startswith(('Remv ', 'Purg ')):
            raise RuntimeError('candidate installation would remove packages')
        # APT can also finish a previously interrupted, unrelated package
        # without installing it again. Its maintainer scripts are still a
        # package mutation, so validate Conf entries as well as Inst entries.
        if line.startswith(('Inst ', 'Conf ')):
            name = line.split()[1].split(':')[0]
            if name not in allowed:
                raise RuntimeError(f'candidate installation changes unrelated package: {name}')
            if line.startswith('Inst '):
                changed.add(name)
    return changed


def install_preserving_marks(base, selected):
    automatic = sorted(set(subprocess.check_output(['apt-mark', 'showauto'], text=True).splitlines()) & set(selected))
    try:
        subprocess.run([base[0], '-y', *base[1:]], check=True)
    finally:
        # Explicit local-file APT arguments otherwise turn dependency packages
        # into manual installs, changing the user's later autoremove behavior.
        if automatic:
            subprocess.run(['apt-mark', 'auto', *automatic], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--retained', action='store_true', help='Keep newer installed security packages')
    args = parser.parse_args()
    paths = runtime_paths(args.directory.resolve())
    selected = dict(zip(PACKAGES, paths))
    # Coordinate optional development/back-end packages already installed from
    # the audited sources instead of removing them to satisfy dependencies.
    for path in args.directory.resolve().glob('*.deb'):
        name = subprocess.check_output(['dpkg-deb', '-f', str(path), 'Package'], text=True).strip()
        current = subprocess.run(['dpkg-query', '-W', '-f=${Status}', name], capture_output=True, text=True)
        if current.returncode == 0 and current.stdout == 'install ok installed':
            selected[name] = str(path)
    paths = list(selected.values())
    # Fail rather than roll back a newer Debian security revision to our build.
    for name in selected:
        current = subprocess.run(['dpkg-query', '-W', '-f=${Version}', name],
                                 text=True, capture_output=True)
        wanted = subprocess.check_output(['dpkg-deb', '-f', selected[name], 'Version'], text=True).strip()
        if current.returncode == 0 and current.stdout.strip():
            if subprocess.run(['dpkg', '--compare-versions', current.stdout.strip(),
                               'gt', wanted]).returncode == 0:
                if args.retained:
                    print(f'Keeping newer installed packages ({name}); shared Trash remains gated by runtime compatibility.')
                    return
                raise RuntimeError(f'{name} is newer than the candidate; rebase the patch')
    # The Docker RUN has network=none. APT's --no-download breaks its local
    # file acquisition here ("Pathname to install is not absolute"). Let APT
    # acquire the explicit local files; the namespace prevents network access.
    base = ['apt-get', '--no-remove', '--no-install-recommends', 'install', *paths]
    plan = subprocess.check_output([base[0], '--simulate', *base[1:]], text=True)
    print(plan, flush=True)
    validate_plan(plan, selected)
    install_preserving_marks(base, selected)
    for name in selected:
        wanted = subprocess.check_output(['dpkg-deb', '-f', selected[name], 'Version'], text=True).strip()
        actual = subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', name], text=True)
        if actual != wanted:
            raise RuntimeError(f'{name} candidate not installed')
    if subprocess.check_output(['dpkg', '--audit'], text=True).strip():
        raise RuntimeError('package database audit failed')


if __name__ == '__main__':
    main()
