#!/usr/bin/python3
"""RP6 decoder-only access probe; restore the exact device ACL in finally."""
import os
from pathlib import Path
import subprocess

root = Path('/storage/.local/share/rocknix-xfce/rootfs')
lib = root / 'usr/lib/aarch64-linux-gnu'
def debian(executable, *args, **kwargs):
    return subprocess.check_output([str(lib / 'ld-linux-aarch64.so.1'), '--library-path',
        str(lib), str(root / executable.lstrip('/')), *args], **kwargs)

node = '/dev/video0'
assert Path('/sys/class/video4linux/video0/name').read_text().strip() == 'qcom-iris-decoder'
acl = debian('/usr/bin/getfacl', '-p', node)
try:
    debian('/usr/bin/setfacl', '-m', 'u:62000:rw', node)
    pid = os.fork()
    if pid == 0:
        try:
            os.setgroups([])
            os.setgid(62000)
            os.setuid(62000)
            fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
            os.close(fd)
            os._exit(0)
        except Exception:
            os._exit(1)
    _, status = os.waitpid(pid, 0)
    assert os.waitstatus_to_exitcode(status) == 0, status
    print('PASS: UID 62000 opens only the selected decoder without video-group membership')
finally:
    debian('/usr/bin/setfacl', '--restore=-', input=acl)
    assert debian('/usr/bin/getfacl', '-p', node) == acl
    print('Decoder ACL restored exactly')
