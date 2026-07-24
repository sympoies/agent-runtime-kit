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

  if [ "$skill" = "guided-feature-build" ]; then
    for path in "$source" "$codex" "$claude"; do
      grep -Fq 'durable test-first lifecycle: contract delta, affected-test scan' "$path"
      grep -Fq 'convergence, and explicit residual gaps' "$path"
    done
  fi
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

run_main_agent_mode_probe() {
  local source="$REPO_ROOT/core/skills/conversation/main-agent-mode/SKILL.md.tera"
  local protocol="$REPO_ROOT/core/skills/conversation/main-agent-mode/references/MAIN_AGENT_MODE_PROTOCOL.md"
  local product rendered golden rendered_protocol golden_protocol

  test -s "$source"
  test -s "$protocol"
  grep -Fq '## Explicit Activation' "$source"
  grep -Fq 'agent-session activity doctor --agent codex --format json' "$source"
  grep -Fq 'agent-session activity doctor --agent claude --format json' "$source"
  grep -Fq 'agent-session activity setup --agent codex --repair --dry-run --format json' "$source"
  grep -Fq 'agent-session activity setup --agent claude --repair --dry-run --format json' "$source"
  if grep -Fq '$WORKER_PROVIDER' "$source"; then
    return 1
  fi
  grep -Fq 'compatibility_owner:"agent-hook"' "$source"
  grep -Fq '`agent-run inspect` remains the child safety boundary' "$source"
  grep -Fq -- '--coordination-mode enforce' "$source"
  grep -Fq -- 'main-agent worker start --assignment-file <private-json> --await-ready 5m' "$source"
  grep -Fq 'delivery.proof:"authenticated-worker-checkpoint"' "$source"
  grep -Fq 'submit_key_recovery' "$source"
  grep -Fq 'The runtime owns this recovery decision and keypress' "$source"
  grep -Fq 'automatic_retry_safe:false' "$source"
  grep -Fq 'main-agent bootstrap' "$source"
  grep -Fq 'candidate conflict check cleared' "$protocol"
  grep -Fq 'incarnation, working directory, and `enforce` mode' "$protocol"
  grep -Fq 'target capability' "$protocol"
  grep -Fq 'authenticated self-check as part of bootstrap' "$protocol"
  grep -Fq 'released or expired claim' "$protocol"
  grep -Fq 'before another mutation turn' "$protocol"
  grep -Fq 'interference or deletion before that handoff' "$protocol"
  grep -Fq 'session created, prompt delivery unverified' "$protocol"
  grep -Fq 'main-agent worker start --assignment-file <private-json> --await-ready 5m' "$protocol"
  grep -Fq 'delivery.proof: authenticated-worker-checkpoint' "$protocol"
  grep -Fq 'delivery.transport_state: submit-key-recovery-succeeded' "$protocol"
  grep -Fq 'The Main Agent never decides whether to inject this' "$protocol"
  grep -Fq 'keypress and never sends it itself.' "$protocol"
  grep -Fq 'automatic_retry_safe: false' "$protocol"
  grep -Fq 'main-agent bootstrap' "$protocol"
  grep -Fq 'as read-only diagnostics only after a' "$protocol"
  grep -Fq 'typed failure; then fix' "$protocol"
  grep -Fq 'Do not resend the prompt or inject another Enter' "$protocol"
  if grep -Fq 'paste without Enter, verified by envelope or character count' "$protocol"; then
    return 1
  fi
  grep -Fq 'On mismatch, truncation, interference, missing readiness' "$protocol"
  grep -Fq 'never downgrade it into a speculative retry' "$protocol"
  grep -Fq 'folded retire step, invoke it' "$protocol"
  grep -Fq 'may run in parallel across lanes' "$protocol"
  grep -Fq 'serialized and main-agent-owned' "$protocol"
  grep -Fq 'Main Agent Mode never auto-applies' "$protocol"
  grep -Fq '## Stop And Recovery Matrix' "$protocol"
  grep -Fq '| Work-context scope or worktree conflict |' "$protocol"
  grep -Fq '| Active or uncertain admitted mutation operation |' "$protocol"
  grep -Fq 'Retain the exact worker owner/session.' "$protocol"
  grep -Fq 'Do not retry the mutation, clear/release its claim, delete/reassign the worker, or guess the outcome.' "$protocol"
  grep -Fq 'Use only hook-retained private authenticated operation material to complete/reconcile a known terminal outcome.' "$protocol"
  grep -Fq 'If proof is unavailable, report blocked and preserve the session and evidence.' "$protocol"
  grep -Fq 'Delete an accepted terminal worker only after the facade and' "$source"
  grep -Fq 'session-management owner prove no active or uncertain operation remains,' "$source"
  grep -Fq 'the durable logical-delete boundary' "$source"
  grep -Fq 'physical cleanup failures in the maintenance projection rather than the live' "$source"
  grep -Fq '## Terminal Worker Cleanup' "$protocol"
  grep -Fq 'durable operation state that no active or uncertain admitted mutation operation' "$protocol"
  grep -Fq 'After operation quiescence is proven, have the exact worker release its active' "$protocol"
  grep -Fq 'work-context claim through the authenticated session-management lifecycle' "$protocol"
  grep -Fq 'Cleanup is complete only when a fresh privacy-safe `list`' "$protocol"
  grep -Fq 'result proves the exact session ID is absent' "$protocol"
  grep -Fq 'visible worker card and its structured error' "$protocol"
  grep -Fq 'and route the failed deletion' "$protocol"
  grep -Fq 'through the session-management recovery owner' "$protocol"

  rendered_contract_assert_product_contains conversation main-agent-mode codex 'For a Codex worker, run these literal commands:'
  rendered_contract_assert_product_contains conversation main-agent-mode codex 'agent-session activity doctor --agent codex --format json'
  rendered_contract_assert_product_contains conversation main-agent-mode codex 'agent-session activity setup --agent codex --repair --dry-run --format json'
  rendered_contract_assert_product_omits conversation main-agent-mode codex 'Claude'
  rendered_contract_assert_product_omits conversation main-agent-mode codex '--agent claude'
  rendered_contract_assert_product_contains conversation main-agent-mode claude 'For a Claude worker, run these literal commands:'
  rendered_contract_assert_product_contains conversation main-agent-mode claude 'agent-session activity doctor --agent claude --format json'
  rendered_contract_assert_product_contains conversation main-agent-mode claude 'agent-session activity setup --agent claude --repair --dry-run --format json'
  rendered_contract_assert_product_omits conversation main-agent-mode claude 'Codex'
  rendered_contract_assert_product_omits conversation main-agent-mode claude '--agent codex'

  for product in codex claude; do
    rendered="$REPO_ROOT/build/$product/plugins/conversation/skills/main-agent-mode/SKILL.md"
    golden="$REPO_ROOT/tests/golden/$product/plugins/conversation/skills/main-agent-mode/expected/SKILL.md"
    rendered_protocol="$REPO_ROOT/build/$product/plugins/conversation/skills/main-agent-mode/references/MAIN_AGENT_MODE_PROTOCOL.md"
    golden_protocol="$REPO_ROOT/tests/golden/$product/plugins/conversation/skills/main-agent-mode/expected/references/MAIN_AGENT_MODE_PROTOCOL.md"
    test -s "$rendered"
    test -s "$golden"
    cmp -s "$rendered" "$golden"
    test -s "$rendered_protocol"
    test -s "$golden_protocol"
    cmp -s "$protocol" "$rendered_protocol"
    cmp -s "$protocol" "$golden_protocol"
  done

  test ! -e "$REPO_ROOT/build/hermes/plugins/conversation/skills/main-agent-mode/SKILL.md"
  test ! -e "$REPO_ROOT/tests/golden/hermes/plugins/conversation/skills/main-agent-mode"
}

failures=0
record_case "conversation.discussion-to-implementation-doc" "workflow skill source and rendered surfaces exist for both products" run_conversation_skill_probe discussion-to-implementation-doc
record_case "conversation.guided-feature-build" "workflow skill source and rendered surfaces exist for both products" run_conversation_skill_probe guided-feature-build
record_case "conversation.handoff-session-prompt" "workflow skill source and rendered surfaces exist for both products" run_conversation_skill_probe handoff-session-prompt
record_case "conversation.outcome-routing" "normal conversation and guided build select advice, explanation, and delegation modes without child-skill selection" run_conversation_outcome_routing_probe
record_case "conversation.main-agent-mode" "explicit opt-in main-agent ownership, verified worker startup, stop rules, and Codex/Claude-only renders are enforced" run_main_agent_mode_probe

exit "$failures"
