#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# Never accept passwords as workflow_dispatch inputs: they are visible in public repo metadata.
if [[ -z "${OPENCODE_PASSWORD:-}" || ${#OPENCODE_PASSWORD} -lt 20 ]]; then
  echo '::error::Set Actions secret OPENCODE_PASSWORD to a unique value of at least 20 characters.'
  exit 1
fi

case "${SESSION_MINUTES:-}" in
  30|60|90|120) ;;
  *) echo '::error::Invalid SESSION_MINUTES (30, 60, 90 or 120).'; exit 1 ;;
esac

pair_log="$(mktemp)"
cleanup() {
  rm -f "$pair_log"
  opencode service stop >/dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Official OpenCode v2 server (localhost only). OpenTunnel handles remote access.
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
printf 'OpenCode remote address (password protected): %s\n' "$origin"
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo '## OpenCode Cloud development session'
    echo
    printf '**OpenCode official UI:** %s\n' "$origin"
    echo
    echo 'Use your private `OPENCODE_PASSWORD` value to sign in. Do not share the secret.'
    echo
    echo 'All changes are made in the dedicated public `opencode-cloud-workspace-20261109` branch. Commit and push changes **before** the run ends, or the runner filesystem will be destroyed.'
    printf '\n**Maximum session:** %s minutes\n' "$SESSION_MINUTES"
  } >> "$GITHUB_STEP_SUMMARY"
fi

printf 'OpenCode runner active for at most %s minutes. Save changes before it stops.\n' "$SESSION_MINUTES"
sleep "$(( SESSION_MINUTES * 60 ))"
