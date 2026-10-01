#!/usr/bin/python3
"""Create the guest-only update payload from an already exported build image."""
import argparse
import io
import json
from pathlib import Path
import runpy
import tarfile

PROJECT = Path(__file__).resolve().parents[1]
API = runpy.run_path(str(PROJECT / 'rootfs-overlay/usr/local/bin/rocknix-container-update'))


def build(root, output):
    files = {}
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if API['allowed'](name) and (path.is_file() or path.is_symlink()):
            files[name] = API['fingerprint'](path)
    manifest = {'format': 1, 'files': files}
    with tarfile.open(output, 'w:gz', dereference=False) as archive:
        for name in files:
            # Add hardlinked files independently; update archives never contain
            # hardlinks or device nodes and do not carry service ownership.
            archive.inodes.clear()
            info = archive.gettarinfo(str(root / name), arcname=name)
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            if info.isfile():
                with (root / name).open('rb') as stream:
                    archive.addfile(info, stream)
            else:
                archive.addfile(info)
        data = (json.dumps(manifest, sort_keys=True) + '\n').encode()
        info = tarfile.TarInfo('manifest.json')
        info.size, info.mode = len(data), 0o644
        archive.addfile(info, io.BytesIO(data))
    # Fresh installations start with the exact same managed-file baseline.
    state = root / API['STATE']
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_bytes(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rootfs', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build(args.rootfs, args.output)
