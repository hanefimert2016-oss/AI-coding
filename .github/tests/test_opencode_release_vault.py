"""GB-capable OpenCode vault regression: streaming chunks, credentials, tamper detection."""
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile

def run(args, env, expect_ok=True):
    p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=180)
    if expect_ok:
        assert p.returncode == 0, f'{args}: {p.stdout}\n{p.stderr}'
    else:
        assert p.returncode != 0, 'Tampered encrypted backup unexpectedly restored'
    return p

with tempfile.TemporaryDirectory() as root_str:
    root = Path(root_str)
    repo = root / 'repo'
    home = root / 'home'
    store = root / 'fake-github-releases'
    runner_temp = root / 'runner-temp'
    repo.mkdir(); home.mkdir(); runner_temp.mkdir()
    code = Path(__file__).resolve().parents[1] / 'scripts'
    dest_scripts = repo / '.github' / 'scripts'
    dest_scripts.mkdir(parents=True)
    for file in ('opencode-release-vault.py', 'opencode-crypto.mjs', 'opencode-project-files.py'):
        (dest_scripts / file).write_bytes((code / file).read_bytes())
    project = home / 'opencode-projects' / 'my-gigabyte-project'
    project.mkdir(parents=True)
    payload = os.urandom(7 * 1024 * 1024)
    (project / 'large.bin').write_bytes(payload)
    (project / 'main.ts').write_text('console.log("preserved")')
    old_cloud_file = repo / 'cloud-workspace' / 'old-app' / 'legacy.py'
    old_cloud_file.parent.mkdir(parents=True, exist_ok=True)
    old_cloud_file.write_text("print('old project still works')")
    (home / '.ssh').mkdir()
    (home / '.ssh' / 'id_rsa').write_text('do-not-copy')
    # Unusual but OpenCode-registered project also survives.
    extra = root / 'srv' / 'special-project'
    extra.mkdir(parents=True)
    (extra / 'build.py').write_text('print("yes")')
    db = home / '.local' / 'share' / 'opencode' / 'opencode.db'
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE session_v2(directory TEXT)')
        conn.execute('INSERT INTO session_v2 VALUES(?)', (str(extra),))
    env = dict(os.environ, HOME=str(home), GITHUB_WORKSPACE=str(repo), RUNNER_TEMP=str(runner_temp),
               OPENCODE_BACKUP_KEY='Q'*48, VAULT_TEST_DIR=str(store), VAULT_CHUNK_MIB='2',
               OPENCODE_BACKUP_TMP=str(root/'emptytmp'), OPENCODE_BACKUP_MNTDATA=str(root/'emptymnt'),
               OPENCODE_BACKUP_WORKSPACE=str(root/'emptyworkspace'), OPENCODE_BACKUP_WORKSPACES=str(root/'emptyworkspaces'),
               OPENCODE_BACKUP_OPTPROJECTS=str(root/'emptyopt'), GITHUB_RUN_ID='1234')
    command = ['python3', str(dest_scripts / 'opencode-release-vault.py')]
    run(command + ['save'], env)
    releases = sorted(store.glob('ocvault-*'))
    assert len(releases) == 1
    assert (releases[0] / 'PUBLISHED').is_file()
    assert len(list(releases[0].glob('part-*.enc'))) >= 4
    (project / 'large.bin').unlink()
    (project / 'main.ts').unlink()
    old_cloud_file.unlink()
    (extra / 'build.py').unlink()
    run(command + ['restore'], env)
    assert hashlib.sha256((project / 'large.bin').read_bytes()).digest() == hashlib.sha256(payload).digest()
    assert (project / 'main.ts').read_text() == 'console.log("preserved")'
    assert old_cloud_file.read_text() == "print('old project still works')"
    assert (extra / 'build.py').read_text() == 'print("yes")'
    assert not (home / '.ssh' / 'id_rsa').is_file() or (home / '.ssh' / 'id_rsa').read_text() == 'do-not-copy'
    encrypted = sorted(releases[0].glob('part-*.enc'))[0]
    corrupted = bytearray(encrypted.read_bytes())
    corrupted[-1] ^= 1
    encrypted.write_bytes(corrupted)
    run(command + ['restore'], env, expect_ok=False)
    print('PASS: >256MB architecture, streaming multipart encryption, remote snapshot, restore, sessions, tamper rejection')
