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

assert_normalized_contract_clause() {
  local contract_file="$1"
  local clause="$2"

  awk '{ printf "%s ", $0 } END { print "" }' "$contract_file" |
    tr -s ' ' |
    grep -Fq "$clause"
}

assert_main_agent_mode_gate_contract() {
  assert_normalized_contract_clause "$1" \
    'A controller observed in `enforce`, `off`, or an unknown mode fails the pre-init gate.'
}

assert_main_agent_preinit_observation_contract() {
  assert_normalized_contract_clause "$1" \
    'Immediately before every `main-agent init` branch, run `agent-session list --format json` and require `cli.agent-session.list.v1` to bind the exact controller session ID, incarnation, and canonical cwd;' &&
    grep -Fq '`session-management.controller-mode-observation.v1`' "$1" &&
    grep -Fq '`session-management.controller-mode-observation-result.v1`' "$1" &&
    grep -Fq '`mode_source:"runtime-observed"`' "$1" &&
    grep -Fq '`fresh:true`' "$1" &&
    grep -Fq '`observed_mode:"advisory"`' "$1" &&
    assert_normalized_contract_clause "$1" \
      'A missing capability, wrong cwd, unbound or stale identity, `mode_source:"requested"` or `mode_source:"configured"`, or observed `enforce`, `off`, or unknown mode fails closed before `main-agent init`.'
}

assert_main_agent_wrong_mode_cleanup_contract() {
  assert_main_agent_mode_gate_contract "$1" &&
    assert_normalized_contract_clause "$1" \
      'Before closing it, the session owner must prove the exact controller session and incarnation, broker zero active and zero uncertain operations, no unfinished typed lifecycle transition, and no unique unpreserved material.' &&
    assert_normalized_contract_clause "$1" 'Authenticated claim inventory must also prove that every claim bound to that exact controller session and incarnation is absent or explicitly transferred/released through its typed owner, including any unrelated successor claim.' &&
    assert_normalized_contract_clause "$1" 'Unknown inventory or any surviving claim retains the controller and fails closed.' &&
    assert_normalized_contract_clause "$1" \
      'Only then close that exact session through its owner, require fresh-list absence, remove its clean controller worktree with `git-cli` when it has no retained purpose, and restart once in `advisory` before attempting `init`.' &&
    assert_normalized_contract_clause "$1" \
      'Missing or ambiguous proof retains the session and worktree and fails closed;'
}

assert_main_agent_prerun_restart_contract() {
  assert_normalized_contract_clause "$1" \
    'A failed controller startup before `main-agent init` may be deleted and restarted once with a compact prompt that points to the private full packet only when no run claim or assignment exists, the broker proves zero active and zero uncertain operations, no unfinished typed lifecycle transition exists, no unique unpreserved worktree material exists, and authenticated claim inventory proves every claim bound to the exact controller session and incarnation is absent or explicitly transferred/released.' &&
    assert_normalized_contract_clause "$1" \
      'This is a controller pre-init recovery, never a worker-start recovery.'
}

assert_main_agent_prerun_restart_replay_contract() {
  grep -Fq '`session-management.failed-controller-restart.v1`' "$1" &&
    grep -Fq '`session-management.failed-controller-restart-result.v1`' "$1" &&
    assert_normalized_contract_clause "$1" 'Every pre-init close-and-restart branch, including a wrong-mode branch, must use this restart-once boundary.' &&
    assert_normalized_contract_clause "$1" 'immutable request digest and durable consumed/idempotency marker' &&
    assert_normalized_contract_clause "$1" 'restart owner, failed controller session ID and incarnation, canonical cwd and controller worktree, requested `advisory` mode, compact prompt and private-packet reference digest, and authenticated claim-inventory projection' &&
    assert_normalized_contract_clause "$1" 'Any changed request field is rejected before deletion or restart.' &&
    assert_normalized_contract_clause "$1" 'consumed before the first destructive stage' &&
    assert_normalized_contract_clause "$1" 'Identical replay returns the same receipt' &&
    assert_normalized_contract_clause "$1" 'partial progress resumes only the recorded remaining stage' &&
    assert_normalized_contract_clause "$1" 'ambiguous restart outcome retains the exact session and fails closed' &&
    assert_normalized_contract_clause "$1" 'If that owner primitive is absent'
}

