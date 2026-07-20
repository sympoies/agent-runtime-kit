#!/usr/bin/env bash
# Authenticated, opt-in Codex reviewer profile and selector smoke.

set -euo pipefail

if [ "${RUNTIME_SMOKE_CODEX_AUTHENTICATED:-0}" != "1" ]; then
  echo "codex-reviewer-dispatch: set RUNTIME_SMOKE_CODEX_AUTHENTICATED=1 to authorize the live probe" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
: "${AGENT_HOME:?AGENT_HOME must name the runtime artifact root}"
SOURCE_CODEX_HOME="${RUNTIME_SMOKE_SOURCE_CODEX_HOME:-${CODEX_HOME:-$HOME/.codex}}"
ARTIFACT_PARENT="$AGENT_HOME/out/runtime-smoke"
mkdir -p "$ARTIFACT_PARENT"
ARTIFACTS_DIR="$(mktemp -d "$ARTIFACT_PARENT/codex-reviewer-dispatch.XXXXXX")"
PROBE_HOME="$ARTIFACTS_DIR/codex-home"
PROMPT_FILE="$ARTIFACTS_DIR/prompt.txt"
STDOUT_FILE="$ARTIFACTS_DIR/codex.stdout.jsonl"
STDERR_FILE="$ARTIFACTS_DIR/codex.stderr.txt"
INVENTORY_FILE="$ARTIFACTS_DIR/reviewer-inventory.txt"
RESPONSE_FILE="$ARTIFACTS_DIR/final-agent-message.txt"
mkdir -p "$PROBE_HOME"

cleanup_probe_home() {
  rm -f "$PROBE_HOME/auth.json" "$PROBE_HOME/agents" "$PROBE_HOME/config.toml"
  rmdir "$PROBE_HOME" 2>/dev/null || true
}
trap cleanup_probe_home EXIT

if [ ! -d "$SOURCE_CODEX_HOME/agents" ]; then
  echo "codex-reviewer-dispatch: installed agents directory missing: $SOURCE_CODEX_HOME/agents" >&2
  exit 1
fi
ln -s "$SOURCE_CODEX_HOME/agents" "$PROBE_HOME/agents"
if [ -f "$SOURCE_CODEX_HOME/auth.json" ]; then
  ln -s "$SOURCE_CODEX_HOME/auth.json" "$PROBE_HOME/auth.json"
