# OpenCode Cloud — encrypted automatic saves on GitHub Actions

OpenCode v2's official web UI runs on the PUBLIC hanefimert2016-oss/AI-coding repo, without modifying FalconOS or private Metodbox projects.

## First-time setup (Android supported)

In **AI-coding → Settings → Secrets and variables → Actions → New repository secret**, add two **different** secrets:

1. **OPENCODE_PASSWORD** — unique OpenCode server password (at least 20 characters).
2. **OPENCODE_BACKUP_KEY** — random 32+ character encryption key, different from the server password. Generate a strong 64-character key on your own device using: openssl rand -hex 32.

**Keep both secret. Losing or changing OPENCODE_BACKUP_KEY makes existing encrypted backups impossible to restore.** Never publish either secret in GitHub issues, code, logs, workflow inputs or chat.

## How it works

1. On [Actions → OpenCode Cloud - Official Web UI](https://github.com/hanefimert2016-oss/AI-coding/actions/workflows/opencode-cloud.yml), select Run workflow, branch main and a duration of 30 to 120 minutes.
2. GitHub Actions restores your last encrypted checkpoint **before** OpenCode starts.
3. In the OpenCode official UI, work inside the cloud-workspace/ folder.
4. The runner creates an initial encrypted checkpoint, then **saves every 2 minutes**, and attempts a final save when it ends normally.
5. Checkpoints are pushed into the PUBLIC branch [opencode-cloud-backups-20261109](https://github.com/hanefimert2016-oss/AI-coding/tree/opencode-cloud-backups-20261109). Only the AES-256-GCM-encrypted file is automatically committed.
6. On the next run, source files, OpenCode chat history, local settings and stored credentials are automatically decrypted and restored.

The backup captures cloud-workspace/, the application data directory (including OpenCode SQLite session database and snapshots), and OpenCode configuration. For a consistent live snapshot, the SQLite database is copied with SQLite's online backup API.

The following reinstallable/generated directories are excluded: node_modules/, .venv/, venv/, .next/, dist/, build/, target/, __pycache__/. OpenCode logs and the machine-specific service.json are excluded too. The maximum compressed checkpoint size is 90 MiB.

## Security and limitations

- Checkpoints are publicly downloadable as **encrypted ciphertext**. Only your high-entropy backup key makes their contents confidential.
- **Never commit plaintext private data to the public source branch.** Git history of encrypted snapshots grows with repeated checkpoints.
- If a checkpoint fails or a runner crashes, the previous successful save is retained. Up to approximately 2 minutes of edits can be lost during normal operation; more if saves fail.
- Manual cancellation may stop the runner before the final checkpoint finishes. The periodic saves reduce this risk but cannot eliminate it.
- GitHub Actions is a temporary CI runtime, not a guaranteed always-on hosting platform. A single GitHub-hosted job has an execution time limit.
- OpenCode's remote one-time pairing URL grants access and is intentionally **never** exposed in public logs. The workflow shows only the remote **base URL**. If password-only login through that address is not supported, secure private delivery of the pairing link is still required before the UI can be used.
- A free OpenCode interface does not guarantee unlimited free AI inference.

References: [OpenCode Web/Remote](https://opencode.ai/docs/cli/web/) · [OpenCode data](https://opencode.ai/docs/troubleshooting/) · [GitHub Actions limits](https://docs.github.com/en/actions/reference/limits).
