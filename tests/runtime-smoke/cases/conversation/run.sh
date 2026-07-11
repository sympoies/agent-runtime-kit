#!/usr/bin/env bash
# Deterministic probes for workflow-only conversation skills.
# shellcheck disable=SC2329

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/rendered-contract.sh
. "$SCRIPT_DIR/lib/rendered-contract.sh"

CONVERSATION_ARTIFACTS_DIR="$ARTIFACTS_DIR/conversation"
mkdir -p "$CONVERSATION_ARTIFACTS_DIR"

require_conversation_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke conversation: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

run_conversation_skill_probe() {
  local skill="$1"
  local out="$CONVERSATION_ARTIFACTS_DIR/${skill}.txt"
  local source="$REPO_ROOT/core/skills/conversation/${skill}/SKILL.md.tera"
  local codex="$REPO_ROOT/build/codex/plugins/conversation/skills/${skill}/SKILL.md"
  local claude="$REPO_ROOT/build/claude/plugins/conversation/skills/${skill}/SKILL.md"

  require_conversation_bin agent-runtime || return 1
  agent-runtime render --product codex >"$CONVERSATION_ARTIFACTS_DIR/render-codex.log" 2>&1
  agent-runtime render --product claude >"$CONVERSATION_ARTIFACTS_DIR/render-claude.log" 2>&1

  {
    printf 'source=%s\n' "$source"
    printf 'codex=%s\n' "$codex"
    printf 'claude=%s\n' "$claude"
  } >"$out"

  test -f "$source"
  test -f "$codex"
  test -f "$claude"
  grep -q "^name: ${skill}$" "$source"
  grep -q "^name: ${skill}$" "$codex"
  grep -q "^name: ${skill}$" "$claude"
}

run_conversation_outcome_routing_probe() {
  local home_policy="$REPO_ROOT/AGENT_HOME.md"
  local guided="$REPO_ROOT/core/skills/conversation/guided-feature-build/SKILL.md.tera"
  local protocol="$REPO_ROOT/core/skills/conversation/guided-feature-build/references/DELEGATION_PROTOCOL.md"

  grep -Fq 'Natural-language collaboration is the default interface' "$home_policy"
  grep -Fq '## Outcome Routing' "$guided"
  grep -Fq 'Advice and explanation stay normal conversation behavior' "$guided"
  grep -Fq 'selects inline, orchestrated, or' "$guided"
  grep -Fq 'parallel execution internally' "$guided"
  grep -Fq 'references/DELEGATION_PROTOCOL.md' "$guided"
  test -s "$protocol"
  grep -Fq '## Write Isolation' "$protocol"

  rendered_contract_assert_skill conversation guided-feature-build
  rendered_contract_assert_all_contain conversation guided-feature-build '## Outcome Routing'
  rendered_contract_assert_all_contain conversation guided-feature-build 'references/DELEGATION_PROTOCOL.md'
  rendered_contract_assert_reference conversation guided-feature-build references/DELEGATION_PROTOCOL.md
}

failures=0
record_case "conversation.actionable-advice" "prompt-style skill source and rendered surfaces exist for both products" run_conversation_skill_probe actionable-advice
record_case "conversation.actionable-knowledge" "prompt-style skill source and rendered surfaces exist for both products" run_conversation_skill_probe actionable-knowledge
record_case "conversation.discussion-to-implementation-doc" "workflow skill source and rendered surfaces exist for both products" run_conversation_skill_probe discussion-to-implementation-doc
record_case "conversation.guided-feature-build" "workflow skill source and rendered surfaces exist for both products" run_conversation_skill_probe guided-feature-build
record_case "conversation.handoff-session-prompt" "workflow skill source and rendered surfaces exist for both products" run_conversation_skill_probe handoff-session-prompt
record_case "conversation.orchestrator-first" "prompt-style skill source and rendered surfaces exist for both products" run_conversation_skill_probe orchestrator-first
record_case "conversation.parallel-first" "prompt-style skill source and rendered surfaces exist for both products" run_conversation_skill_probe parallel-first
record_case "conversation.outcome-routing" "normal conversation and guided build select advice, explanation, and delegation modes without child-skill selection" run_conversation_outcome_routing_probe

exit "$failures"
