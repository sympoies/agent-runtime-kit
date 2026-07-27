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

  grep -Fq 'Natural-language collaboration is the default.' "$home_policy"
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

assert_main_agent_v2_recovery_contract() {
  local contract_file="$1"
  local required_inputs_count
  local stale_schema

  required_inputs_count="$(grep -Fc 'recovery_action.required_inputs:[' "$contract_file")"
  if [ "$required_inputs_count" -ne 1 ]; then
    return 1
  fi
  if ! grep -Fq 'recovery_action.required_inputs:["terminalization_reason","idempotency_key"]' "$contract_file"; then
    return 1
  fi
  for stale_schema in \
    main-agent.worker-diagnose-result.v1 \
    main-agent.worker-supervise-result.v1 \
    main-agent.worker-recovery-action.v1 \
    main-agent.worker-reconcile-stopped-result.v1
  do
    if grep -Fq "$stale_schema" "$contract_file"; then
      return 1
    fi
  done
  return 0
}

assert_completed_terminal_receipt_replay_fixture() {
  local fixture="$1"

  grep -Fxq 'replay_kind=completed_v2_terminal_receipt' "$fixture" &&
    grep -Fxq 'same_request=true' "$fixture" &&
    grep -Fxq 'same_original_revision=true' "$fixture" &&
    grep -Fxq 'same_idempotency_key=true' "$fixture" &&
    grep -Fxq 'result=committed' "$fixture" &&
    grep -Fxq 'mutation_repeated=false' "$fixture"
}

assert_main_agent_replay_boundaries() {
  local contract_file="$1"
  local boundary

  for boundary in \
    'exact same request, original revision' \
    'same idempotency key' \
    'matching completed v2' \
    'returns that committed result' \
    'without repeating' \
    'New key, changed request' \
    'neither a matching completed v2' \
    'terminal receipt nor a matching strict progress receipt fails closed.' \
    'exact replay of an interrupted stage 1' \
    'validating a matching strict progress receipt' \
    'It must also' \
    'cancelled assignment' \
    'session-only quarantine' \
    'exact worker' \
    'stopped runtime' \
    'operation quiescence' \
    'current controller authority'
  do
    if ! grep -Fq "$boundary" "$contract_file"; then
      return 1
    fi
  done
  if grep -Fq 'sole stale-revision exception' "$contract_file"; then
    return 1
  fi
  return 0
}

