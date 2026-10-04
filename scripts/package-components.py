#!/usr/bin/python3
"""Validate cached components and package the assembled system in CI."""
import argparse
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[1]
C = runpy.run_path(str(PROJECT / 'payload/bin/rocknix-components'))


def package(manifest, store, output):
    started = time.monotonic()
    value = C['release'](json.loads(manifest.read_text()))
    files = C['materialize'](value, store, 'kapdon/rocknix-desktop', 'install')
    with tempfile.TemporaryDirectory(prefix='assembled-release-', dir=output.parent) as scratch:
        system = Path(scratch) / 'system'
        C['assemble'](value, files, system, 'install')
        (system / 'release-info.json').write_bytes(C['encoded']({
            'commit': value['commit'], 'built_at': value['built_at']}))
        assembled = time.monotonic()
        # This process and tar share the caller's fakeroot session: archive
        # service owners, hardlinks and setuid modes survive CI's unprivileged UID.
        subprocess.run(['tar', '--sort=name', '--numeric-owner', '-I', 'xz -T0 -3',
                        '-cf', str(output), '-C', str(system), '.'], check=True)
        packed = time.monotonic()
    timing = {'validation_assembly_seconds': round(assembled - started, 3),
              'compression_seconds': round(packed - assembled, 3),
              'total_seconds': round(time.monotonic() - started, 3),
              'archive_bytes': output.stat().st_size}
    (manifest.parent / 'packaging-timings.json').write_bytes(C['encoded'](timing))
    print(json.dumps(timing), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--store', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    package(args.manifest, args.store, args.output)