assert_main_agent_folded_input_contract() {
  grep -Fq 'prefer the folded readiness boundary' "$1" &&
    ! grep -Fq 'require the folded readiness boundary' "$1" &&
    assert_normalized_contract_clause "$1" \
    'Before input, a privacy-safe observation must prove the exact already-delivered prompt at an idle composer, the broker must prove zero active and zero uncertain operations, and the observation must classify the surface as an ordinary provider composer rather than a trust, authentication, account, permission, secret, provider-mutation, startup-dialog, or unknown state.' &&
    grep -Fq '`input_sent:true`' "$1" &&
    assert_normalized_contract_clause "$1" \
      'trusted released session-management owner' &&
    grep -Fq '`composer_state:"idle"`' "$1" &&
    grep -Fq '`sensitive_dialog:false`' "$1" &&
    grep -Fq '`broker_active:0`' "$1" &&
    grep -Fq '`broker_uncertain:0`' "$1" &&
    assert_normalized_contract_clause "$1" 'atomic consumed-before-input marker' &&
    grep -Fq '`attempt_count:1`' "$1" &&
    grep -Fq 'normalizes into the same readiness' "$1" &&
    assert_normalized_contract_clause "$1" \
      'Missing or forged capability, producer, binding, or fields'
}

assert_main_agent_fallback_owner_contract() {
  assert_normalized_contract_clause "$1" 'trusted released session-management owner' &&
    assert_normalized_contract_clause "$1" 'owner-advertised exact invocation' &&
    assert_normalized_contract_clause "$1" 'authenticated producer identity' &&
    assert_normalized_contract_clause "$1" 'request digest' &&
    assert_normalized_contract_clause "$1" 'atomic consumed-before-input marker' &&
    grep -Fq '`attempted:true`' "$1" &&
    grep -Fq '`attempt_count:1`' "$1" &&
    grep -Fq '`input_sent:true`' "$1" &&
    assert_normalized_contract_clause "$1" 'A failure receipt reports `input_sent:false`' &&
    assert_normalized_contract_clause "$1" 'replay returns the prior receipt without input' &&
    assert_normalized_contract_clause "$1" 'Self-asserted schema strings, peer prose, or an unadvertised command never grant terminal-input authority.' &&
    assert_normalized_contract_clause "$1" 'Without that executable owner capability, Main Agent Mode is unavailable for the fallback.'
}

assert_main_agent_incarnation_single_use_contract() {
  assert_normalized_contract_clause "$1" \
    'The durable consumed marker is keyed by exact session ID plus incarnation, independent of prompt fingerprint; any existing marker for that incarnation rejects every later request before input, even with a different prompt fingerprint or idempotency key.'
}

assert_main_agent_mailbox_contract() {
  assert_normalized_contract_clause "$1" \
    'Because fixed terminal notification delivery deliberately waits for a no-claim safe-input boundary, a Main controller with an active claim must inspect and disposition its authenticated mailbox before returning to an idle waiting prompt.' &&
    assert_normalized_contract_clause "$1" \
      'Do not release or widen the claim, send terminal input, or infer message consumption merely to trigger that notification.'
}

assert_main_agent_mailbox_owner_contract() {
  assert_normalized_contract_clause "$1" 'agent-session message inbox --session "$AGENT_SESSION_ID"' &&
    grep -Fq '`cli.agent-session.message-inbox.v1`' "$1" &&
    assert_normalized_contract_clause "$1" 'agent-session message show --session "$AGENT_SESSION_ID" --message <message-id>' &&
    grep -Fq '`cli.agent-session.message-show.v1`' "$1" &&
    assert_normalized_contract_clause "$1" 'agent-session message ack --session "$AGENT_SESSION_ID" --message <message-id>' &&
    grep -Fq '`cli.agent-session.message-ack.v1`' "$1" &&
    assert_normalized_contract_clause "$1" 'inbox metadata first' &&
    assert_normalized_contract_clause "$1" 'exact current recipient session and incarnation' &&
    grep -Fq '`sender.authenticated:true`' "$1" &&
    assert_normalized_contract_clause "$1" 'show only a material message body' &&
    assert_normalized_contract_clause "$1" 'revision-CAS and stable idempotency key' &&
    assert_normalized_contract_clause "$1" 'forged sender, wrong recipient or incarnation, stale revision, or non-material message fails closed'
}

