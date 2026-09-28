#!/usr/bin/python3
"""Verify and remove only exact fixtures from check-shared-data.sh on RP6."""
from pathlib import Path
import stat

manifest = Path('/storage/.local/share/rocknix-xfce/home/.cache/rocknix-shared-check.paths')
paths = [Path(line) for line in manifest.read_text().splitlines()]
parents = {Path('/storage') / name for name in ('Desktop', 'Steam', 'backup', 'games-external', 'games-internal', 'roms')}
assert len(paths) == 6 and {path.parent for path in paths} == parents
expected = b'non-root create\nnon-root edit\n'
# Validate ALL fixtures before deleting any of them.
for path in paths:
    assert path.name.startswith('.rocknix-bwrap-check.') and not path.is_symlink()
    assert stat.S_ISDIR(path.lstat().st_mode) and path.stat().st_uid == 0
    assert [child.name for child in path.iterdir()] == ['renamed']
    item = path / 'renamed'
    info = item.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1
    assert item.read_bytes() == expected
    print(f'PASS: host sees UID 0 and correct file contents for {path.parent}', flush=True)
for path in paths:
    (path / 'renamed').unlink()
    path.rmdir()
manifest.unlink()
print('PASS: all six exact disposable fixtures removed; existing shared data untouched')
