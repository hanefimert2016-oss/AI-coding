#!/usr/bin/env python3
"""Back up user-created project folders from common runner paths and OpenCode sessions."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

SKIP_ROOTS = ('/etc', '/usr', '/bin', '/sbin', '/lib', '/lib64', '/proc',
              '/sys', '/dev', '/root', '/run', '/var/lib', '/var/run')
EXCLUDES = (
    '.git/', 'node_modules/', '.venv/', 'venv/', '.next/', 'dist/',
    'build/', 'target/', '__pycache__/', '.cache/', '.npm/', '.rustup/',
    '.sdkman/', '.dotnet/', '.nvm/', '.ssh/', '.aws/', '.azure/', '.kube/',
    '.gnupg/', '.docker/', '_temp/', '_actions/', '_tool/', '*.sock', '*.socket',
    '.git-credentials', '.netrc',
)

def safe_path(value):
    path = Path(value)
    if not path.is_absolute() or str(path) == '/':
        return None
    resolved = path.resolve(strict=False)
    if str(resolved) == '/' or any(resolved == Path(p) or Path(p) in resolved.parents for p in SKIP_ROOTS):
        return None
    return path

def paths():
    home = Path.home()
    repo = Path(os.environ['GITHUB_WORKSPACE'])
    base = {
        'home': os.getenv('OPENCODE_BACKUP_HOME', str(home)),
        'repository': os.getenv('OPENCODE_BACKUP_REPOSITORY', str(repo)),
        'mntdata': os.getenv('OPENCODE_BACKUP_MNTDATA', '/mnt/data'),
        'workspace': os.getenv('OPENCODE_BACKUP_WORKSPACE', '/workspace'),
        'workspaces': os.getenv('OPENCODE_BACKUP_WORKSPACES', '/workspaces'),
        'optprojects': os.getenv('OPENCODE_BACKUP_OPTPROJECTS', '/opt/projects'),
    }
    # /tmp contains OS-owned and snap-private directories. Never traverse it by default.
    # A caller may explicitly opt in to a known temp root, while paths stored in
    # the OpenCode session DB will still be discovered individually below.
    requested_tmp_root = os.environ.get('OPENCODE_BACKUP_TMP')
    if requested_tmp_root:
        base['tmp'] = requested_tmp_root
    accepted = {}
    for name, location in base.items():
        root = safe_path(location)
        if root is not None and root.is_dir():
            accepted[name] = str(root)
    db = home / '.local/share/opencode/opencode.db'
    if db.is_file():
        try:
            with sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=8) as conn:
                for table in ('session_v2', 'session', 'project', 'project_directory', 'workspace', 'worktree'):
                    columns = {col[1] for col in conn.execute(f'PRAGMA table_info({table})')}
                    for field in ('directory', 'worktree', 'path'):
                        if field not in columns:
                            continue
                        for (value,) in conn.execute(f'SELECT DISTINCT "{field}" FROM "{table}"'):
                            if not isinstance(value, str) or '\n' in value:
                                continue
                            root = safe_path(value)
                            if root is None or not root.is_dir():
                                continue
                            if any(root == Path(basepath) or Path(basepath) in root.parents for basepath in accepted.values()):
                                continue
                            name = 'session-' + hashlib.sha256(str(root).encode()).hexdigest()[:24]
                            accepted[name] = str(root)
        except sqlite3.Error as exc:
            print(f'Warning: OpenCode directory discovery failed: {exc}', file=sys.stderr)
    return accepted

def rsync(source, dest, extra=()):
    dest.mkdir(parents=True, exist_ok=True)
    exclude = ['--exclude=' + item for item in EXCLUDES]
    exclude += ['--exclude=' + item for item in extra]
    subprocess.run(['rsync', '-a', *exclude, str(source) + '/', str(dest) + '/'], check=True)

def save(destination):
    destination.mkdir(parents=True, exist_ok=True)
    repo = Path(os.environ['GITHUB_WORKSPACE']).resolve()
    home = Path.home().resolve()
    entries = paths()
    for name, source in entries.items():
        additional = []
        if name == 'home':
            additional = ['/.config/opencode/', '/.local/share/opencode/', '/work/_temp/', '/work/_actions/', '/work/_tool/']
            if repo.is_relative_to(home):
                additional.append('/' + str(repo.relative_to(home)) + '/')
        elif name == 'repository':
            additional = ['/.github/', '/cloud-workspace/']
        elif name == 'tmp':
            additional = ['/opencode-save.*/', '/opencode-restore.*/', '/opencode-backup-checkout/',
                          '/tmp.*', '/systemd-private-*/']
        rsync(Path(source), destination / name, additional)
    (destination / 'root-map.json').write_text(json.dumps(entries, sort_keys=True), encoding='utf-8')
    print(f'Project backup roots: {len(entries)}')

def restore(destination):
    mapping = destination / 'root-map.json'
    if not mapping.is_file():
        print('Older checkpoint has no project directory manifest.')
        return
    entries = json.loads(mapping.read_text(encoding='utf-8'))
    if not isinstance(entries, dict) or len(entries) > 1000:
        raise ValueError('Invalid project root map')
    for name, location in entries.items():
        if not isinstance(name, str) or not isinstance(location, str) or name in ('.', '..') or '/' in name:
            raise ValueError('Invalid project root entry')
        target = safe_path(location)
        source = destination / name
        if target is None:
            raise ValueError(f'Unsafe project destination: {location}')
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            rsync(source, target)
    print(f'Project restore roots: {len(entries)}')

if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ('save', 'restore'):
        raise SystemExit('Usage: opencode-project-files.py save|restore DESTINATION')
    (save if sys.argv[1] == 'save' else restore)(Path(sys.argv[2]))