assert_main_agent_controller_matrix_contract() {
  grep -Fq '| Pre-init controller startup failed before `main-agent init` |' "$1" &&
    grep -Fq 'This controller-only recovery requires no run claim or assignment, broker zero active/zero uncertain, no unfinished typed lifecycle transition, no unique unpreserved material, and authenticated claim inventory proving all exact-session/incarnation claims absent or transferred/released.' "$1" &&
    ! grep -Fq '| Pre-run startup failed' "$1"
}

assert_main_agent_post_delivery_contract() {
  assert_normalized_contract_clause "$1" \
    'Because the response-hosting turn has no post-delivery callback, its final response must explicitly hand off the retained disposition `controller cleanup pending` to an already-authenticated session-management owner and must not claim that physical cleanup ran.' &&
    assert_normalized_contract_clause "$1" \
      'In a later authenticated owner turn, after result delivery, that owner must prove broker zero active and zero uncertain operations, no unfinished typed lifecycle transition, no unique unpreserved material, and authenticated claim inventory proving every claim bound to the exact controller session and incarnation is absent or explicitly transferred/released, including any unrelated successor claim preserved by closeout;' &&
    assert_normalized_contract_clause "$1" \
      'Until a subsequent authenticated read-back proves every stage, lifecycle cleanup is pending and no owner may claim physical closeout complete.' &&
    ! grep -Fq 'main-agent.post-delivery-cleanup-receipt.v1' "$1"
}

assert_main_agent_cleanup_handoff_contract() {
  assert_normalized_contract_clause "$1" 'Facade logical live-worker absence is not physical session-owner absence' &&
    assert_normalized_contract_clause "$1" '`cleanup_pending:false` covers only run and worker cleanup' &&
    assert_normalized_contract_clause "$1" 'every claim bound to the exact controller session and incarnation' &&
    assert_normalized_contract_clause "$1" 'unrelated successor claim' &&
    grep -Fq '`session-management.controller-cleanup-handoff.v1`' "$1" &&
    grep -Fq '`main-agent.controller-cleanup-handoff.v1`' "$1" &&
    grep -Fq '`session-management.controller-cleanup-handoff-result.v1`' "$1" &&
    assert_normalized_contract_clause "$1" 'exact persist and consume invocations' &&
    assert_normalized_contract_clause "$1" 'producer and recipient-owner identities, run ID and revision, controller session and incarnation, canonical controller worktree, remaining cleanup stages, request digest, and idempotency key' &&
    assert_normalized_contract_clause "$1" 'Identical persist replay returns the same receipt' &&
    assert_normalized_contract_clause "$1" 'altered identity, worktree, run revision, cleanup stages, digest, recipient, or key fails closed' &&
    assert_normalized_contract_clause "$1" 'passes that opaque reference, matching run/controller bindings, persisted revision, and a consume idempotency key to the exact consume invocation' &&
    assert_normalized_contract_clause "$1" 'atomically consumes the handoff reference before the first destructive stage' &&
    assert_normalized_contract_clause "$1" 'authenticated progress receipt containing the request digest, consume key, original persisted revision, and completed stages' &&
    assert_normalized_contract_clause "$1" 'Identical consume replay returns that receipt and resumes only uncommitted stages.' &&
    assert_normalized_contract_clause "$1" 'interrupted consume after session deletion reconciles exact-session absence through fresh authenticated identity/list evidence and never repeats deletion' &&
    assert_normalized_contract_clause "$1" 'changed reference, identity, revision, digest, or consume key fails before mutation' &&
    assert_normalized_contract_clause "$1" 'authenticated result read-back with matching run/controller bindings and revision' &&
    assert_normalized_contract_clause "$1" 'bounded cleanup status and opaque handoff reference' &&
    assert_normalized_contract_clause "$1" 'never a private path or unauthenticated deletion instruction'
}

