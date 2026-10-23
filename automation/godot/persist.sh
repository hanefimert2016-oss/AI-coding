#!/usr/bin/env bash
set -euo pipefail

ROOT="${GITHUB_WORKSPACE:?}"
STATE="$ROOT/memory"
GAME="$ROOT/work/game"
RESULTS="$ROOT/work/results"
RUN="${GODOT_RUN_NUMBER:-unknown}"
PASSED="${GODOT_TEST_PASSED:-false}"

mkdir -p "$STATE/persistent/run-history/$RUN"
HISTORY="$STATE/persistent/run-history/$RUN"
cp -a "$RESULTS/." "$HISTORY/" 2>/dev/null || true
printf '%s\n' "$PASSED" > "$HISTORY/test-passed.txt"

if [[ "$PASSED" == "true" ]]; then
  mkdir -p "$STATE/persistent/project"
  rsync -a --delete \
    --exclude='.godot/' \
    --exclude='.import/' \
    --exclude='*.tmp' \
    "$GAME/" "$STATE/persistent/project/"
  # The run metadata is the authoritative counter. Write it explicitly,
  # rather than relying on timestamp/size heuristics when rsync copies JSON.
  python3 - "$RESULTS/run_metadata.json" "$STATE/persistent/project/data/ci_state.json" <<'PY'
import json, pathlib, sys
source = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
metadata = json.loads(source.read_text())
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
check = json.loads(target.read_text())
assert check["run_number"] == metadata["run_number"]
assert check["previous_run"] < check["run_number"]
print("FORCED_PERSISTED_RUN_NUMBER=", check["run_number"])
PY
  echo "PROJECT_PERSISTED=YES" | tee -a "$HISTORY/persistence.txt"
else
  echo "PROJECT_PERSISTED=NO (validation failed; previous good project preserved)" | tee -a "$HISTORY/persistence.txt"
fi

# GitHub will refuse files above 100 MiB. Avoid a partial, misleading commit.
if find "$STATE/persistent" -type f -size +95M -print -quit | grep -q .; then
  echo "::error::Generated file exceeds 95 MiB. Use Git LFS or a Releases asset for large video/build binaries."
  exit 5
fi

python3 - "$STATE/persistent" "$HISTORY" <<'PY'
import hashlib, json, pathlib, sys
root, history = map(pathlib.Path, sys.argv[1:])
project = root / "project"
out = {}
for file in sorted(project.rglob("*")):
    if file.is_file() and ".godot" not in file.parts:
        out[str(file.relative_to(project))] = {
            "size": file.stat().st_size,
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest()
        }
(history / "project-manifest.json").write_text(json.dumps(out, indent=2) + "\n")
print("PERSISTENT_PROJECT_FILES=",len(out))
PY

git -C "$STATE" config user.name "github-actions[bot]"
git -C "$STATE" config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git -C "$STATE" add -A persistent
if ! git -C "$STATE" diff --cached --quiet; then
  git -C "$STATE" commit -m "Persist Godot run $RUN (test=$PASSED)"
  git -C "$STATE" push origin HEAD:godot-persistent-state
  echo "PERSIST_BRANCH_COMMIT=$(git -C "$STATE" rev-parse HEAD)" | tee -a "$RESULTS/published.txt"
else
  echo "Nothing changed in Godot persisted state."
fi
