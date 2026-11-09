# OpenCode Cloud — encrypted chats, provider credentials and multi-GB projects

Runs the **official OpenCode v2 web UI** on the **public** hanefimert2016-oss/AI-coding repository. FalconOS is not touched.

## First-time setup (Android supported)

In [AI-coding Actions Secrets](https://github.com/hanefimert2016-oss/AI-coding/settings/secrets/actions), configure two different secrets:

1. **OPENCODE_PASSWORD:** a unique OpenCode server password of at least 20 characters.
2. **OPENCODE_BACKUP_KEY:** a different random encryption key with at least 32 characters. On your device, generate one by running openssl rand -hex 32.

**Run limits:** GitHub-hosted job timeout 355 minutes (5 hours 55 minutes); maximum OpenCode session 330 minutes (5.5 hours). The remaining 25 minutes are reserved for startup, shutdown and final encrypted backups. Large backups can still exceed this margin and may be interrupted. The public Actions runner itself cannot exceed GitHub's 360-minute hard limit.

The backup encryption key must stay unchanged to restore older backups. Never paste provider keys or passwords in a public commit, issue, log or workflow input.

Start [OpenCode Cloud Actions](https://github.com/hanefimert2016-oss/AI-coding/actions/workflows/opencode-cloud.yml) manually on main for 30 to 330 minutes (default 330 minutes / 5.5 hours).

## What persists

| State | Encrypted storage | Frequency |
|---|---|---|
| Chats, OpenCode v2 providers, OAuth tokens / API keys in the SQLite database | Git checkpoint branch opencode-cloud-backups-20261109 | Approximately every 2 minutes + normal exit |
| Legacy provider credentials in auth.json, global provider configs, plugins and agents | Same encrypted Git checkpoint | Approximately every 2 minutes + normal exit |
| Project directories from home, repo, /tmp, /mnt/data, /workspace, /workspaces, /opt/projects and OpenCode-registered custom paths | GitHub Releases assets with prefix ocvault- | Initially, roughly every 20 minutes, normal exit |
| Large OpenCode snapshots and legacy project storage | Same encrypted Release vault | Approximately every 20 minutes + normal exit |

Previous single-file and 40-MiB-part Git checkpoints remain readable. The three newest successfully published large snapshots are retained. A release is published only after all authenticated chunks and its encrypted manifest are safely uploaded.

## Multi-GB file support

The project vault streams compressed data into AES-256-GCM authenticated 256 MiB chunks. Each GitHub Release asset must be below 2 GiB. There is no 256 MiB aggregate project size limit, but a standard GitHub Ubuntu Actions runner has about 14 GB of storage, so much bigger active projects cannot fit on its temporary disk. Upload time, network usage and GitHub policies are also constraints.

GitHub Releases is a **release-distribution service, not unlimited guaranteed backup storage**. Do not treat this as a permanent replacement for an independent backup provider. Because large backups would use too much bandwidth every two minutes, the project checkpoint interval is 20 minutes; crashes can lose changes since the last published release. A normal stop attempts one last save, while a cancellation or runner timeout might interrupt it.

## Provider state and security

OpenCode v2 stores connected provider and account credentials in its SQLite database. Legacy auth.json files and OpenCode global config are also captured, so those settings normally come back on restart. OAuth tokens can still expire or be revoked by providers.

GitHub repository secrets, environment-only API tokens, SSH keys, CI access tokens and provider-side online data are **not** backed up automatically. Those need separate secure configuration. Large Release assets and Git snapshots are **publicly downloadable encrypted ciphertext**. The strong private OPENCODE_BACKUP_KEY protects their confidentiality.

Unreadable system-owned temporary directories (including /tmp/snap-private-tmp) are skipped rather than aborting an entire Release snapshot. A GitHub Actions warning reports how many inaccessible entries were skipped. If your own project is inaccessible, that project's files **will not be in the snapshot** until its permissions are fixed; do not interpret a published backup as proof that every unreadable file was saved.

System directories and CI runtime internals are not included. Reinstallable dependencies and caches, symlinks and SSH private keys are excluded. The backup restores discovered projects to the original validated directory paths.

This system has automated tests for encryption, chat/provider persistence, multi-part project archiving, restoration and tamper rejection. Actual large uploads through GitHub Releases still require a live GitHub Actions test to confirm the full remote path.

GitHub Actions is temporary CI infrastructure, not an always-running server. Privileged one-use OpenCode pairing links must not be shared in public logs.

Official references: [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), [GitHub Runner specs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job), [OpenCode provider accounts](https://opencode.ai/docs/cli/providers), [OpenCode configuration](https://docs.opencode.ai/docs/config/).