assert_main_agent_nonzero_wrong_mode_contract() {
  assert_normalized_contract_clause "$1" 'post-init wrong-mode incident with one or more assignments' &&
    assert_normalized_contract_clause "$1" 'freeze every new launch and Main-owned mutation' &&
    assert_normalized_contract_clause "$1" 'preserve every worker, claim, worktree, and unique material' &&
    assert_normalized_contract_clause "$1" 'reconcile active or uncertain operations only through their exact owners' &&
    assert_normalized_contract_clause "$1" 'Never use zero-assignment closeout for a nonzero run' &&
    assert_normalized_contract_clause "$1" '`starting`, `working`, `submitted`, and `accepted`' &&
    grep -Fq '`main-agent.nonzero-wrong-mode-recovery.v1`' "$1" &&
    grep -Fq '`main-agent.nonzero-wrong-mode-recovery-result.v1`' "$1" &&
    assert_normalized_contract_clause "$1" 'exact owner-supplied invocation' &&
    assert_normalized_contract_clause "$1" 'revision-CAS request' &&
    assert_normalized_contract_clause "$1" 'immutable assignment ID/revision/state snapshot' &&
    assert_normalized_contract_clause "$1" 'one typed-owner receipt per assignment' &&
    assert_normalized_contract_clause "$1" 'durably consumes a progress marker keyed by the full request digest, original run and assignment revisions, and idempotency key' &&
    assert_normalized_contract_clause "$1" 'authenticated progress receipt records completed assignment stages and their typed-owner receipts' &&
    assert_normalized_contract_clause "$1" 'Identical replay accepts that receipt across the now-stale original revisions and resumes only uncommitted stages' &&
    assert_normalized_contract_clause "$1" 'A partial result preserves its committed stages, freezes every remaining stage' &&
    assert_normalized_contract_clause "$1" 'an ambiguous stage is never repeated until its exact typed owner proves whether it committed' &&
    assert_normalized_contract_clause "$1" 'executable typed owner recovery is unavailable, retain the run unchanged and fail closed'
}

assert_main_agent_preinit_observation_fixture() {
  grep -Fxq 'ordering_immediately_before_init=true' "$1" &&
    grep -Fxq 'wrong_cwd_rejected=true' "$1" &&
    grep -Fxq 'unbound_identity_rejected=true' "$1" &&
    grep -Fxq 'observed_enforce_rejected=true' "$1"
}

assert_main_agent_fallback_owner_fixture() {
  grep -Fxq 'missing_binding_rejected=true' "$1" &&
    grep -Fxq 'mismatched_identity_prompt_rejected=true' "$1" &&
    grep -Fxq 'forged_or_missing_capability_rejected=true' "$1" &&
    grep -Fxq 'attempted_false_rejected=true' "$1" &&
    grep -Fxq 'sensitive_or_unknown_surface_rejected=true' "$1" &&
    grep -Fxq 'replay_input_rejected=true' "$1"
}

assert_main_agent_prerun_restart_fixture() {
  grep -Fxq 'first_attempt_marker_consumed=true' "$1" &&
    grep -Fxq 'surviving_claim_rejected=true' "$1" &&
    grep -Fxq 'changed_restart_request_rejected=true' "$1" &&
    grep -Fxq 'identical_replay_repeats_mutation=false' "$1" &&
    grep -Fxq 'ambiguous_restart_retries=false' "$1"
}

assert_main_agent_mailbox_fixture() {
  grep -Fxq 'forged_sender_rejected=true' "$1" &&
    grep -Fxq 'wrong_recipient_incarnation_rejected=true' "$1" &&
    grep -Fxq 'stale_revision_rejected=true' "$1" &&
    grep -Fxq 'non_material_body_shown=false' "$1"
}

assert_main_agent_cleanup_fixture() {
  grep -Fxq 'tombstoned_physical_session_present_complete=false' "$1" &&
    grep -Fxq 'active_successor_claim_delete_allowed=false' "$1" &&
    grep -Fxq 'altered_identity_worktree_revision_rejected=true' "$1" &&
    grep -Fxq 'unadvertised_persist_consume_rejected=true' "$1" &&
    grep -Fxq 'interrupted_consume_repeats_delete=false' "$1" &&
    grep -Fxq 'changed_consume_request_mutates=false' "$1" &&
    grep -Fxq 'replay_repeats_cleanup=false' "$1"
}

assert_main_agent_nonzero_wrong_mode_fixture() {
  grep -Fxq 'starting_preserved=true' "$1" &&
    grep -Fxq 'working_preserved=true' "$1" &&
    grep -Fxq 'submitted_preserved=true' "$1" &&
    grep -Fxq 'accepted_preserved=true' "$1" &&
    grep -Fxq 'typed_owner_receipts_bound=true' "$1" &&
    grep -Fxq 'changed_snapshot_rejected=true' "$1" &&
    grep -Fxq 'first_assignment_stage_committed=true' "$1" &&
    grep -Fxq 'replay_resumes_only_second_stage=true' "$1" &&
    grep -Fxq 'new_key_repeats_first_stage=false' "$1" &&
    grep -Fxq 'zero_assignment_closeout_used=false' "$1"
}

