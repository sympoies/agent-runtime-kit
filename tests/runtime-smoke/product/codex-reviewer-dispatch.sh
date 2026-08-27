#!/usr/bin/env bash
# Authenticated, opt-in Codex reviewer profile and selector smoke.
#
# Three distinct outcomes, and only the third is a pass:
#   * the host exposes no `agent_type` selector  -> skip-host-capability
#   * the host advertises a canonical identity but refuses to dispatch it
#     -> FAIL (agent-runtime-kit#58); the inline fallback still works, but a
#     schema that advertises an undispatchable reviewer is a broken surface,
#     not a supported host shape
#   * every canonical identity dispatches         -> pass
#
# The advertised-but-rejected verdict does not rely on the model's own report:
# the probe greps the Codex event stream for the host's verbatim rejection
# (`agent type is currently not available`) and fails on it directly.

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
    expected_model = "gpt-5.6-sol"
    expected_effort = "low" if name == "reviewer-quick" else "medium"
    expected = {
        "name": name,
        "model": expected_model,
        "model_reasoning_effort": expected_effort,
        "sandbox_mode": "read-only",
    }
    actual = {key: profile.get(key) for key in expected}
    if actual != expected:
        raise SystemExit(f"installed profile mismatch for {name}: {actual!r}")
    # agent-runtime-kit#58: codex-cli enumerates `$CODEX_HOME/agents/*.toml`
    # into the `spawn_agent` `agent_type` schema through a path-following stat,
    # but resolves dispatch content from the directory entry itself and refuses
    # a symlinked leaf. The link map therefore installs `agents` as one
    # directory symlink so every profile leaf stays a regular file.
    if profile_path.is_symlink():
        raise SystemExit(
            f"installed reviewer profile is a symlink: {profile_path}; codex-cli "
            "advertises it but cannot dispatch it. Install `$CODEX_HOME/agents` "
            "as a single directory symlink (agent-runtime-kit#58)."
        )
inventory_file.write_text("\n".join(names) + "\n", encoding="utf-8")
PY

{
  printf 'model = "gpt-5.6-sol"\n'
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
  echo 'Never retry a rejected dispatch and never substitute a different agent_type for a rejected one.'
  echo 'If the schema advertises an identity below but dispatching it fails, reply exactly:'
  echo 'REVIEWER_DISPATCH_ADVERTISED_REJECTED followed by each rejected identity and its verbatim error text.'
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

# Objective host verdict first: codex-cli emits this verbatim when it advertises
# an `agent_type` it will not dispatch. Checked against the Codex event stream
# and stderr, so a model that misreports the outcome cannot turn a broken
# surface into a skip or a pass.
HOST_REJECTION='agent type is currently not available'
if grep -Fq "$HOST_REJECTION" "$STDOUT_FILE" "$STDERR_FILE" "$RESPONSE_FILE" 2>/dev/null; then
  echo "codex-reviewer-dispatch: status=fail-advertised-rejected selector=agent_type host_error='$HOST_REJECTION'" >&2
  echo "codex-reviewer-dispatch: the active spawn_agent schema advertises a canonical reviewer identity the host refuses to dispatch (agent-runtime-kit#58); artifacts=$ARTIFACTS_DIR" >&2
  exit 1
fi
if grep -Eq '^REVIEWER_DISPATCH_ADVERTISED_REJECTED([[:space:]]|$)' "$RESPONSE_FILE"; then
  echo "codex-reviewer-dispatch: status=fail-advertised-rejected selector=agent_type artifacts=$ARTIFACTS_DIR" >&2
  cat "$RESPONSE_FILE" >&2
  exit 1
fi
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

echo "codex-reviewer-dispatch: status=pass reviewers=8 parent=gpt-5.6-sol/xhigh/danger-full-access child-profiles=sol/quick-low/specialists-medium/read-only artifacts=$ARTIFACTS_DIR"
