#!/usr/bin/env bash
set -euo pipefail

ROOT="${GITHUB_WORKSPACE:?}"
SOURCE="$ROOT/source/godot"
STATE="$ROOT/memory/persistent/project"
GAME="$ROOT/work/game"
RESULTS="$ROOT/work/results"

mkdir -p "$GAME" "$RESULTS"
if [[ -s "$STATE/project.godot" ]]; then
  echo "RESTORE_SOURCE=persistent-branch" | tee "$RESULTS/restore.txt"
  rsync -a --exclude='.godot/' --exclude='.import/' "$STATE/" "$GAME/"
else
  echo "RESTORE_SOURCE=starter-template" | tee "$RESULTS/restore.txt"
  rsync -a --exclude='.godot/' --exclude='.import/' "$SOURCE/" "$GAME/"
fi
test -s "$GAME/project.godot"
test -s "$GAME/scenes/main.tscn"
test -s "$GAME/scripts/world.gd"

python3 - "$GAME" "$RESULTS" <<'PY'
import json, os, pathlib, sys
from datetime import datetime, timezone
game, results = map(pathlib.Path, sys.argv[1:3])
state_file = game / "data/ci_state.json"
previous = json.loads(state_file.read_text()) if state_file.exists() else {}
last = int(previous.get("run_number", 0))
current = last + 1
payload = {
    "run_number": current,
    "previous_run": last,
    "github_run_id": os.environ.get("GITHUB_RUN_ID", "local"),
    "github_sha": os.environ.get("GITHUB_SHA", "local"),
    "updated_utc": datetime.now(timezone.utc).isoformat(),
}
state_file.parent.mkdir(parents=True, exist_ok=True)
state_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
(results / "run_metadata.json").write_text(json.dumps(payload, indent=2) + "\n")
print(f"PERSISTENCE_RESTORED_PREVIOUS={last}")
print(f"PERSISTENCE_NEXT_RUN={current}")
with open(os.environ["GITHUB_ENV"], "a") as env:
    env.write(f"GODOT_RUN_NUMBER={current}\n")
PY
