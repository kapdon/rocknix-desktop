#!/usr/bin/python3
"""Verify real Firefox V4L2 decoding from RP6 logs and the live RDD process.

Launch Firefox through Apps with MOZ_LOG=PlatformDecoderModule:5,FFmpegVideo:5
and MOZ_LOG_FILE=/home/rocknix/.cache/rocknix-decoder-detail.log, then play the
existing H.264 fixture. Run this on the host while video is still playing.
Does not launch Firefox, alter preferences or disable browser sandboxes.
"""
from pathlib import Path
import os
import re

cache = Path('/storage/.local/share/rocknix-xfce/home/.cache')
logs = list(cache.glob('rocknix-decoder-detail.log*.moz_log'))
assert logs, 'no Firefox diagnostic logs'
text = '\n'.join(path.read_text() for path in logs)
assert 'V4L2 codec h264_v4l2m2m' in text
assert 'V4L2 FFmpeg init successful' in text
frames = re.findall(r'V4L2 Got one frame output with pts=(\d+)', text)
assert len(frames) >= 30, len(frames)
rdds = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal():
        continue
    try:
        if (proc / 'comm').read_text().strip() != 'RDD Process':
            continue
        if 'xfce-desktop.service' not in (proc / 'cgroup').read_text():
            continue
        status = dict(line.split(':', 1) for line in (proc / 'status').read_text().splitlines() if ':' in line)
        namespace_pid = status['NSpid'].split()[-1]
        if f'[RDD {namespace_pid}:' not in text:
            continue
        assert status['Uid'].split() == ['62000'] * 4
        assert int(status['CapEff'], 16) == 0
        assert status['NoNewPrivs'].strip() == '1' and status['Seccomp'].strip() == '2'
        targets = [os.readlink(fd) for fd in (proc / 'fd').iterdir()]
        assert '/dev/video0' in targets, 'RDD has no active decoder device'
        assert '/opt/ffmpeg-rpi-7.1.5/lib/libavcodec.so.61' in (proc / 'maps').read_text()
        rdds.append(proc.name)
    except (FileNotFoundError, ProcessLookupError):
        continue
assert len(rdds) == 1, rdds
assert Path('/sys/class/video4linux/video0/name').read_text().strip() == 'qcom-iris-decoder'
print(f'PASS: Firefox RDD host PID {rdds[0]} uses Iris via h264_v4l2m2m; '
      f'{len(frames)} logged hardware frames, latest PTS {max(map(int, frames))}; '
      'UID 62000, zero capabilities, NNP and seccomp enabled')