elif [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "codex-reviewer-dispatch: no reusable Codex auth.json or OPENAI_API_KEY" >&2
  exit 1
fi

python3 - "$REPO_ROOT/manifests/agents.yaml" "$SOURCE_CODEX_HOME/agents" "$INVENTORY_FILE" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
agents_dir = Path(sys.argv[2])
inventory_file = Path(sys.argv[3])
names: list[str] = []
reviewer_id = ""
product = ""
for line in manifest.read_text(encoding="utf-8").splitlines():
    if line.startswith("  - id: "):
        reviewer_id = line.split(": ", 1)[1]
        product = ""
    elif re.match(r"^      [a-z]+:$", line):
        product = line.strip().removesuffix(":")
    elif (
        reviewer_id.startswith("code-review.reviewer-")
        and product == "codex"
        and line.startswith("        name: ")
    ):
        names.append(line.split(": ", 1)[1])

if len(names) != 8 or len(set(names)) != 8 or "reviewer-quick" not in names:
    raise SystemExit(f"unexpected manifest reviewer inventory: {names!r}")
for name in names:
    profile_path = agents_dir / f"{name}.toml"
    if not profile_path.is_file():
        raise SystemExit(f"missing installed reviewer profile: {profile_path}")
    profile_text = profile_path.read_text(encoding="utf-8")
    profile = {
        field: match.group(1) if (
            match := re.search(
                rf'^{re.escape(field)} = "([^"]+)"$',
                profile_text,
                flags=re.MULTILINE,
            )
        ) else None
        for field in ("name", "model", "model_reasoning_effort", "sandbox_mode")
    }
    expected_model = "gpt-5.6-terra" if name == "reviewer-quick" else "gpt-5.6-sol"
    expected = {
        "name": name,
        "model": expected_model,
        "model_reasoning_effort": "medium",
        "sandbox_mode": "read-only",
    }
    actual = {key: profile.get(key) for key in expected}
    if actual != expected:
        raise SystemExit(f"installed profile mismatch for {name}: {actual!r}")
inventory_file.write_text("\n".join(names) + "\n", encoding="utf-8")
PY

{
  printf 'model = "gpt-5.4"\n'
  printf 'model_reasoning_effort = "xhigh"\n'
  printf 'sandbox_mode = "danger-full-access"\n'
  printf '[features]\n'
  printf 'multi_agent = true\n'
} >"$PROBE_HOME/config.toml"

{
  echo 'Inspect the exposed subagent dispatch tool schema before calling it.'
  echo 'If it does not expose an agent_type selector, do not spawn any child and reply exactly:'
  echo 'REVIEWER_DISPATCH_SKIP selector=agent_type unavailable fallback=inline'
  echo 'If agent_type is exposed, dispatch every identity below with agent_type set to the exact hyphenated identity.'
  echo 'Use task_name values probe-1 through probe-8 so task_name cannot masquerade as the profile selector.'
  echo 'Ask each child only to reply PROFILE_OK followed by its assigned identity; wait for all children.'
  echo 'Then reply REVIEWER_DISPATCH_PASS followed by all eight identities in manifest order.'
  cat "$INVENTORY_FILE"
} >"$PROMPT_FILE"

set +e
CODEX_HOME="$PROBE_HOME" codex --ask-for-approval never exec \
  --ephemeral \
  --skip-git-repo-check \
  -C "$REPO_ROOT" \
  --json \
  "$(cat "$PROMPT_FILE")" >"$STDOUT_FILE" 2>"$STDERR_FILE"
exit_code="$?"
set -e

if [ "$exit_code" -ne 0 ]; then
  echo "codex-reviewer-dispatch: Codex execution failed; artifacts=$ARTIFACTS_DIR" >&2
  exit "$exit_code"
fi
python3 - "$STDOUT_FILE" "$RESPONSE_FILE" <<'PY'
import json
import sys
from pathlib import Path

messages = []
for raw in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        continue
    item = event.get("item")
    if isinstance(item, dict) and item.get("type") == "agent_message":
        text = item.get("text")
        if isinstance(text, str):
            messages.append(text)
if not messages:
    raise SystemExit("Codex JSONL contained no agent_message event")
Path(sys.argv[2]).write_text(messages[-1].strip() + "\n", encoding="utf-8")
PY

if grep -Fxq 'REVIEWER_DISPATCH_SKIP selector=agent_type unavailable fallback=inline' "$RESPONSE_FILE"; then
  echo "codex-reviewer-dispatch: status=skip-host-capability selector=agent_type fallback=inline artifacts=$ARTIFACTS_DIR"
  exit 0
fi
if ! grep -Eq '^REVIEWER_DISPATCH_PASS([[:space:]]|$)' "$RESPONSE_FILE"; then
  echo "codex-reviewer-dispatch: missing pass or explicit capability-skip marker; artifacts=$ARTIFACTS_DIR" >&2
  exit 1
fi
while IFS= read -r reviewer; do
  if ! grep -Fq "$reviewer" "$RESPONSE_FILE"; then
    echo "codex-reviewer-dispatch: authenticated result omitted $reviewer; artifacts=$ARTIFACTS_DIR" >&2
    exit 1
  fi
done <"$INVENTORY_FILE"

echo "codex-reviewer-dispatch: status=pass reviewers=8 parent=gpt-5.4/xhigh/danger-full-access child-profiles=explicit/medium/read-only artifacts=$ARTIFACTS_DIR"
