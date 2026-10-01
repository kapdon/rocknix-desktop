#!/usr/bin/env python3
"""Temporary guest-only persistence fixture: setup, update externally, verify, cleanup.

Run on the reserved RP6 with Desktop active. Does not alter the desktop user's
password or keep recovery copies. Cleanup verifies fixture identity first.
"""
import argparse
from pathlib import Path
import runpy

GUEST = r'''
import hashlib,json,os,pwd,grp,secrets,stat,subprocess
from pathlib import Path
assert os.getuid()==0
assert Path('/proc/self/uid_map').read_text().split()==['0','200000','65536']
base=Path('/var/lib/rocknix-update-ownership-probe')
homefile=Path('/home/rocknix/.rocknix-update-ownership-probe')
user='rd-update-user'
service='rd-update-service'
accounts=[Path('/etc')/name for name in ('passwd','shadow','group','gshadow','subuid','subgid')]
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def account_hashes():
    return {str(p):digest(p) for p in accounts}
def run(*args,**kw):
    return subprocess.run(args,check=True,text=True,capture_output=True,**kw)
def fingerprint(p):
    s=p.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
    return [s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),digest(p)]
def identities():
    for name,number in ((user,2055),(service,2056)):
        entry=pwd.getpwnam(name)
        assert (entry.pw_uid,entry.pw_gid)==(number,number)
        assert grp.getgrnam(name).gr_gid==number
if phase=='setup':
    assert not os.path.lexists(base) and not os.path.lexists(homefile)
    for name,number in ((user,2055),(service,2056)):
        for lookup,key in ((pwd.getpwnam,name),(grp.getgrnam,name),
                           (pwd.getpwuid,number),(grp.getgrgid,number)):
            try: lookup(key)
            except KeyError: pass
            else: raise RuntimeError('Fixture account/identity already exists')
    before=account_hashes()
    base.mkdir(mode=0o700)
    # Record only hashes, never password/account recovery copies.
    (base/'before.json').write_text(json.dumps(before))
    for name,number in ((user,2055),(service,2056)):
        run('/usr/sbin/groupadd','--gid',str(number),name)
        run('/usr/sbin/useradd','--no-log-init','--no-create-home','--uid',str(number),
            '--gid',str(number),'--shell','/usr/sbin/nologin',name)
    run('/usr/sbin/chpasswd',input=user+':'+secrets.token_urlsafe(24)+'\n')
    first=digest(Path('/etc/shadow'))
    run('/usr/sbin/chpasswd',input=user+':'+secrets.token_urlsafe(24)+'\n')
    assert digest(Path('/etc/shadow'))!=first
    files={}
    for path,owner in ((base/'user-owned',2055),(base/'service-owned',2056),(homefile,0)):
        with path.open('x') as stream: stream.write('ROCKNIX update ownership fixture\n')
        path.chmod(0o600)
        os.chown(path,owner,owner)
        files[str(path)]=fingerprint(path)
    (base/'expected.json').write_text(json.dumps({'accounts':account_hashes(),'files':files}))
    print('PASS: temporary accounts, changed test password and mixed-owner files created')
else:
    assert base.is_dir() and not base.is_symlink() and base.stat().st_uid==0
    identities()
    expected=json.loads((base/'expected.json').read_text())
    assert account_hashes()==expected['accounts'],'account/password data changed'
    for name,value in expected['files'].items():
        assert fingerprint(Path(name))==value,(name,'owner/mode/content changed')
    assert set(expected['files'])=={str(base/'user-owned'),str(base/'service-owned'),str(homefile)}
    print('PASS: extra user, changed password, service owner and root-owned home file preserved')
    if phase=='cleanup':
        before=json.loads((base/'before.json').read_text())
        for name in (user,service):
            run('/usr/sbin/userdel',name)
            # Debian may remove the matching private group with userdel.
            try: grp.getgrnam(name)
            except KeyError: pass
            else: run('/usr/sbin/groupdel',name)
        assert account_hashes()==before,'account cleanup did not restore original hashes'
        for name in expected['files']: Path(name).unlink()
        (base/'expected.json').unlink()
        (base/'before.json').unlink()
        base.rmdir()
        print('PASS: only test accounts/files removed; original account hashes restored')
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['setup', 'verify', 'cleanup'])
    args = parser.parse_args()
    base = Path('/storage/rocknix-desktop/managed/host')
    runtime = runpy.run_path(str(base / 'bin/rocknix-lxc'))['Runtime'](
        base / 'host-tools', Path('/storage/rocknix-desktop/data/rootfs'))
    result = runtime.attach('/usr/bin/python3', '-', input='phase='+repr(args.phase)+'\n'+GUEST)
    print(result.stdout, result.stderr, flush=True)
    assert result.returncode == 0
    # Attach only: never close the active Desktop's runtime.

if __name__ == '__main__':
    main()
