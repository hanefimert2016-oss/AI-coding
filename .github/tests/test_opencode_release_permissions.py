"""Regression: inaccessible system temporary dirs must not break project backups."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "scripts" / "opencode-release-vault.py"

def run(env, action):
    return subprocess.run(["python3", str(VAULT), action],
                          env=env, capture_output=True, text=True, timeout=120)

with tempfile.TemporaryDirectory(prefix="oc-permission-test-") as temp:
    base = Path(temp)
    home, repo, runner_tmp, release_store, tmp_project_root = [base / name for name in (
        "home", "repo", "runner-temp", "release-store", "temporary-projects")]
    for folder in (home, repo, runner_tmp, release_store, tmp_project_root):
        folder.mkdir()

    # This reproduces /tmp/snap-private-tmp on Ubuntu Actions (0o000 is unreadable
    # to ordinary runner users). Another inaccessible folder checks generic handling.
    protected = [tmp_project_root / name for name in (
        "snap-private-tmp", "permission-denied-fixture")]
    for folder in protected:
        folder.mkdir()
        folder.chmod(0)

    user_project = tmp_project_root / "my-project" / "src" / "main.py"
    user_project.parent.mkdir(parents=True)
    user_project.write_text("print('keep my project')\n")

    env = dict(os.environ,
        HOME=str(home), GITHUB_WORKSPACE=str(repo), RUNNER_TEMP=str(runner_tmp),
        VAULT_TEST_DIR=str(release_store), VAULT_CHUNK_MIB="1",
        GITHUB_RUN_ID="permission-regression",
        OPENCODE_BACKUP_KEY="U" * 48,
        OPENCODE_BACKUP_TMP=str(tmp_project_root),
        OPENCODE_BACKUP_HOME=str(home),
        OPENCODE_BACKUP_REPOSITORY=str(repo),
        OPENCODE_BACKUP_MNTDATA=str(base / "absentmnt"),
        OPENCODE_BACKUP_WORKSPACE=str(base / "absentwork"),
        OPENCODE_BACKUP_WORKSPACES=str(base / "absentworks"),
        OPENCODE_BACKUP_OPTPROJECTS=str(base / "absentopt"))
    try:
        result = run(env, "save")
        assert result.returncode == 0, (
            "Vault save failed with private temporary folders:\n"
            + result.stdout + result.stderr)
        assert list(release_store.glob("ocvault-*/PUBLISHED")), (
            "Encrypted Release snapshot was not published")
        user_project.unlink()
        result = run(env, "restore")
        assert result.returncode == 0, result.stdout + result.stderr
        assert user_project.read_text() == "print('keep my project')\n"
        print("PASS: private temp directories ignored, user project restored")
    finally:
        for folder in protected:
            folder.chmod(0o700)
