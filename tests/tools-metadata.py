#!/usr/bin/python3
"""Tools metadata is idempotent and leaves unrelated or custom content alone."""
import runpy
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

update = runpy.run_path('payload/bin/rocknix-tools-metadata')['update']
release_date = runpy.run_path('payload/bin/rocknix-tools-metadata')['release_date']
artwork = Path('payload/integration/desktop-mode.svg')
with tempfile.TemporaryDirectory() as temp:
    modules = Path(temp)
    xml = modules / 'gamelist.xml'
    original = '<gameList><!--keep--><game><path>./other.sh</path><name>Other</name></game></gameList>'
    xml.write_text(original)
    update(modules, artwork)
    first = xml.read_bytes()
    update(modules, artwork)
    assert xml.read_bytes() == first
    assert b'<!--keep-->' in first
    assert len(ET.parse(xml).findall('game')) == 2
    assert (modules / 'images/rocknix-desktop.svg').read_bytes() == artwork.read_bytes()
    update(modules, artwork, remove=True)
    assert len(ET.parse(xml).findall('game')) == 1
    assert not (modules / 'images/rocknix-desktop.svg').exists()
    build = modules / 'build-info'
    release = modules / 'release-info.json'
    build.write_text('commit=installed-revision\nbuilt=2026-09-27T01:00:00Z\n')
    release.write_text('{"commit":"installed-revision","released_at":"2026-09-28T14:18:54Z"}')
    date = release_date(build, release)
    assert date == '20260928T141854'
    update(modules, artwork, releasedate=date)
    assert ET.parse(xml).findtext('game/releasedate') == date
    build.write_text('commit=other-revision\n')
    assert release_date(build, release) is None
    release.write_text('{"commit":"other-revision","released_at":"invalid"}')
    assert release_date(build, release) is None
    update(modules, artwork, remove=True)
    for content in ('<broken', '<gameList><game><path>./Desktop Mode.sh</path><name>Custom</name></game></gameList>'):
        xml.write_text(content)
        try:
            update(modules, artwork)
        except (ValueError, ET.ParseError):
            pass
        else:
            raise AssertionError('unsafe metadata accepted')
        assert xml.read_text() == content
    xml.unlink()
    target = modules / 'personal.xml'
    target.write_text(original)
    xml.symlink_to(target)
    try:
        update(modules, artwork)
    except ValueError:
        pass
    else:
        raise AssertionError('symlink accepted')
    assert target.read_text() == original
    xml.unlink()
    raw_entry = '<game><path>./stock.sh</path><desc>iOS 2 & 3</desc></game>'
    xml.write_text('<gameList>' + raw_entry + '</gameList>')
    update(modules, artwork)
    assert raw_entry in xml.read_text()
    update(modules, artwork, remove=True)
    assert xml.read_text() == '<gameList>' + raw_entry + '</gameList>'
    xml.write_text('<?xml version="1.0"?><gameList />')
    update(modules, artwork)
    assert len(ET.parse(xml).findall('game')) == 1
print('PASS: Tools artwork install/remove, idempotency, custom metadata and symlink protection')
