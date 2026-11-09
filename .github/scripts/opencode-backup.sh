#!/usr/bin/env bash
# Encrypted incremental checkpointing of a disposable Actions runner.
set -Eeuo pipefail
umask 077

repo="${GITHUB_WORKSPACE:?GITHUB_WORKSPACE required}"
runner_temp="${RUNNER_TEMP:?RUNNER_TEMP required}"
branch='opencode-cloud-backups-20261109'
checkout="$runner_temp/opencode-backup-checkout"
workspace="$repo/cloud-workspace"
data="$HOME/.local/share/opencode"
config="$HOME/.config/opencode"
backup_file="$checkout/.opencode-cloud/latest.enc"
crypto="$repo/.github/scripts/opencode-crypto.mjs"
lock="$runner_temp/opencode-backup.lock"

if [[ -z "${OPENCODE_BACKUP_KEY:-}" || ${#OPENCODE_BACKUP_KEY} -lt 32 ]]; then
  echo '::error::Set Actions secret OPENCODE_BACKUP_KEY to a high-entropy, unique 32+ character value.' >&2
  exit 1
fi

prepare() {
  mkdir -p "$workspace" "$runner_temp"
  git -C "$repo" fetch --no-tags -q origin "refs/heads/$branch:refs/remotes/origin/$branch"
  if [[ ! -d "$checkout/.git" && ! -f "$checkout/.git" ]]; then
    git -C "$repo" worktree add --detach "$checkout" "origin/$branch" >/dev/null
    git -C "$checkout" checkout -q -B "$branch" "origin/$branch"
  fi
  git -C "$checkout" config user.name 'github-actions[bot]'
  git -C "$checkout" config user.email '41898282+github-actions[bot]@users.noreply.github.com'
}

restore() (
  [[ -f "$backup_file" ]] || { echo 'No previous encrypted backup: starting fresh.'; return 0; }
  local temp
  temp="$(mktemp -d "$runner_temp/opencode-restore.XXXXXX")"
  trap 'rm -rf "$temp"' EXIT
  node "$crypto" decrypt "$backup_file" "$temp/payload.tar.gz"
  mkdir -p "$temp/payload"
  tar -xzf "$temp/payload.tar.gz" -C "$temp/payload" --no-same-owner
  if [[ -d "$temp/payload/workspace" ]]; then
    mkdir -p "$workspace"
    rsync -a "$temp/payload/workspace/" "$workspace/"
  fi
  if [[ -d "$temp/payload/data" ]]; then
    mkdir -p "$data"
    rsync -a "$temp/payload/data/" "$data/"
  fi
  if [[ -d "$temp/payload/config" ]]; then
    mkdir -p "$config"
    rsync -a --exclude='/service.json' "$temp/payload/config/" "$config/"
  fi
  python3 "$repo/.github/scripts/opencode-project-files.py" restore "$temp/payload/projects"
  echo 'Encrypted OpenCode session, settings and project folders restored.'
)

save_unlocked() (
  local temp size
  temp="$(mktemp -d "$runner_temp/opencode-save.XXXXXX")"
  trap 'rm -rf "$temp"' EXIT
  mkdir -p "$temp/payload/workspace" "$temp/payload/data" "$temp/payload/config"
  if [[ -d "$workspace" ]]; then
    rsync -a \
      --exclude='node_modules/' --exclude='.venv/' --exclude='venv/' \
      --exclude='.next/' --exclude='dist/' --exclude='build/' \
      --exclude='target/' --exclude='__pycache__/' \
      "$workspace/" "$temp/payload/workspace/"
  fi
  if [[ -d "$data" ]]; then
    rsync -a --exclude='/log/' --exclude='/opencode.db' \
      --exclude='/opencode.db-wal' --exclude='/opencode.db-shm' \
      "$data/" "$temp/payload/data/"
    if [[ -f "$data/opencode.db" ]]; then
      python3 - "$data/opencode.db" "$temp/payload/data/opencode.db" <<'PY'
import sqlite3
import sys
from pathlib import Path
source, destination = sys.argv[1:]
Path(destination).parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(f'file:{source}?mode=ro', uri=True, timeout=30) as original:
    with sqlite3.connect(destination, timeout=30) as snapshot:
        original.backup(snapshot, pages=256, sleep=0.1)
PY
    fi
  fi
  if [[ -d "$config" ]]; then
    rsync -a --exclude='/service.json' "$config/" "$temp/payload/config/"
  fi
  python3 "$repo/.github/scripts/opencode-project-files.py" save "$temp/payload/projects"
  tar -czf "$temp/payload.tar.gz" -C "$temp/payload" .
  size="$(stat -c '%s' "$temp/payload.tar.gz")"
  if (( size > 90 * 1024 * 1024 )); then
    echo '::error::Encrypted checkpoint is larger than 90 MiB; split the project or remove generated files.' >&2
    return 1
  fi
  node "$crypto" encrypt "$temp/payload.tar.gz" "$temp/latest.enc"
  mkdir -p "$(dirname "$backup_file")"
  cp "$temp/latest.enc" "$backup_file"
  git -C "$checkout" add -- '.opencode-cloud/latest.enc'
  git -C "$checkout" commit -q -m "Encrypted OpenCode checkpoint $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  git -C "$checkout" push -q origin "$branch"
  echo "Encrypted checkpoint pushed to $branch ($(date -u +'%H:%M:%S') UTC, compressed $size bytes)."
)

save() {
  exec 9>"$lock"
  if ! flock -n 9; then
    echo 'Another checkpoint is in progress; skipping overlap.'
    return 0
  fi
  save_unlocked
}

case "${1:-}" in
  prepare) prepare ;;
  restore) restore ;;
  save) save ;;
  *) echo 'Usage: bash opencode-backup.sh prepare|restore|save' >&2; exit 2 ;;
esac
