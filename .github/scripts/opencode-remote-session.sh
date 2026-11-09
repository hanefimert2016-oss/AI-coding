#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# Never accept passwords as workflow_dispatch inputs: they are visible in public repo metadata.
if [[ -z "${OPENCODE_PASSWORD:-}" || ${#OPENCODE_PASSWORD} -lt 20 ]]; then
  echo '::error::Set Actions secret OPENCODE_PASSWORD to a unique value of at least 20 characters.'
  exit 1
fi

if [[ -z "${OPENCODE_BACKUP_KEY:-}" || ${#OPENCODE_BACKUP_KEY} -lt 32 ]]; then
  echo '::error::Set Actions secret OPENCODE_BACKUP_KEY to a unique 32+ character value distinct from the server password.'
  exit 1
fi
case "${SESSION_MINUTES:-}" in
  30|60|90|120|180|240|300|330) ;;
  *) echo '::error::Invalid SESSION_MINUTES (allowed: 30, 60, 90, 120, 180, 240, 300, 330 minutes).'; exit 1 ;;
esac

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backup="$script_dir/opencode-backup.sh"
vault="$script_dir/opencode-release-vault.py"
vault_lock="$RUNNER_TEMP/opencode-release-vault.lock"
pair_log="$(mktemp)"
autosave_pid=''
vault_pid=''
backup_ready=0
cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$autosave_pid" ]]; then
    kill "$autosave_pid" 2>/dev/null || true
    wait "$autosave_pid" 2>/dev/null || true
  fi
  if [[ -n "$vault_pid" ]]; then
    kill "$vault_pid" 2>/dev/null || true
    wait "$vault_pid" 2>/dev/null || true
  fi
  if [[ "$backup_ready" == 1 ]]; then
    bash "$backup" save || echo '::warning::Final chat/provider checkpoint failed; last successful backup remains.'
    flock -n "$vault_lock" python3 "$vault" save || echo '::warning::Final GB project checkpoint incomplete; last published release remains.'
  fi
  rm -f "$pair_log"
  opencode service stop >/dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Official OpenCode v2 server (localhost only). OpenTunnel handles remote access.
bash "$backup" prepare
bash "$backup" restore
python3 "$vault" restore
backup_ready=1
cd "$GITHUB_WORKSPACE/cloud-workspace"

opencode service set hostname 127.0.0.1 >/dev/null
opencode service set password "$OPENCODE_PASSWORD" >/dev/null
opencode service start >/dev/null

ready=0
for _ in $(seq 1 30); do
  if curl -fsS --max-time 2 --user "opencode:$OPENCODE_PASSWORD" \
      http://127.0.0.1:49374/api/info >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -ne 1 ]]; then
  echo '::error::OpenCode local server did not pass its readiness check.'
  exit 1
fi

# Pairing links bypass login and must NEVER appear in a public Actions log.
if ! opencode pair --remote --yes >"$pair_log" 2>&1; then
  echo '::error::OpenCode remote pairing failed (output withheld for security).'
  exit 1
fi

origin="$(python3 - "$pair_log" <<'PY'
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
raw = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
raw = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', raw)
urls = re.findall(r'https://[^\s<>"\x1b]+', raw)
for url in urls:
    url = url.rstrip(').,;')
    p = urlsplit(url)
    if p.scheme == 'https' and p.hostname and '/auth/connect/' in p.path:
        print(f'{p.scheme}://{p.netloc}/')
        break
PY
)"

if [[ -z "$origin" ]]; then
  echo '::error::No safe public URL could be extracted from remote pairing output.'
  exit 1
fi

# The URL alone is not a credential; the user must supply the Actions secret password.
# Do not publish /auth/connect/ token URLs in this public repository.
# Store an initial snapshot, then repeat every 120 seconds.
bash "$backup" save
(
  while sleep 120; do
    bash "$backup" save || echo '::warning::Periodic checkpoint failed; the previous successful backup remains available.'
  done
) &
autosave_pid=$!

# Multi-GB projects are backed up to authenticated encrypted GitHub Release assets.
# Full uploads are deliberately less frequent than chat/credential checkpoints.
(
  while true; do
    flock -n "$vault_lock" python3 "$vault" save || echo '::warning::Release upload failed; last published snapshot is preserved.'
    sleep 1200
  done
) &
vault_pid=$!

printf 'OpenCode remote address (password protected): %s\n' "$origin"
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '## OpenCode Cloud development session'
    echo
    printf '**OpenCode official UI:** %s\n' "$origin"
    echo
    echo 'Use your private `OPENCODE_PASSWORD` value to sign in. Do not share the secret.'
    echo
    echo 'OpenCode chats, provider OAuth/API credentials and settings: encrypted Git checkpoint every 2 minutes.'
    echo 'Project folders and large OpenCode snapshots: encrypted Release checkpoint approximately every 20 minutes, plus final exit attempt.'
    echo 'GitHub Releases stores ciphertext assets, not unencrypted project files.'
    echo 'The next session restores the last successful encrypted checkpoint before starting.'
    echo 'The public branch opencode-cloud-backups-20261109 contains encrypted small state. Published Releases contain encrypted large project data.'
    printf '\n**Maximum session:** %s minutes\n' "$SESSION_MINUTES"
  } >> "$GITHUB_STEP_SUMMARY"
fi

printf 'OpenCode active at most %s minutes. Chat/provider autosave 2min, large-project Releases 20min.\n' "$SESSION_MINUTES"
sleep "$(( SESSION_MINUTES * 60 ))"
