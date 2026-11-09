"""Verify that the Actions duration dropdown and shell validation stay synchronized."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
yaml = (root / ".github/workflows/opencode-cloud.yml").read_text()
shell = (root / ".github/scripts/opencode-remote-session.sh").read_text()

timeout_match = re.search(r"(?m)^    timeout-minutes: (\d+)$", yaml)
default_match = re.search(r"(?m)^        default: '(\d+)'$", yaml)
allowed_match = re.search(r"(?m)^  ([0-9|]+)\) ;;$", shell)
assert timeout_match and default_match and allowed_match, "Missing expected duration config"

job_timeout = int(timeout_match.group(1))
default = int(default_match.group(1))
options_block = yaml.split("        options:", 1)[1].split("\n\npermissions:", 1)[0]
choices = [int(x) for x in re.findall(r"(?m)^          - '(\d+)'$", options_block)]
allowed = [int(x) for x in allowed_match.group(1).split("|")]

assert choices == [30, 60, 90, 120, 180, 240, 300, 330], choices
assert allowed == choices, (allowed, choices)
assert default == 330, default
assert job_timeout == 355, job_timeout
assert job_timeout <= 360 and job_timeout - max(choices) >= 25
print("PASS: 355-min job, 330-min session, matching choices, >=25-min finalization buffer")
