#!/usr/bin/python3
"""Validate active user documentation without treating historical reports as current."""
from pathlib import Path
import re

paths = [Path('README.md'), Path('contributor.md'), *Path('docs').glob('*.md')]
for path in paths:
    text = path.read_text()
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' in target or target.startswith('#'):
            continue
        target = target.split('#', 1)[0]
        assert (path.parent / target).exists(), (path, target)

readme = Path('README.md').read_text()
assert 'navigation and the full terminal layout' not in readme
assert 'does not replace the native ROCKNIX keyboard' in readme
assert '(cd dist && sha256sum -c rocknix-sway-rp6-arm64.tar.xz.sha256)' in readme
print('PASS: active documentation links, Desktop-only keyboard and checksum instructions')
