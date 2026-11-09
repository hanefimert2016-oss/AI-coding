"""End-to-end encrypted multi-part backup test against a temporary local Git remote."""
from pathlib import Path
import os
import shutil
import sqlite3
import subprocess
import tempfile

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'

def run(*args, env=None):
    p = subprocess.run(args, env=env, capture_output=True, text=True)
    if p.returncode:
        raise AssertionError(f'Command failed (exit {p.returncode}): {args}\n{p.stdout}\n{p.stderr}')
    return p

with tempfile.TemporaryDirectory() as root_str:
    root = Path(root_str)
    repo = root / 'repo'
    remote = root / 'remote.git'
    home = root / 'home'
    tmp = root / 'runner-temp'
    for path in (repo, home, tmp):
        path.mkdir()
    run('git', 'init', '--bare', str(remote))
    run('git', 'init', '-b', 'main', str(repo))
    run('git', '-C', str(repo), 'config', 'user.name', 'OpenCode Test')
    run('git', '-C', str(repo), 'config', 'user.email', 'test@example.invalid')
    script_dir = repo / '.github' / 'scripts'
    script_dir.mkdir(parents=True)
    for name in ('opencode-backup.sh', 'opencode-crypto.mjs', 'opencode-project-files.py'):
        shutil.copy2(SCRIPTS / name, script_dir / name)
    run('git', '-C', str(repo), 'add', '.')
    run('git', '-C', str(repo), 'commit', '-m', 'fixture')
    run('git', '-C', str(repo), 'remote', 'add', 'origin', str(remote))
    run('git', '-C', str(repo), 'push', 'origin', 'main')
    run('git', '-C', str(repo), 'checkout', '-b', 'opencode-cloud-backups-20261109')
    run('git', '-C', str(repo), 'push', 'origin', 'opencode-cloud-backups-20261109')
    run('git', '-C', str(repo), 'checkout', 'main')

    temp_projects = root / 'temporary-projects'
    scratch = root / 'mntdata'
    srv = root / 'srv' / 'a-session'
    sources = {
        'workspace': repo / 'cloud-workspace' / 'index.html',
        'home': home / 'any-folder' / 'src' / 'app.ts',
        'repository': repo / 'other-project' / 'README.md',
        'temporary': temp_projects / 'created-here' / 'script.py',
        'mnt': scratch / 'assets' / 'project.txt',
        'session': srv / 'main.go',
    }
    for name, path in sources.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('project-' + name)
    # A 41 MiB incompressible fixture forces 2 encrypted chunks (each <= 40 MiB).
    large_file = home / 'any-folder' / 'asset.bin'
    large_file.write_bytes(os.urandom(41 * 1024 * 1024))
    (home / '.ssh').mkdir()
    (home / '.ssh' / 'id_rsa').write_text('Never save this private key')

    db = home / '.local/share/opencode/opencode.db'
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE session_v2(directory TEXT)')
        connection.execute('INSERT INTO session_v2 VALUES(?)', (str(srv),))
        connection.execute('CREATE TABLE messages(txt TEXT)')
        connection.execute('INSERT INTO messages VALUES(?)', ('old chat',))
    env = dict(os.environ, GITHUB_WORKSPACE=str(repo), HOME=str(home),
               RUNNER_TEMP=str(tmp), OPENCODE_BACKUP_KEY='I'*48,
               OPENCODE_BACKUP_HOME=str(home),
               OPENCODE_BACKUP_REPOSITORY=str(repo),
               OPENCODE_BACKUP_TMP=str(temp_projects),
               OPENCODE_BACKUP_MNTDATA=str(scratch),
               OPENCODE_BACKUP_WORKSPACE=str(root/'other-workspace'),
               OPENCODE_BACKUP_WORKSPACES=str(root/'other-workspaces'),
               OPENCODE_BACKUP_OPTPROJECTS=str(root/'optprojects'))
    backup_script = str(script_dir / 'opencode-backup.sh')
    run('bash', backup_script, 'prepare', env=env)
    run('bash', backup_script, 'save', env=env)
    checkpoint = tmp / 'opencode-backup-checkout' / '.opencode-cloud'
    assert (checkpoint / 'manifest.enc').is_file()
    assert (checkpoint / 'part-0000.enc').is_file()
    assert (checkpoint / 'part-0001.enc').is_file(), 'Multi-part split did not occur'
    assert not (checkpoint / 'latest.enc').exists()
    for path in sources.values():
        path.unlink()
    large_file.unlink()
    db.unlink()
    (home / '.ssh' / 'id_rsa').unlink()
    run('bash', backup_script, 'restore', env=env)
    for name, path in sources.items():
        assert path.read_text() == 'project-' + name, name
    assert large_file.stat().st_size == 41 * 1024 * 1024
    assert not (home / '.ssh' / 'id_rsa').exists()
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT txt FROM messages').fetchone()[0] == 'old chat'
    # GCM authentication must reject tampered encrypted chunks.
    part = checkpoint / 'part-0001.enc'
    altered = bytearray(part.read_bytes())
    altered[-1] ^= 1
    part.write_bytes(altered)
    p = subprocess.run(['bash', backup_script, 'restore'], env=env, capture_output=True)
    assert p.returncode != 0, 'Corrupted encrypted chunk was accepted'
    print('PASS: encrypted chunking, 6 project locations, SQLite history, Git push, restore, key exclusion and tamper rejection')
