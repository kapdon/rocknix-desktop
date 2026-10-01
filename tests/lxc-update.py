#!/usr/bin/python3
"""Guest update preserves packages, profiles, local edits and fail-closed paths."""
import io
import json
from pathlib import Path
import runpy
import tarfile
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
api = runpy.run_path(str(PROJECT / 'rootfs-overlay/usr/local/bin/rocknix-container-update'))
pack = runpy.run_path(str(PROJECT / 'scripts/package-integration.py'))


def write(root, name, data, mode=0o644):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)
    path.chmod(mode)
    return path


def rejects(root, archive):
    try:
        api['apply'](root, archive)
    except RuntimeError:
        return
    raise AssertionError('unsafe update accepted')


with tempfile.TemporaryDirectory() as temp:
    work = Path(temp)
    source, guest = work / 'source', work / 'guest'
    config = 'etc/xdg/waybar/style.css'
    binary = 'usr/local/bin/rocknix-launcher'
    obsolete = 'usr/local/bin/rocknix-old'
    write(source, config, 'v1')
    write(source, binary, 'v1', 0o755)
    write(source, obsolete, 'old', 0o755)
    write(source, 'etc/rocknix-desktop-build-info', 'commit=one')
    write(source, 'opt/ffmpeg-rpi-7.1.5/lib/real.so', 'library')
    (source / 'opt/ffmpeg-rpi-7.1.5/lib/link.so').symlink_to('real.so')
    write(source, 'opt/rocknix-fuzzel/bin/fuzzel', 'upstream launcher', 0o755)
    write(source, 'opt/rocknix-fuzzel/lib/libpixman-1.so.0.46.4', 'private pixman')
    (source / 'opt/rocknix-fuzzel/lib/libpixman-1.so.0').symlink_to('libpixman-1.so.0.46.4')
    # Ensure the packager cannot scoop up application packages/home data.
    write(source, 'var/lib/dpkg/status', 'not managed')
    write(source, 'home/rocknix/profile', 'not managed')
    archive = work / 'integration.tar.gz'
    pack['build'](source, archive)
    write(guest, config, 'local previous config')
    app = write(guest, 'opt/vesktop/client', 'installed app')
    db = write(guest, 'var/lib/dpkg/status', 'installed package database')
    profile = write(guest, 'home/rocknix/profile', 'existing profile')
    assert api['apply'](guest, archive) == [config]
    assert (guest / config).read_text() == 'local previous config'
    assert (guest / (config + '.rocknix-new')).read_text() == 'v1'
    assert (guest / binary).read_text() == 'v1'
    assert (guest / 'opt/ffmpeg-rpi-7.1.5/lib/link.so').read_text() == 'library'
    assert (guest / 'opt/rocknix-fuzzel/bin/fuzzel').read_text() == 'upstream launcher'
    assert (guest / 'opt/rocknix-fuzzel/lib/libpixman-1.so.0').read_text() == 'private pixman'
    # Accept the shipped config, then a normal update replaces it.
    (guest / (config + '.rocknix-new')).replace(guest / config)
    write(source, config, 'v2')
    write(source, binary, 'v2', 0o755)
    (source / obsolete).unlink()
    pack['build'](source, archive)
    assert not api['apply'](guest, archive)
    assert (guest / config).read_text() == 'v2'
    assert not (guest / obsolete).exists()
    # Interrupted application: one file already matches v3, manifest still v2.
    write(source, config, 'v3')
    write(source, binary, 'v3', 0o755)
    pack['build'](source, archive)
    write(guest, binary, 'v3', 0o755)
    assert not api['apply'](guest, archive)
    assert not api['apply'](guest, archive)
    # Local binary edits and symlink substitution are not followed/overwritten.
    write(guest, binary, 'user customization', 0o755)
    write(source, binary, 'v4', 0o755)
    pack['build'](source, archive)
    assert api['apply'](guest, archive) == [binary]
    assert (guest / binary).read_text() == 'user customization'
    assert app.read_text() == 'installed app'
    assert db.read_text() == 'installed package database'
    assert profile.read_text() == 'existing profile'
    outside = work / 'outside'
    outside.mkdir()
    (guest / 'etc/xdg/waybar').rename(guest / 'etc/xdg/waybar-saved')
    (guest / 'etc/xdg/waybar').symlink_to(outside, target_is_directory=True)
    rejects(guest, archive)
    assert not list(outside.iterdir())
    (guest / 'etc/xdg/waybar').unlink()
    (guest / 'etc/xdg/waybar-saved').rename(guest / 'etc/xdg/waybar')
    for name, kind in [('etc/shadow', tarfile.REGTYPE),
                       ('usr/local/bin/rocknix-bad', tarfile.LNKTYPE),
                       ('../etc/shadow', tarfile.REGTYPE)]:
        bad = work / 'bad.tar'
        with tarfile.open(bad, 'w') as tar:
            item = tarfile.TarInfo(name)
            item.type, item.linkname = kind, '/etc/shadow'
            tar.addfile(item)
            data = json.dumps({'format': 1, 'files': {name: {}}}).encode()
            meta = tarfile.TarInfo('manifest.json')
            meta.size = len(data)
            tar.addfile(meta, io.BytesIO(data))
        rejects(guest, bad)
    # A tampered later member must fail before an earlier valid file changes.
    bad = work / 'tampered.tar'
    with tarfile.open(archive) as original, tarfile.open(bad, 'w') as tar:
        for member in original.getmembers():
            content = original.extractfile(member).read() if member.isfile() else None
            if member.name == binary:
                content = b'tampered'
                member.size = len(content)
            tar.addfile(member, io.BytesIO(content) if content is not None else None)
    before = (guest / binary).read_text()
    rejects(guest, bad)
    assert (guest / binary).read_text() == before
    # The public CLI must reject native host root and ordinary users alike.
    try:
        api['require_container']()
    except RuntimeError:
        pass
    else:
        raise AssertionError('host accepted as mapped guest')
print('PASS: integration updates preserve apps/profiles/config edits and reject unsafe paths')