assert_main_agent_controller_recovery_contract() {
  local contract_file="$1"

  grep -Fq 'Main controller uses `advisory`; every isolated implementation worker uses `enforce`.' "$contract_file" &&
  assert_main_agent_wrong_mode_cleanup_contract "$contract_file" &&
    assert_main_agent_preinit_observation_contract "$contract_file" &&
    assert_main_agent_prerun_restart_contract "$contract_file" &&
    assert_main_agent_prerun_restart_replay_contract "$contract_file" &&
    assert_main_agent_folded_input_contract "$contract_file" &&
    assert_main_agent_fallback_owner_contract "$contract_file" &&
    assert_main_agent_incarnation_single_use_contract "$contract_file" &&
    assert_main_agent_mailbox_contract "$contract_file" &&
    assert_main_agent_mailbox_owner_contract "$contract_file" &&
    assert_main_agent_post_delivery_contract "$contract_file" &&
    assert_main_agent_cleanup_handoff_contract "$contract_file" &&
    assert_main_agent_nonzero_wrong_mode_contract "$contract_file" &&
    grep -Fq 'post-init controller-mode mismatch' "$contract_file" &&
    grep -Fq 'checkpoint a zero-assignment blocker' "$contract_file" &&
    grep -Fq 'explicit authority boundaries' "$contract_file" &&
    grep -Fq 'Never close or delete an owner' "$contract_file" &&
    grep -Fq '`workers_absent:true`' "$contract_file" &&
    grep -Fq '`cleanup_pending:true`' "$contract_file" &&
    assert_normalized_contract_clause "$contract_file" 'typed maintenance tombstone'
}

