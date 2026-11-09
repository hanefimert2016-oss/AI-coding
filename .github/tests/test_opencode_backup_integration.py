"""Test fast encrypted Git checkpoints for OpenCode chats and provider authentication."""
from pathlib import Path
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'

def run(*args, env=None):
    p = subprocess.run(args, env=env, capture_output=True, text=True, timeout=100)
    assert p.returncode == 0, f'{args}\n{p.stdout}\n{p.stderr}'
    return p

with tempfile.TemporaryDirectory() as root_str:
    root = Path(root_str)
    repo, remote, home, tmp = (root / name for name in ('repo', 'remote.git', 'home', 'runner-temp'))
    for p in (repo, home, tmp):
        p.mkdir()
    run('git', 'init', '--bare', str(remote))
    run('git', 'init', '-b', 'main', str(repo))
    run('git', '-C', str(repo), 'config', 'user.name', 'Backup Test')
    run('git', '-C', str(repo), 'config', 'user.email', 'test@example.invalid')
    scripts = repo / '.github' / 'scripts'
    scripts.mkdir(parents=True)
    for name in ('opencode-backup.sh', 'opencode-crypto.mjs', 'opencode-project-files.py'):
        shutil.copy2(SCRIPTS / name, scripts / name)
    run('git', '-C', str(repo), 'add', '.')
    run('git', '-C', str(repo), 'commit', '-m', 'test fixture')
    run('git', '-C', str(repo), 'remote', 'add', 'origin', str(remote))
    run('git', '-C', str(repo), 'push', 'origin', 'main')
    run('git', '-C', str(repo), 'checkout', '-b', 'opencode-cloud-backups-20261109')
    run('git', '-C', str(repo), 'push', 'origin', 'opencode-cloud-backups-20261109')
    run('git', '-C', str(repo), 'checkout', 'main')

    data = home / '.local/share/opencode'
    config = home / '.config/opencode'
    data.mkdir(parents=True)
    config.mkdir(parents=True)
    auth = data / 'auth.json'
    auth.write_text(json.dumps({'provider-example': {'type':'api','key':'private-provider-key'}}))
    prefs = config / 'opencode.json'
    prefs.write_text(json.dumps({'provider': {'provider-example': {'options': {'baseURL':'https://example.invalid/v1'}}}}))
    db = data / 'opencode.db'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE messages(txt TEXT)')
        con.execute('INSERT INTO messages VALUES(?)', ('previous OpenCode chat',))
        con.execute('CREATE TABLE provider_credentials(token TEXT)')
        con.execute('INSERT INTO provider_credentials VALUES(?)', ('oauth-refresh-token',))

    env = dict(os.environ, GITHUB_WORKSPACE=str(repo), HOME=str(home),
               RUNNER_TEMP=str(tmp), OPENCODE_BACKUP_KEY='I'*48)
    script = str(scripts / 'opencode-backup.sh')
    run('bash', script, 'prepare', env=env)
    run('bash', script, 'save', env=env)
    checkpoint = tmp / 'opencode-backup-checkout' / '.opencode-cloud'
    assert (checkpoint / 'manifest.enc').is_file()
    part = checkpoint / 'part-0000.enc'
    assert part.is_file()
    auth.unlink()
    prefs.unlink()
    db.unlink()
    run('bash', script, 'restore', env=env)
    assert json.loads(auth.read_text())['provider-example']['key'] == 'private-provider-key'
    assert json.loads(prefs.read_text())['provider']['provider-example']['options']['baseURL'].endswith('/v1')
    with sqlite3.connect(db) as con:
        assert con.execute('SELECT txt FROM messages').fetchone()[0] == 'previous OpenCode chat'
        assert con.execute('SELECT token FROM provider_credentials').fetchone()[0] == 'oauth-refresh-token'
    corrupted = bytearray(part.read_bytes())
    corrupted[-1] ^= 1
    part.write_bytes(corrupted)
    p = subprocess.run(['bash', script, 'restore'], env=env, capture_output=True)
    assert p.returncode != 0, 'Tampered encrypted provider/auth checkpoint was accepted'
    print('PASS: encrypted OpenCode chats, legacy auth.json, provider SQLite tokens, config, Git push and tamper rejection')
