#!/usr/bin/env bash
# Deterministic memory policy, audit, and product-capability smoke.

set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

agent-docs preflight --docs-home "$REPO_ROOT" --project-path "$REPO_ROOT" --intent memory --strict >/dev/null

bash scripts/ci/retired-memory-audit.sh --self-test

state_out="${XDG_STATE_HOME:-$HOME/.local/state}/agent-runtime-kit/out"
mkdir -p "$state_out"
no_agent_home_state="$(mktemp -d "$state_out/memory-runtime-no-agent-home.XXXXXX")"
trap 'rm -rf "$no_agent_home_state"' EXIT
env -u AGENT_HOME -u AGENT_RUNTIME_MEMORY_AUDIT_OUT \
  XDG_STATE_HOME="$no_agent_home_state" \
  bash scripts/ci/retired-memory-audit.sh --self-test >/dev/null

python3 - <<'PY'
from pathlib import Path

root = Path.cwd()
policy = (root / "core/policies/memory.md").read_text(encoding="utf-8")
codex = (root / "targets/codex/hooks/config.block.toml").read_text(encoding="utf-8")
claude = (root / "core/hooks/claude/settings.hooks.jsonc").read_text(encoding="utf-8")
codex_harness = (root / "docs/source/harness-shape-codex.md").read_text(encoding="utf-8")

for text in (
    "agent-memory recall startup",
    "agent-memory recall on-demand <term>",
    "agent-memory candidate add <producer>",
    "explicit user approval",
    "| Codex |",
    "| Claude |",
    "| Hermes |",
):
    assert text in policy, text

assert "user-prompt-agent-memory.sh" in codex
assert "user-prompt-agent-memory.sh" not in claude
assert "agent-memory recall startup" in codex_harness
assert "agent-memory candidate add\n  codex" in codex_harness
assert "agent-memory index global" not in codex_harness
assert "/Users/" not in policy
assert "/home/" not in policy
PY

python3 -m unittest tests.hooks.test_shared_hooks.SharedHookTests.test_agent_memory_cue_injects_startup_memory_once_for_codex tests.hooks.test_shared_hooks.SharedHookTests.test_agent_memory_cue_noops_outside_codex tests.hooks.test_shared_hooks.SharedHookTests.test_agent_memory_cue_noops_when_startup_recall_fails

echo "memory-runtime: deterministic policy, audit, and product routing passed"
