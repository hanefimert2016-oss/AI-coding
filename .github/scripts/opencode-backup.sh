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
backup_dir="$checkout/.opencode-cloud"
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
  [[ -f "$backup_file" || -f "$backup_dir/manifest.enc" ]] || { echo 'No previous encrypted backup: starting fresh.'; return 0; }
  local temp
  temp="$(mktemp -d "$runner_temp/opencode-restore.XXXXXX")"
  trap 'rm -rf "$temp"' EXIT
  if [[ -f "$backup_dir/manifest.enc" ]]; then
    node "$crypto" decrypt "$backup_dir/manifest.enc" "$temp/manifest.txt"
    read -r version parts expected_sha expected_size < "$temp/manifest.txt"
    if [[ "$version" != "V2" || ! "$parts" =~ ^[0-9]+$ || ! "$expected_sha" =~ ^[0-9a-f]{64}$ || ! "$expected_size" =~ ^[0-9]+$ ]]; then
      echo '::error::Invalid encrypted backup manifest.' >&2
      return 1
    fi
    if (( parts < 1 || parts > 7 || expected_size > 268435456 )); then
      echo '::error::Backup exceeded restore size limits.' >&2
      return 1
    fi
    : > "$temp/payload.tar.gz"
    local part
    for ((i=0; i<parts; i++)); do
      part="$(printf 'part-%04d.enc' "$i")"
      [[ -f "$backup_dir/$part" ]] || { echo "::error::Missing $part" >&2; return 1; }
      node "$crypto" decrypt "$backup_dir/$part" "$temp/chunk.bin"
      cat "$temp/chunk.bin" >> "$temp/payload.tar.gz"
      rm -f "$temp/chunk.bin"
    done
    if [[ "$(stat -c '%s' "$temp/payload.tar.gz")" != "$expected_size" || "$(sha256sum "$temp/payload.tar.gz" | cut -d' ' -f1)" != "$expected_sha" ]]; then
      echo '::error::Backup checksum mismatch.' >&2
      return 1
    fi
  else
    # Restore existing checkpoints made by the original (single-file) backup system.
    node "$crypto" decrypt "$backup_file" "$temp/payload.tar.gz"
  fi
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
  # Project files are streamed independently into encrypted GitHub Release assets.
  # Keep the frequent Git checkpoint small: provider auth, chat SQLite and OpenCode config.
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
  tar -czf "$temp/payload.tar.gz" -C "$temp/payload" .
  size="$(stat -c '%s' "$temp/payload.tar.gz")"
  if (( size > 256 * 1024 * 1024 )); then
    echo '::error::Compressed backup exceeds 256 MiB; store oversized models/videos elsewhere.' >&2
    return 1
  fi
  mkdir -p "$temp/parts" "$temp/encrypted" "$backup_dir"
  split -b 40m -d -a 4 "$temp/payload.tar.gz" "$temp/parts/part-"
  local count=0 item sha
  sha="$(sha256sum "$temp/payload.tar.gz" | cut -d' ' -f1)"
  for item in "$temp/parts"/part-*; do
    [[ -f "$item" ]] || continue
    node "$crypto" encrypt "$item" "$(printf '%s/part-%04d.enc' "$temp/encrypted" "$count")"
    count=$((count+1))
  done
  printf 'V2 %s %s %s\n' "$count" "$sha" "$size" > "$temp/manifest.txt"
  node "$crypto" encrypt "$temp/manifest.txt" "$temp/encrypted/manifest.enc"
  # Git commit is atomic: older complete snapshots stay in history if push fails.
  rm -f "$backup_dir"/part-*.enc "$backup_dir/manifest.enc" "$backup_file"
  cp "$temp/encrypted/"* "$backup_dir/"
  git -C "$checkout" add -A -- '.opencode-cloud/'
  git -C "$checkout" commit -q -m "Encrypted OpenCode checkpoint $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  git -C "$checkout" push -q origin "$branch"
  echo "Encrypted checkpoint saved to $branch ($size compressed bytes, $count parts)."

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