run_main_agent_mode_probe() {
  local source="$REPO_ROOT/core/skills/conversation/main-agent-mode/SKILL.md.tera"
  local protocol="$REPO_ROOT/core/skills/conversation/main-agent-mode/references/MAIN_AGENT_MODE_PROTOCOL.md"
  local e2e_plan="$REPO_ROOT/docs/discussions/2026-07-27-main-agent-fresh-session-e2e-plan.md"
  local closeout_design="$REPO_ROOT/docs/discussions/2026-07-29-main-agent-closeout-macro.md"
  local stale_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-stale-v1.md"
  local extra_input_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-extra-input.md"
  local completed_receipt_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-completed-receipt-replay.txt"
  local changed_request_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-completed-receipt-changed-request.txt"
  local wrong_mode_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-wrong-mode-near-miss.md"
  local misplaced_restart_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-misplaced-restart-near-miss.md"
  local unsafe_input_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-unsafe-input-near-miss.md"
  local deferred_mailbox_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-deferred-mailbox-near-miss.md"
  local premature_cleanup_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-premature-cleanup-near-miss.md"
  local replayed_submit_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-replayed-submit-near-miss.md"
  local preinit_observation_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-preinit-observation.txt"
  local preinit_observation_near_miss="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-preinit-observation-near-miss.txt"
  local fallback_owner_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-fallback-owner.txt"
  local fallback_owner_near_miss="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-fallback-owner-near-miss.txt"
  local prerun_restart_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-prerun-restart.txt"
  local prerun_restart_near_miss="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-prerun-restart-near-miss.txt"
  local mailbox_owner_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-mailbox-owner.txt"
  local mailbox_owner_near_miss="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-mailbox-owner-near-miss.txt"
  local cleanup_handoff_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-cleanup-handoff.txt"
  local cleanup_handoff_near_miss="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-cleanup-handoff-near-miss.txt"
  local nonzero_wrong_mode_fixture="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-nonzero-wrong-mode.txt"
  local nonzero_wrong_mode_near_miss="$CONVERSATION_ARTIFACTS_DIR/main-agent-mode-nonzero-wrong-mode-near-miss.txt"
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
  printf '%s\n' \
    'A controller observed in `enforce`, `off`, or an unknown mode fails the pre-init gate.' \
    'Close that session first, then inspect broker state and unique material before restarting once in advisory.' \
    >"$wrong_mode_fixture"
  if assert_main_agent_wrong_mode_cleanup_contract "$wrong_mode_fixture"; then
    return 1
  fi
  printf '%s\n' \
    'After assignment creation, a failed worker startup may restart once with no active operations and no unique material.' \
    >"$misplaced_restart_fixture"
  if assert_main_agent_prerun_restart_contract "$misplaced_restart_fixture"; then
    return 1
  fi
  printf '%s\n' \
    'Before input, the exact prompt is visible at an idle composer, but active and uncertain operations and trust dialogs may be accepted.' \
    >"$unsafe_input_fixture"
  if assert_main_agent_folded_input_contract "$unsafe_input_fixture"; then
    return 1
  fi
  printf '%s\n' \
    'The same session incarnation may consume prompt fingerprint A with attempt_count:1.' \
    'A changed prompt fingerprint B may start a new attempt_count:1 for that incarnation.' \
    >"$replayed_submit_fixture"
  if assert_main_agent_incarnation_single_use_contract "$replayed_submit_fixture"; then
    return 1
  fi
  printf '%s\n' \
    'Because fixed terminal notification delivery deliberately waits for a no-claim safe-input boundary, a Main controller with an active claim may inspect and disposition its authenticated mailbox before returning to an idle waiting prompt.' \
    'Do not release or widen the claim, send terminal input, or infer message consumption merely to trigger that notification.' \
    >"$deferred_mailbox_fixture"
  if assert_main_agent_mailbox_contract "$deferred_mailbox_fixture"; then
    return 1
  fi
  printf '%s\n' \
    'The response-hosting turn claims cleanup complete, then deletes the exact controller before broker zero/zero and fresh-list absence.' \
    >"$premature_cleanup_fixture"
  if assert_main_agent_post_delivery_contract "$premature_cleanup_fixture"; then
    return 1
  fi
  printf '%s\n' \
    'ordering_immediately_before_init=true' \
    'wrong_cwd_rejected=true' \
    'unbound_identity_rejected=true' \
    'observed_enforce_rejected=true' >"$preinit_observation_fixture"
  assert_main_agent_preinit_observation_fixture "$preinit_observation_fixture"
  printf '%s\n' \
    'ordering_immediately_before_init=false' \
    'wrong_cwd_rejected=false' \
    'unbound_identity_rejected=false' \
    'observed_enforce_rejected=false' >"$preinit_observation_near_miss"
  if assert_main_agent_preinit_observation_fixture "$preinit_observation_near_miss"; then return 1; fi
  printf '%s\n' \
    'missing_binding_rejected=true' \
    'mismatched_identity_prompt_rejected=true' \
    'forged_or_missing_capability_rejected=true' \
    'attempted_false_rejected=true' \
    'sensitive_or_unknown_surface_rejected=true' \
    'replay_input_rejected=true' >"$fallback_owner_fixture"
  assert_main_agent_fallback_owner_fixture "$fallback_owner_fixture"
  printf '%s\n' \
    'missing_binding_rejected=false' \
    'mismatched_identity_prompt_rejected=false' \
    'forged_or_missing_capability_rejected=false' \
    'attempted_false_rejected=false' \
    'sensitive_or_unknown_surface_rejected=false' \
    'replay_input_rejected=false' >"$fallback_owner_near_miss"
  if assert_main_agent_fallback_owner_fixture "$fallback_owner_near_miss"; then return 1; fi
  printf '%s\n' \
    'first_attempt_marker_consumed=true' \
    'surviving_claim_rejected=true' \
    'changed_restart_request_rejected=true' \
    'identical_replay_repeats_mutation=false' \
    'ambiguous_restart_retries=false' >"$prerun_restart_fixture"
  assert_main_agent_prerun_restart_fixture "$prerun_restart_fixture"
  printf '%s\n' \
    'first_attempt_marker_consumed=false' \
    'surviving_claim_rejected=false' \
    'changed_restart_request_rejected=false' \
    'identical_replay_repeats_mutation=true' \
    'ambiguous_restart_retries=true' >"$prerun_restart_near_miss"
  if assert_main_agent_prerun_restart_fixture "$prerun_restart_near_miss"; then return 1; fi
  printf '%s\n' \
    'forged_sender_rejected=true' \
    'wrong_recipient_incarnation_rejected=true' \
    'stale_revision_rejected=true' \
    'non_material_body_shown=false' >"$mailbox_owner_fixture"
  assert_main_agent_mailbox_fixture "$mailbox_owner_fixture"
  printf '%s\n' \
    'forged_sender_rejected=false' \
    'wrong_recipient_incarnation_rejected=false' \
    'stale_revision_rejected=false' \
    'non_material_body_shown=true' >"$mailbox_owner_near_miss"
  if assert_main_agent_mailbox_fixture "$mailbox_owner_near_miss"; then return 1; fi
  printf '%s\n' \
    'tombstoned_physical_session_present_complete=false' \
    'active_successor_claim_delete_allowed=false' \
    'altered_identity_worktree_revision_rejected=true' \
    'unadvertised_persist_consume_rejected=true' \
    'interrupted_consume_repeats_delete=false' \
    'changed_consume_request_mutates=false' \
    'replay_repeats_cleanup=false' >"$cleanup_handoff_fixture"
  assert_main_agent_cleanup_fixture "$cleanup_handoff_fixture"
  printf '%s\n' \
    'tombstoned_physical_session_present_complete=true' \
    'active_successor_claim_delete_allowed=true' \
    'altered_identity_worktree_revision_rejected=false' \
    'unadvertised_persist_consume_rejected=false' \
    'interrupted_consume_repeats_delete=true' \
    'changed_consume_request_mutates=true' \
    'replay_repeats_cleanup=true' >"$cleanup_handoff_near_miss"
  if assert_main_agent_cleanup_fixture "$cleanup_handoff_near_miss"; then return 1; fi
  printf '%s\n' \
    'starting_preserved=true' \
    'working_preserved=true' \
    'submitted_preserved=true' \
    'accepted_preserved=true' \
    'typed_owner_receipts_bound=true' \
    'changed_snapshot_rejected=true' \
    'first_assignment_stage_committed=true' \
    'replay_resumes_only_second_stage=true' \
    'new_key_repeats_first_stage=false' \
    'zero_assignment_closeout_used=false' >"$nonzero_wrong_mode_fixture"
  assert_main_agent_nonzero_wrong_mode_fixture "$nonzero_wrong_mode_fixture"
  printf '%s\n' \
    'starting_preserved=false' \
    'working_preserved=false' \
    'submitted_preserved=false' \
    'accepted_preserved=false' \
    'typed_owner_receipts_bound=false' \
    'changed_snapshot_rejected=false' \
    'first_assignment_stage_committed=false' \
    'replay_resumes_only_second_stage=false' \
    'new_key_repeats_first_stage=true' \
    'zero_assignment_closeout_used=true' >"$nonzero_wrong_mode_near_miss"
  if assert_main_agent_nonzero_wrong_mode_fixture "$nonzero_wrong_mode_near_miss"; then return 1; fi
  assert_main_agent_v2_recovery_contract "$source"
  assert_main_agent_v2_recovery_contract "$protocol"
  assert_main_agent_controller_recovery_contract "$source"
  assert_main_agent_controller_recovery_contract "$protocol"
  assert_main_agent_controller_matrix_contract "$protocol"
  grep -Fq '## Milestone 1 — Pragmatic Codex Daily-use Cutline' "$e2e_plan"
  grep -Fq 'F34 exact-owner reconciliation' "$e2e_plan"
  grep -Fq 'acceptance of the prepared F22/F33 repair' "$e2e_plan"
  grep -Fq 'one deterministic provider-free happy path' "$e2e_plan"
  grep -Fq 'do not open another one for the cutline' "$e2e_plan"
  grep -Fq 'does not change the blocker inventory or its F18 owner' "$e2e_plan"
  grep -Fq 'Satisfying this milestone does not complete the full cross-product E2E' "$e2e_plan"
  grep -Fq '## Milestone 2 — Full Cross-product E2E Completion' "$e2e_plan"
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
  grep -Fq 'typed maintenance' "$source"
  grep -Fq 'tombstone in the maintenance projection' "$source"
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
  grep -Fq 'typed maintenance tombstone and its structured error' "$protocol"
  grep -Fq 'Do not restore a live worker card' "$protocol"
  grep -Fq 'route the failed deletion' "$protocol"
  grep -Fq 'through the session-management recovery owner' "$protocol"
  grep -Fq '## Run Closeout And Handoff' "$source"
  grep -Fq 'main-agent.run-wide-closeout.v1' "$source"
  grep -Fq 'main-agent closeout' "$source"
  grep -Fq '`handoff_ready:false` is a resumable partial result' "$source"
  grep -Fq '`controller-claim-provenance-required`' "$source"
  grep -Fq '`progress_receipt.completed_stages`' "$source"
  grep -Fq 'Keep the Main provider session live' "$source"
  grep -Fq '## Run Closeout And Handoff' "$protocol"
  grep -Fq 'prepare the private final' "$protocol"
  grep -Fq 'main-agent closeout' "$protocol"
  grep -Fq '`handoff_ready:true`' "$protocol"
  grep -Fq '`handoff_ready:false` is resumable progress' "$protocol"
  grep -Fq '`progress_receipt.completed_stages`' "$protocol"
  grep -Fq '`controller-claim-provenance-required`' "$protocol"
  grep -Fq 'preserves an unrelated successor claim' "$protocol"
  grep -Fq 'Keep the Main provider session live' "$protocol"
  grep -Fq 'durable controller-claim binding created at' "$closeout_design"
  grep -Fq 'Context equality alone never establishes claim ownership.' "$closeout_design"
  grep -Fq '"completed_stages": [' "$closeout_design"
  grep -Fq '"run_owned_claim_absent": true' "$closeout_design"
  grep -Fq '"handoff_ready": false' "$closeout_design"
  grep -Fq 'Bind its request digest to the original expected run revision' "$closeout_design"
  grep -Fq 'matching progress receipt attests them' "$closeout_design"
  grep -Fq 'original now-stale revision returns or resumes' "$closeout_design"
  grep -Fq 'receipt, or external drift fails closed' "$closeout_design"
  grep -Fq 'Failure preserves every resource not already changed by a committed stage' "$closeout_design"
  grep -Fq 'preserved and reported, the run-owned claim is recorded absent' "$closeout_design"
  grep -Fq 'controller-claim provenance is ambiguous or cannot be proven' "$closeout_design"

  rendered_contract_assert_product_contains conversation main-agent-mode codex 'For a Codex worker, run these literal commands:'
  rendered_contract_assert_product_contains conversation main-agent-mode codex 'main-agent capabilities --provider codex --format json'
  rendered_contract_assert_product_contains conversation main-agent-mode codex 'main-agent self readiness --format json'
  rendered_contract_assert_product_contains conversation main-agent-mode codex 'agent-session activity doctor --agent codex --format json'
  rendered_contract_assert_product_contains conversation main-agent-mode codex 'agent-session activity setup --agent codex --repair --dry-run --format json'
  rendered_contract_assert_product_omits conversation main-agent-mode codex 'Claude'
  rendered_contract_assert_product_omits conversation main-agent-mode codex '--agent claude'
  rendered_contract_assert_product_contains conversation main-agent-mode claude 'For a Claude worker, run these literal commands:'
  rendered_contract_assert_product_contains conversation main-agent-mode claude 'main-agent capabilities --provider claude --format json'
  rendered_contract_assert_product_contains conversation main-agent-mode claude 'main-agent self readiness --format json'
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
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '## Run Closeout And Handoff'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'main-agent.run-wide-closeout.v1'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'main-agent closeout'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`handoff_ready:true`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`handoff_ready:false` is a resumable partial result'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`progress_receipt.completed_stages`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" '`controller-claim-provenance-required`'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'original run revision, request, and parent idempotency key'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'diagnostic and intentional recovery primitives'
    rendered_contract_assert_product_contains conversation main-agent-mode "$product" 'Keep the Main provider session live'
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
    assert_main_agent_controller_recovery_contract "$rendered"
    assert_main_agent_controller_recovery_contract "$golden"
    cmp -s "$rendered" "$golden"
    test -s "$rendered_protocol"
    test -s "$golden_protocol"
    assert_main_agent_v2_recovery_contract "$rendered_protocol"
    assert_main_agent_v2_recovery_contract "$golden_protocol"
    assert_main_agent_replay_boundaries "$rendered_protocol"
    assert_main_agent_replay_boundaries "$golden_protocol"
    assert_main_agent_controller_recovery_contract "$rendered_protocol"
    assert_main_agent_controller_recovery_contract "$golden_protocol"
    assert_main_agent_controller_matrix_contract "$rendered_protocol"
    assert_main_agent_controller_matrix_contract "$golden_protocol"
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
record_case "conversation.main-agent-mode" "explicit opt-in ownership, verified startup, post-claim terminalization, macro-first closeout, and Codex/Claude-only renders are enforced" run_main_agent_mode_probe

exit "$failures"
