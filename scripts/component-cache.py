#!/usr/bin/python3
"""Stage finished archives for independent, disposable Actions cache entries."""
import argparse
import json
import os
from pathlib import Path
import runpy
import shutil

PROJECT = Path(__file__).resolve().parents[1]
B = runpy.run_path(str(PROJECT / 'scripts/build-components.py'))
C = B['C']


def transfer(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    try:
        os.link(source, target)
    except OSError:
        shutil.copyfile(source, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('keys', 'restore', 'stage'))
    parser.add_argument('--cache', type=Path, default=PROJECT / 'build/actions-cache')
    parser.add_argument('--store', type=Path, default=PROJECT / 'build/component-store')
    args = parser.parse_args()
    keys, _ = B['input_keys']()
    if args.action == 'keys':
        print(json.dumps(keys, indent=2))
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
                for role, key in keys.items():
                    stream.write(f'{role}={key}\n')
        return
    for role, key in keys.items():
        directory = args.cache / role
        source, target = (directory, args.store) if args.action == 'restore' else (args.store, directory)
        store = B['Store'](source)
        spec = store.find(role, key)
        if spec is None:
            if args.action == 'stage':
                raise RuntimeError('built archive missing: ' + role)
            continue
        # Each exact-key entry holds just its binding and compressed archive.
        for name in (spec['asset'], f'{role}-{key}.json'):
            transfer(source / name, target / name)


if __name__ == '__main__':
    main()
