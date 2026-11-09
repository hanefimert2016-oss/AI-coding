"""Regression: OpenCode project home is outside /tmp and the OS scratch root isn't scanned."""
import importlib.util
from pathlib import Path
import os
import sqlite3
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
helper_path = root / "scripts" / "opencode-project-files.py"
spec = importlib.util.spec_from_file_location("oc_project_paths", helper_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix="oc-default-location-") as base_name:
    base = Path(base_name)
    home = base / "home"
    repo = base / "repo"
    scratch = base / "runner-scratch"
    old_tmp = base / "legacy-tmp"
    cloud = repo / "cloud-workspace"
    projects = home / "opencode-projects"
    unusual = old_tmp / "registered-open-code-project"
    for path in (home, repo, scratch, old_tmp, cloud, projects, unusual):
        path.mkdir(parents=True, exist_ok=True)
    (projects / "new-app.py").write_text("print('project preserved')")
    (unusual / "existing-project.py").write_text("print('older project preserved')")
    db = home / ".local/share/opencode/opencode.db"
    db.parent.mkdir(parents=True)
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE session_v2(directory TEXT)")
        conn.execute("INSERT INTO session_v2 VALUES(?)", (str(unusual),))

    base_env = {
        "HOME": str(home),
        "GITHUB_WORKSPACE": str(repo),
        "RUNNER_TEMP": str(scratch),
        "OPENCODE_BACKUP_HOME": str(home),
        "OPENCODE_BACKUP_REPOSITORY": str(repo),
        "OPENCODE_BACKUP_MNTDATA": str(base / "not-mounted"),
        "OPENCODE_BACKUP_WORKSPACE": str(base / "not-workspace"),
        "OPENCODE_BACKUP_WORKSPACES": str(base / "not-workspaces"),
        "OPENCODE_BACKUP_OPTPROJECTS": str(base / "not-opt"),
    }
    env_without_tmp = dict(os.environ, **base_env)
    env_without_tmp.pop("OPENCODE_BACKUP_TMP", None)
    with patch.dict(os.environ, env_without_tmp, clear=True), patch("pathlib.Path.home", return_value=home):
        locations = module.paths()
        assert "home" in locations and locations["home"] == str(home)
        assert "tmp" not in locations, "System /tmp must not be scanned by default"
        assert str(unusual) in locations.values(), "OpenCode-registered temp projects must remain backed up"

    env_with_explicit_tmp = dict(base_env, OPENCODE_BACKUP_TMP=str(old_tmp))
    with patch.dict(os.environ, env_with_explicit_tmp, clear=True), patch("pathlib.Path.home", return_value=home):
        locations = module.paths()
        assert locations["tmp"] == str(old_tmp), "Explicit legacy temp root must remain supported"

    server = (root / "scripts" / "opencode-remote-session.sh").read_text()
    assert 'projects_home="$HOME/opencode-projects"' in server, "Missing dedicated user projects dir"
    assert 'cd "$projects_home"' in server, "OpenCode must open in dedicated project folder"
    assert 'export TMPDIR="$RUNNER_TEMP/opencode-scratch"' in server, "Runner temp must be isolated"
    assert 'mkdir -p "$TMPDIR" "$projects_home"' in server, "Missing creation of safe directories"
print("PASS: /home/runner/opencode-projects default, isolated scratch, registered legacy temp projects")
