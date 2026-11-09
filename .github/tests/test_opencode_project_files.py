"""Local project save/restore regression test; no external credentials are used."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1] / 'scripts'
spec = importlib.util.spec_from_file_location('opencode_project_files', BASE / 'opencode-project-files.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as root_path:
    root = Path(root_path)
    home, repo = root / 'home', root / 'repo'
    home.mkdir()
    repo.mkdir()
    locations = {
        'OPENCODE_BACKUP_HOME': home,
        'OPENCODE_BACKUP_REPOSITORY': repo,
        'OPENCODE_BACKUP_TMP': root / 'tmp',
        'OPENCODE_BACKUP_MNTDATA': root / 'mnt',
        'OPENCODE_BACKUP_WORKSPACE': root / 'workspace',
        'OPENCODE_BACKUP_WORKSPACES': root / 'workspaces',
        'OPENCODE_BACKUP_OPTPROJECTS': root / 'optprojects',
    }
    files = {k: v / 'a-project' / 'src' / 'app.js' for k, v in locations.items()}
    for name, file in files.items():
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('project-' + name)
    extra = home / 'work' / 'another-app' / 'module.py'
    extra.parent.mkdir(parents=True)
    extra.write_text('print(123)')
    secret = home / '.ssh' / 'id_rsa'
    secret.parent.mkdir()
    secret.write_text('test-private-key')
    unusual = root / 'srv' / 'custom-project'
    unusual.mkdir(parents=True)
    (unusual / 'app.go').write_text('package main')
    db = home / '.local' / 'share' / 'opencode' / 'opencode.db'
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as connection:
        connection.execute('CREATE TABLE session_v2(directory TEXT)')
        connection.execute('INSERT INTO session_v2 VALUES (?)', (str(unusual),))
    environ = {k: str(v) for k, v in locations.items()}
    environ.update(HOME=str(home), GITHUB_WORKSPACE=str(repo))
    with patch.dict(os.environ, environ), patch('pathlib.Path.home', return_value=home):
        dest = root / 'archive'
        module.save(dest)
        assert not (dest / 'home' / '.ssh' / 'id_rsa').exists()
        unusual_name = 'session-' + hashlib.sha256(str(unusual).encode()).hexdigest()[:24]
        assert (dest / unusual_name / 'app.go').is_file()
        for file in files.values():
            file.unlink()
        extra.unlink()
        (unusual / 'app.go').unlink()
        module.restore(dest)
        for name, file in files.items():
            assert file.read_text() == 'project-' + name, name
        assert extra.read_text() == 'print(123)'
        assert (unusual / 'app.go').read_text() == 'package main'
print('PASS: directories from home, repo, temporary/mounted paths and OpenCode sessions')