run_main_agent_mode_probe() {
  local source="$REPO_ROOT/core/skills/conversation/main-agent-mode/SKILL.md.tera"
  local protocol="$REPO_ROOT/core/skills/conversation/main-agent-mode/references/MAIN_AGENT_MODE_PROTOCOL.md"
  local stale_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-stale-v1.md"
  local extra_input_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-extra-input.md"
  local completed_receipt_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-completed-receipt-replay.txt"
  local changed_request_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-completed-receipt-changed-request.txt"
  local product rendered golden rendered_protocol golden_protocol

  test -s "$source"
  test -s "$protocol"
  printf '%s\n' \
    'replay_kind=completed_v2_terminal_receipt' \
    'same_request=true' \
    'same_original_revision=true' \
    'same_idempotency_key=true' \
    'result=committed' \
    'mutation_repeated=false' >"$completed_receipt_fixture"
  assert_completed_terminal_receipt_replay_fixture "$completed_receipt_fixture"
  printf '%s\n' \
    'replay_kind=completed_v2_terminal_receipt' \
    'same_request=false' \
    'same_original_revision=true' \
    'same_idempotency_key=true' \
    'result=committed' \
    'mutation_repeated=false' >"$changed_request_fixture"
  if assert_completed_terminal_receipt_replay_fixture "$changed_request_fixture"; then
    return 1
  fi
  printf '%s\n' \
    'recovery_action.required_inputs:["terminalization_reason","idempotency_key"]' \
    'main-agent.worker-diagnose-result.v1' >"$stale_fixture"
  if assert_main_agent_v2_recovery_contract "$stale_fixture"; then
    return 1
  fi
  printf '%s\n' \
    'recovery_action.required_inputs:["terminalization_reason","idempotency_key"]' \
    'recovery_action.required_inputs:["terminalization_reason","idempotency_key","operator_override"]' \
    >"$extra_input_fixture"
  if assert_main_agent_v2_recovery_contract "$extra_input_fixture"; then
    return 1
  fi
  assert_main_agent_v2_recovery_contract "$source"
  assert_main_agent_v2_recovery_contract "$protocol"
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
  grep -Fq 'main-agent worker supervise <assignment-id> --format json' "$source"
  grep -Fq 'main-agent worker diagnose <assignment-id> --format json' "$protocol"
  grep -Fq '`recovery_action.kind`' "$protocol"
  grep -Fq '`recovery_action.executable:true`' "$protocol"
  grep -Fq '`recovery_action.required_inputs`' "$protocol"
  grep -Fq '`dependency-not-satisfied`' "$protocol"
  grep -Fq 'worker wait <dependency-id> --until terminal --timeout 60s' "$protocol"
  grep -Fq 'Only `accepted` or `released` satisfies a dependency.' "$protocol"
  grep -Fq 'main-agent worker request-changes <assignment-id>' "$protocol"
  grep -Fq 'changes only `submitted` to `working`' "$protocol"
  grep -Fq 'does not send review guidance, provider input, or re-arm auto-resume' "$protocol"
  grep -Fq 'main-agent worker message <assignment-id>' "$protocol"
  grep -Fq 'agent-session broker status --session "$AGENT_SESSION_ID" --format json' "$protocol"
  grep -Fq 'capability-failure-closed recovery lane' "$protocol"
  grep -Fq 'Service health, provider process health, provider session binding, and the Main relationship are four distinct states.' "$protocol"
  grep -Fq 'agent-session resume <session-id> --format json' "$protocol"
  grep -Fq 'post-rebind assignment ownership' "$protocol"
  grep -Fq 'run exact-controller `main-agent self recover` before attempting rebind' "$protocol"
  grep -Fq '`rebind` is reserved for a proven controller-incarnation mismatch' "$protocol"
  grep -Fq 'it is not a stale-broker recovery' "$protocol"
  grep -Fq 'classification' "$protocol"
  grep -Fq 'last_proven_safe_state' "$protocol"
  grep -Fq 'non-authoritative starting failure' "$protocol"
  grep -Fq 'A folded `readiness_failed` snapshot can be superseded' "$protocol"
  grep -Fq 'pending mailbox notification is not readiness proof' "$protocol"
  grep -Fq 'notification-pending' "$protocol"
  grep -Fq 'idle composer' "$protocol"
  grep -Fq 'stable dirty material plus stale provider progress is stalled' "$protocol"
  grep -Fq 'do not renew edit authority indefinitely' "$protocol"
  grep -Fq 'classification: post_claim_failure' "$protocol"
  grep -Fq 'last_proven_safe_state.post_claim_terminalization_safe: true' "$protocol"
  grep -Fq 'automatic_retry_safe: false' "$protocol"
  grep -Fq 'recovery_action.kind: stopped_worker_terminalization' "$protocol"
  grep -Fq 'recovery_action.required_inputs:["terminalization_reason","idempotency_key"]' "$protocol"
  grep -Fq 'main-agent worker reconcile-stopped <assignment-id>' "$protocol"
  grep -Fq -- '--reason <bounded-terminalization-reason>' "$protocol"
  grep -Fq '`main-agent.worker-diagnose-result.v2`' "$protocol"
  grep -Fq '`main-agent.worker-supervise-result.v2`' "$protocol"
  grep -Fq '`main-agent.worker-recovery-action.v2`' "$protocol"
  grep -Fq 'main-agent.worker-reconcile-stopped-result.v2' "$protocol"
  grep -Fq '`terminalized:true`' "$protocol"
  grep -Fq '`worker_claim_active_after:false`' "$protocol"
  grep -Fq 'active_disposition:"absent"' "$protocol"
  grep -Fq 'release_provenance:"not_attributed_to_attempt"' "$protocol"
  grep -Fq 'observed_at_stage1:<bool>' "$protocol"
  grep -Fq '`input_sent:false`' "$protocol"
  grep -Fq '`worktree_preserved:true`' "$protocol"
  grep -Fq 'session-only authority quarantine' "$protocol"
  grep -Fq 'frozen assignment schema v3' "$protocol"
  grep -Fq 'CLI and HTTP resume are denied while quarantined' "$protocol"
  grep -Fq 'observational coordination access does not renew generic claims or operations' "$protocol"
  grep -Fq 'exact original controller' "$protocol"
  grep -Fq 'explicit distinct successor' "$protocol"
  grep -Fq 'same current run, Main session, and incarnation' "$protocol"
  grep -Fq 'authorized retry rolls' "$protocol"
  grep -Fq 'orphaned progress forward' "$protocol"
  grep -Fq 'exact same request, original revision' "$protocol"
  grep -Fq 'same idempotency key' "$protocol"
  grep -Fq 'matching completed v2' "$protocol"
  grep -Fq 'returns that committed result' "$protocol"
  grep -Fq 'despite the now-stale' "$protocol"
  grep -Fq 'without repeating' "$protocol"
  grep -Fq 'New key, changed request' "$protocol"
  grep -Fq 'neither a matching completed v2' "$protocol"
  grep -Fq 'terminal receipt nor a matching strict progress receipt fails closed.' "$protocol"
  grep -Fq 'must retain the original' "$protocol"
  grep -Fq 'now-stale `--if-revision`' "$protocol"
  grep -Fq 'validating a matching' "$protocol"
  grep -Fq 'cancelled assignment' "$protocol"
  grep -Fq 'current controller authority' "$protocol"
  grep -Fq 'Refusal status alone does not report a safe state.' "$protocol"
  grep -Fq 'fresh v2 `worker diagnose` or `worker supervise` projection' "$protocol"
  grep -Fq 'unless an envelope explicitly exposes that proof' "$protocol"
  if grep -Fq 'worker_claim_revoked' "$protocol"; then
    return 1
  fi
  grep -Fq '`working` → `reconcile-stopped` → `cancelled` → `retire`' "$protocol"
  grep -Fq 'fences the exact stopped worker session authority against resume' "$protocol"
  grep -Fq 'Unrelated session, run, and coordination authority remains unchanged.' "$protocol"
  grep -Fq 'preserves the worktree, branch, diff, durable run, and Main session' "$protocol"
  grep -Fq 'A live or unknown runtime, or any active or uncertain operation, fails closed.' "$protocol"
  grep -Fq '`worker-runtime-still-live`' "$protocol"
  grep -Fq '`coordination-runtime-unverified`' "$protocol"
  grep -Fq '`worker-not-quiescent`' "$protocol"
  grep -Fq '`worker-incarnation-changed`' "$protocol"
  grep -Fq '`assignment-state-conflict`' "$protocol"
  grep -Fq 'retire the reconciled worker or create a distinct replacement assignment' "$protocol"
  grep -Fq 'Never use raw tmux, terminal input, group cleanup, or a B3 runtime-stop primitive' "$protocol"
  grep -Fq 'unchanged blocking fingerprint' "$protocol"
  grep -Fq 'preserve the full goal and unfinished checklist' "$protocol"
  grep -Fq 'account binding is verified before structured auto-resume is re-armed' "$protocol"
  grep -Fq 'Never use `/logout` or raw terminal input' "$protocol"
  grep -Fq 'Do not send a blind Enter' "$protocol"
  if grep -Fq 'No public review/revise action exists.' "$protocol"; then
    return 1
  fi
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
  grep -Fq 'Retire an accepted terminal worker only after the facade and' "$source"
  grep -Fq 'session-management owner prove no active or uncertain operation remains,' "$source"
  grep -Fq 'the durable logical-delete boundary' "$source"
  grep -Fq 'physical cleanup failures in the maintenance projection rather than the live' "$source"
  grep -Fq 'A submitted assignment with a released claim, clean worktree, terminated' "$source"
  grep -Fq 'do not renew mutation authority merely because supervision reports' "$source"
  grep -Fq '`claim_renewal_required`' "$source"
  grep -Fq '`post_claim_failure`' "$source"
  grep -Fq '`last_proven_safe_state.post_claim_terminalization_safe:true`' "$source"
  grep -Fq '`automatic_retry_safe:false`' "$source"
  grep -Fq '`recovery_action.kind:"stopped_worker_terminalization"`' "$source"
  grep -Fq 'recovery_action.required_inputs:["terminalization_reason","idempotency_key"]' "$source"
  grep -Fq 'main-agent worker reconcile-stopped <assignment-id>' "$source"
  grep -Fq -- '--reason <bounded-terminalization-reason>' "$source"
  grep -Fq '`main-agent.worker-diagnose-result.v2`' "$source"
  grep -Fq '`main-agent.worker-supervise-result.v2`' "$source"
  grep -Fq '`main-agent.worker-recovery-action.v2`' "$source"
  grep -Fq '`main-agent.worker-reconcile-stopped-result.v2`' "$source"
  grep -Fq '`terminalized:true`' "$source"
  grep -Fq '`worker_claim_active_after:false`' "$source"
  grep -Fq 'active_disposition:"absent"' "$source"
  grep -Fq 'release_provenance:"not_attributed_to_attempt"' "$source"
  grep -Fq 'observed_at_stage1:<bool>' "$source"
  grep -Fq '`input_sent:false`' "$source"
  grep -Fq '`worktree_preserved:true`' "$source"
  grep -Fq 'session-only authority quarantine' "$source"
  grep -Fq 'frozen assignment schema v3' "$source"
  grep -Fq 'CLI and HTTP resume are denied while quarantined' "$source"
  grep -Fq 'observational coordination access does not renew generic claims or operations' "$source"
  grep -Fq 'exact original controller' "$source"
  grep -Fq 'explicit distinct successor' "$source"
  grep -Fq 'same current run, Main session, and incarnation' "$source"
  grep -Fq 'authorized replay rolls' "$source"
  grep -Fq 'orphaned progress forward' "$source"
  grep -Fq 'exact same request, original revision' "$source"
  grep -Fq 'same idempotency key' "$source"
  grep -Fq 'matching completed v2' "$source"
  grep -Fq 'returns that committed result' "$source"
  grep -Fq 'despite the now-stale' "$source"
  grep -Fq 'without repeating' "$source"
  grep -Fq 'New key, changed request' "$source"
  grep -Fq 'neither a matching completed v2' "$source"
  grep -Fq 'terminal receipt nor a matching strict progress receipt fails closed.' "$source"
  grep -Fq 'must retain the original' "$source"
  grep -Fq 'now-stale `--if-revision`' "$source"
  grep -Fq 'validating a matching' "$source"
  grep -Fq 'cancelled assignment' "$source"
  grep -Fq 'current controller authority' "$source"
  grep -Fq 'Refusal status alone does not report a safe state.' "$source"
  grep -Fq 'fresh v2 `worker diagnose` or `worker supervise` projection' "$source"
  grep -Fq 'unless an envelope explicitly exposes that proof' "$source"
  if grep -Fq 'worker_claim_revoked' "$source"; then
    return 1
  fi
  grep -Fq '`worker-runtime-still-live`' "$source"
  grep -Fq '`coordination-runtime-unverified`' "$source"
  grep -Fq '`worker-not-quiescent`' "$source"
  grep -Fq '`worker-incarnation-changed`' "$source"
  grep -Fq '`assignment-state-conflict`' "$source"
  grep -Fq 'fences the exact worker session authority against resume' "$source"
  grep -Fq 'Unrelated session, run, and coordination authority remains unchanged.' "$source"
  grep -Fq 'preserves its worktree, branch, diff, the durable run, and the Main session' "$source"
  grep -Fq 'live or unknown runtime, or any active or uncertain operation' "$source"
  grep -Fq 'retire that reconciled worker or create a distinct replacement assignment' "$source"
  grep -Fq 'Never use raw tmux, terminal input, group cleanup, or a B3 runtime-stop primitive' "$source"
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
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'main-agent worker supervise <assignment-id> --format json'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`recovery_action.kind`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`dependency-not-satisfied`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`main-agent worker request-changes`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'does not send review guidance, provider input, or re-arm auto-resume'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'state:"submitted"'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'main-agent self recover` before attempting rebind'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`rebind` is reserved for a proven controller-incarnation mismatch'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'capability-failure-closed recovery lane'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'post-rebind assignment ownership'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'stable dirty material plus stale provider progress is stalled'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`claim_renewal_required`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`post_claim_failure`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`last_proven_safe_state.post_claim_terminalization_safe:true`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`automatic_retry_safe:false`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`recovery_action.kind:"stopped_worker_terminalization"`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`main-agent.worker-diagnose-result.v2`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`main-agent.worker-supervise-result.v2`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`main-agent.worker-recovery-action.v2`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'main-agent worker reconcile-stopped <assignment-id>'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '--reason <bounded-terminalization-reason>'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`main-agent.worker-reconcile-stopped-result.v2`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'recovery_action.required_inputs:["terminalization_reason","idempotency_key"]'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`worker_claim_active_after:false`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'active_disposition:"absent"'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'release_provenance:"not_attributed_to_attempt"'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'frozen assignment schema v3'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'CLI and HTTP resume are denied while quarantined'
    rendered_contract_assert_product_omits conversation main-agent-mode "$product" 'worker_claim_revoked'
    rendered_contract_assert_product_omits conversation main-agent-mode "$product" 'main-agent.worker-diagnose-result.v1'
    rendered_contract_assert_product_omits conversation main-agent-mode "$product" 'main-agent.worker-supervise-result.v1'
    rendered_contract_assert_product_omits conversation main-agent-mode "$product" 'main-agent.worker-recovery-action.v1'
    rendered_contract_assert_product_omits conversation main-agent-mode "$product" 'main-agent.worker-reconcile-stopped-result.v1'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`input_sent:false`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`worktree_preserved:true`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'matching completed v2 terminal receipt'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'without repeating mutation'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'live or unknown runtime, or any active or uncertain operation'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'Never use raw tmux, terminal input, group cleanup, or a B3 runtime-stop primitive'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'Never use `/logout` or raw terminal input'
  done

  for product in codex claude; do
    rendered="$REPO_ROOT/build/$product/plugins/conversation/skills/main-agent-mode/SKILL.md"
    golden="$REPO_ROOT/tests/golden/$product/plugins/conversation/skills/main-agent-mode/expected/SKILL.md"
    rendered_protocol="$REPO_ROOT/build/$product/plugins/conversation/skills/main-agent-mode/references/MAIN_AGENT_MODE_PROTOCOL.md"
    golden_protocol="$REPO_ROOT/tests/golden/$product/plugins/conversation/skills/main-agent-mode/expected/references/MAIN_AGENT_MODE_PROTOCOL.md"
    test -s "$rendered"
    test -s "$golden"
    assert_main_agent_v2_recovery_contract "$rendered"
    assert_main_agent_v2_recovery_contract "$golden"
    assert_main_agent_replay_boundaries "$rendered"
    assert_main_agent_replay_boundaries "$golden"
    cmp -s "$rendered" "$golden"
    test -s "$rendered_protocol"
    test -s "$golden_protocol"
    assert_main_agent_v2_recovery_contract "$rendered_protocol"
    assert_main_agent_v2_recovery_contract "$golden_protocol"
    assert_main_agent_replay_boundaries "$rendered_protocol"
    assert_main_agent_replay_boundaries "$golden_protocol"
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
record_case "conversation.main-agent-mode" "explicit opt-in main-agent ownership, verified worker startup, post-claim terminalization, stop rules, and Codex/Claude-only renders are enforced" run_main_agent_mode_probe

exit "$failures"
