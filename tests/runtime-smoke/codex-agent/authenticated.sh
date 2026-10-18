#!/usr/bin/env bash
# Scheduled tester only: authenticated isolated doctor + knowledge acceptance.
set -euo pipefail
if [ "${RUNTIME_SMOKE_CODEX_AUTHENTICATED:-0}" != 1 ]; then
  echo "codex-agent acceptance: scheduled tester must set RUNTIME_SMOKE_CODEX_AUTHENTICATED=1" >&2
  exit 2
fi
umask 077
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source_home="${RUNTIME_SMOKE_SOURCE_CODEX_HOME:-${CODEX_HOME:-$HOME/.codex}}"
source_home="$(cd "$source_home" && pwd -P)"
: "${RUNTIME_SMOKE_ARTIFACTS_DIR:?allocate a private directory with agent-out project}"
RUNTIME_SMOKE_ARTIFACTS_DIR="$(
  python3 - "$REPO_ROOT" "$RUNTIME_SMOKE_ARTIFACTS_DIR" <<'PY'
import sys
from pathlib import Path
repo = Path(sys.argv[1]).resolve()
directory = Path(sys.argv[2]).absolute()
if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
    raise SystemExit('codex-agent acceptance: artifacts require a non-symlink directory')
resolved = directory.resolve()
if resolved == repo or repo in resolved.parents:
    raise SystemExit('codex-agent acceptance: artifacts must remain outside the repository')
directory.mkdir(parents=True, exist_ok=True, mode=0o700)
directory.chmod(0o700)
print(resolved)
PY
)"
command -v codex >/dev/null
command -v codex-cli >/dev/null
python3 "$REPO_ROOT/tests/runtime-smoke/codex-agent/run.py" --layer product \
  --matrix-out "$RUNTIME_SMOKE_ARTIFACTS_DIR/matrix.json" \
  >"$RUNTIME_SMOKE_ARTIFACTS_DIR/product.json"

# Only an auth symlink is borrowed. No operator config/hooks/skills are linked.
# Credentials are never read by this script, copied, printed or retained.
if [ ! -f "$source_home/auth.json" ]; then
  echo "codex-agent acceptance: file-backed auth is required for this bridge smoke; credential-store-only acceptance remains manual" >&2
  exit 2
fi
probe="$(mktemp -d "${TMPDIR:-/tmp}/codex-agent-authenticated.XXXXXX")"
chmod 700 "$probe"
cleanup() { rm -rf "$probe"; }
trap cleanup EXIT
mkdir -p "$probe/codex-home" "$probe/workspace" "$probe/shell/prompts" "$probe/xdg"
ln -s "$source_home/auth.json" "$probe/codex-home/auth.json"
printf 'AUTHENTICATED_HOME_INSTRUCTION_SENTINEL\n' >"$probe/codex-home/AGENTS.md"
printf 'AUTHENTICATED_PROJECT_INSTRUCTION_SENTINEL\n' >"$probe/workspace/AGENTS.md"
# Literal placeholder consumed by codex-cli's template renderer.
# shellcheck disable=SC2016
printf '%s\n' '$ARGUMENTS' >"$probe/shell/prompts/actionable-knowledge.md"

# The outer managed session's controls remain active. This small smoke does
# not replace the observed lifecycle controls listed in README.md.
# Capture raw product output privately; publish only the tester receipt fields.
(
  cd "$probe/workspace"
  export CODEX_HOME="$probe/codex-home"
  export ZDOTDIR="$probe/shell"
  export XDG_CONFIG_HOME="$probe/xdg"
  unset CODEX_CLI_AGENT_RUNTIME CODEX_AUTH_FILE CODEX_AUTH_REMOTE_SSH CODEX_AUTH_REMOTE_NAME
  codex-cli agent doctor --format json >"$RUNTIME_SMOKE_ARTIFACTS_DIR/doctor.json"
  codex-cli agent knowledge 'Reply with the active runtime mode only: isolated.' \
    >"$RUNTIME_SMOKE_ARTIFACTS_DIR/knowledge.stdout.txt" \
    2>"$RUNTIME_SMOKE_ARTIFACTS_DIR/knowledge.stderr.txt"
)
python3 - "$RUNTIME_SMOKE_ARTIFACTS_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path
root = Path(sys.argv[1])
doctor = json.loads((root / 'doctor.json').read_text())
assert doctor['schema_version'] == 'cli.codex-cli.agent.doctor.v1'
assert doctor['data']['ready'] is True
stdout = (root / 'knowledge.stdout.txt').read_text()
stderr = (root / 'knowledge.stderr.txt').read_text()
assert stdout.strip().lower() == 'isolated', 'knowledge did not return the required smoke response'
for forbidden in ['AUTHENTICATED_HOME_INSTRUCTION_SENTINEL',
                  'AUTHENTICATED_PROJECT_INSTRUCTION_SENTINEL', 'agent-hook']:
    assert forbidden not in stdout + stderr, 'runtime content surfaced in isolated smoke'
assert not re.search(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}', stdout + stderr), 'unexpected credential-shaped output'
print(json.dumps(dict(schema_version='codex-agent-authenticated-smoke.v1',
                      doctor_ready=True, response='isolated', sentinel_output_absent=True,
                      acceptance_complete=False,
                      remaining=['A3 lifecycle controls', 'A4 discovery controls',
                                 'A6 sandbox effects', 'A7 bridge-denial fault injection'])))
PY
