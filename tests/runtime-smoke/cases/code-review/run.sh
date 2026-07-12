#!/usr/bin/env bash
# Deterministic probes for code review workflow skills.
# shellcheck disable=SC2329

set -euo pipefail

: "${REPO_ROOT:?}"
: "${SCRIPT_DIR:?}"
: "${TMP_ROOT:?}"
: "${ARTIFACTS_DIR:?}"
: "${RESULTS_FILE:?}"

# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/results.sh
. "$SCRIPT_DIR/lib/results.sh"
# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/rendered-contract.sh
. "$SCRIPT_DIR/lib/rendered-contract.sh"

CODE_REVIEW_ARTIFACTS_DIR="$ARTIFACTS_DIR/code-review"
CODE_REVIEW_WORKSPACE="$TMP_ROOT/workspaces/code-review-basic-repo"
mkdir -p "$CODE_REVIEW_ARTIFACTS_DIR" "$CODE_REVIEW_WORKSPACE"

require_code_review_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke code-review: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

run_testing_specialist_contract_probe() {
  local agent="$REPO_ROOT/core/agents/code-review/reviewer-testing/AGENT.md.tera"
  local specialist="$REPO_ROOT/core/skills/code-review/code-review-specialists/references/specialists/testing.md"

  for path in "$agent" "$specialist"; do
    grep -Fiq 'test-delta completeness' "$path"
    grep -Fiq 'lost invariants' "$path"
    grep -Fiq 'duplicate owners' "$path"
    grep -Fiq 'meaningful red' "$path"
    grep -Fiq 'stable behavioral boundary' "$path"
    grep -Fiq 'deterministic fixtures' "$path"
    grep -Fiq 'residual gaps' "$path"
  done
}

init_diff_fixture() {
  local tree commit

  rm -rf "$CODE_REVIEW_WORKSPACE"
  mkdir -p "$CODE_REVIEW_WORKSPACE"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$CODE_REVIEW_WORKSPACE"
  git -C "$CODE_REVIEW_WORKSPACE" init -q
  git -C "$CODE_REVIEW_WORKSPACE" config user.email runtime-smoke@example.invalid
  git -C "$CODE_REVIEW_WORKSPACE" config user.name "Runtime Smoke"
  mkdir -p "$CODE_REVIEW_WORKSPACE/src" "$CODE_REVIEW_WORKSPACE/tests"
  printf 'def handler():\n    return {"ok": True}\n' >"$CODE_REVIEW_WORKSPACE/src/api.py"
  printf 'def test_handler():\n    assert True\n' >"$CODE_REVIEW_WORKSPACE/tests/test_api.py"
  git -C "$CODE_REVIEW_WORKSPACE" add .
  tree="$(git -C "$CODE_REVIEW_WORKSPACE" write-tree)"
  commit="$(printf 'runtime smoke code review base\n' | git -C "$CODE_REVIEW_WORKSPACE" commit-tree "$tree")"
  git -C "$CODE_REVIEW_WORKSPACE" update-ref refs/heads/main "$commit"
  git -C "$CODE_REVIEW_WORKSPACE" symbolic-ref HEAD refs/heads/main
  printf '\n\ndef new_handler():\n    return {"ok": False}\n' >>"$CODE_REVIEW_WORKSPACE/src/api.py"
}

write_findings() {
  local findings="$1"

  cat >"$findings" <<'JSONL'
{"severity":"HIGH","confidence":0.82,"path":"src/api.py","line":1,"category":"api-contract","summary":"Runtime smoke finding.","evidence":"Fixture evidence anchors the changed API file.","recommendation":"Keep the fixture stable.","specialist":"api-contract","test_suggestion":"Keep a focused smoke test."}
JSONL
}

run_quick_pass_probe() {
  local scope_out="$CODE_REVIEW_ARTIFACTS_DIR/quick-pass-scope.json"
  require_code_review_bin review-specialists || return 1
  init_diff_fixture

  review-specialists scope \
    --repo "$CODE_REVIEW_WORKSPACE" \
    --base main \
    --format json >"$scope_out" 2>&1

  grep -q '"schema_version": "cli.review-specialists.scope.v1"' "$scope_out"
  grep -q '"suggested_specialists"' "$scope_out"
}

run_focused_lens_probe() {
  local scope_out="$CODE_REVIEW_ARTIFACTS_DIR/focused-lens-scope.json"
  require_code_review_bin review-specialists || return 1
  init_diff_fixture

  review-specialists scope \
    --repo "$CODE_REVIEW_WORKSPACE" \
    --base main \
    --testing \
    --api-contract \
    --format json >"$scope_out" 2>&1

  grep -q '"schema_version": "cli.review-specialists.scope.v1"' "$scope_out"
  grep -q '"forced_specialists"' "$scope_out"
  grep -q '"testing"' "$scope_out"
  grep -q '"api-contract"' "$scope_out"
}

run_pre_merge_gate_probe() {
  local scope_out="$CODE_REVIEW_ARTIFACTS_DIR/pre-merge-gate-scope.json"
  require_code_review_bin review-specialists || return 1
  init_diff_fixture

  review-specialists scope \
    --repo "$CODE_REVIEW_WORKSPACE" \
    --base main \
    --testing \
    --maintainability \
    --format json >"$scope_out" 2>&1

  grep -q '"schema_version": "cli.review-specialists.scope.v1"' "$scope_out"
  grep -q '"forced_specialists"' "$scope_out"
  grep -q '"testing"' "$scope_out"
  grep -q '"maintainability"' "$scope_out"
}

run_cli_command_contract_policy_probe() {
  local gate_body="$REPO_ROOT/core/skills/code-review/code-review-specialists/references/DELIVERY_SPECIALIST_REVIEW_GATE.md"
  local api_reviewer="$REPO_ROOT/core/agents/code-review/reviewer-api-contract/AGENT.md.tera"
  local api_fallback="$REPO_ROOT/core/skills/code-review/code-review-specialists/references/specialists/api-contract.md"
  local gate_section
  local reviewer_path

  gate_section="$(awk '
    found && /^## / { exit }
    /^## CLI Command-Block Contract Check$/ { found = 1 }
    found { print }
  ' "$gate_body")"

  grep -Fq 'core/skills/{dispatch,pr}/deliver-*/SKILL.md.tera' <<<"$gate_section"
  grep -Fq 'Force the `api-contract` lens' <<<"$gate_section"
  grep -Fq 'pinned nils-cli surface' <<<"$gate_section"
  grep -Fq 'Check every invocation' <<<"$gate_section"
  grep -Fq '`--dry-run --format json`' <<<"$gate_section"
  grep -Fq 'require `ok=true`' <<<"$gate_section"
  grep -Fq 'plan-bearing field' <<<"$gate_section"
  grep -Fq '`data.plan`' <<<"$gate_section"
  grep -Fq '`data.plan_steps[].plan`' <<<"$gate_section"
  grep -Fq '`guard_plan`' <<<"$gate_section"
  grep -Fq '`issue_plan`' <<<"$gate_section"
  grep -Fq 'read output' <<<"$gate_section"
  grep -Fq 'downstream JSON fields' <<<"$gate_section"
  grep -Fq 'comments-aware fetch' <<<"$gate_section"
  grep -Fq '`forge-cli issue view --with-comments`' <<<"$gate_section"
  grep -Fq 'evidence blocks a passing review outcome.' <<<"$gate_section"
  for reviewer_path in "$api_reviewer" "$api_fallback"; do
    grep -Fq 'CLI command syntax, flags, subcommands, and machine-readable output fields' "$reviewer_path"
    grep -Fq 'non-mutating dry-runs' "$reviewer_path"
  done
}

run_follow_up_probe() {
  local scope_out="$CODE_REVIEW_ARTIFACTS_DIR/follow-up-scope.json"
  local findings="$CODE_REVIEW_ARTIFACTS_DIR/follow-up-findings.jsonl"
  local validate_out="$CODE_REVIEW_ARTIFACTS_DIR/follow-up-validate.json"
  require_code_review_bin review-specialists || return 1
  init_diff_fixture
  write_findings "$findings"

  review-specialists scope \
    --repo "$CODE_REVIEW_WORKSPACE" \
    --base main \
    --testing \
    --maintainability \
    --format json >"$scope_out" 2>&1
  review-specialists validate \
    --input "$findings" \
    --repo "$CODE_REVIEW_WORKSPACE" \
    --validate-paths \
    --validate-lines \
    --format json >"$validate_out" 2>&1

  grep -q '"schema_version": "cli.review-specialists.scope.v1"' "$scope_out"
  grep -q '"schema_version": "cli.review-specialists.validate.v1"' "$validate_out"
}

run_code_review_specialists_probe() {
  local scope_out="$CODE_REVIEW_ARTIFACTS_DIR/scope.json"
  local findings="$CODE_REVIEW_ARTIFACTS_DIR/findings.jsonl"
  local validate_out="$CODE_REVIEW_ARTIFACTS_DIR/validate.json"
  local merge_out="$CODE_REVIEW_ARTIFACTS_DIR/merge.json"
  local summary_out="$CODE_REVIEW_ARTIFACTS_DIR/specialist-review.md"
  local render_out="$CODE_REVIEW_ARTIFACTS_DIR/render.json"
  local rendered_report="$CODE_REVIEW_ARTIFACTS_DIR/rendered-report.md"
  require_code_review_bin review-specialists || return 1
  init_diff_fixture
  write_findings "$findings"

  review-specialists scope \
    --repo "$CODE_REVIEW_WORKSPACE" \
    --base main \
    --format json >"$scope_out" 2>&1
  review-specialists validate \
    --input "$findings" \
    --repo "$CODE_REVIEW_WORKSPACE" \
    --validate-paths \
    --validate-lines \
    --format json >"$validate_out" 2>&1
  review-specialists merge \
    --input "$findings" \
    --summary-out "$summary_out" \
    --format json >"$merge_out" 2>&1
  review-specialists render \
    --profile report \
    --input "$merge_out" \
    --out "$rendered_report" \
    --format json >"$render_out" 2>&1

  grep -q '"schema_version": "cli.review-specialists.scope.v1"' "$scope_out"
  grep -q '"schema_version": "cli.review-specialists.validate.v1"' "$validate_out"
  grep -q '"schema_version": "cli.review-specialists.merge.v1"' "$merge_out"
  grep -q '"schema_version": "cli.review-specialists.render.v1"' "$render_out"
  grep -q 'Runtime smoke finding' "$summary_out"
  grep -q 'Specialist Review Report' "$rendered_report"
}

run_code_review_outcome_routing_probe() {
  local skill="$REPO_ROOT/core/skills/code-review/code-review-specialists/SKILL.md.tera"

  grep -Fq '# Code Review' "$skill"
  grep -Fq '## Mode Selection' "$skill"
  grep -Fq '**Quick**' "$skill"
  grep -Fq '**Focused**' "$skill"
  grep -Fq '**Specialist**' "$skill"
  grep -Fq '**Follow-up**' "$skill"
  grep -Fq '**Pre-merge**' "$skill"
  grep -Fq 'The caller requests the review outcome; the workflow selects the mode.' "$skill"
  grep -Fq 'must dispatch the selected reviewers' "$skill"

  rendered_contract_assert_skill code-review code-review-specialists
  rendered_contract_assert_all_contain code-review code-review-specialists '# Code Review'
  rendered_contract_assert_all_contain code-review code-review-specialists '## Mode Selection'
  rendered_contract_assert_product_contains code-review code-review-specialists codex '`multi_agent_v1.spawn_agent`'
  rendered_contract_assert_product_omits code-review code-review-specialists codex '`delegate_task`'
  rendered_contract_assert_product_contains code-review code-review-specialists claude '`~/.claude/agents/reviewer-<lens>.md`'
  rendered_contract_assert_product_omits code-review code-review-specialists claude '`delegate_task`'
  rendered_contract_assert_product_contains code-review code-review-specialists hermes '`delegate_task`'
  rendered_contract_assert_product_contains code-review code-review-specialists hermes 'generic read-only task for each selected lens'
  rendered_contract_assert_product_omits code-review code-review-specialists hermes 'managed reviewer'
  rendered_contract_assert_product_omits code-review code-review-specialists hermes '`reviewer-testing`'
  rendered_contract_assert_product_omits code-review code-review-specialists hermes '`multi_agent_v1.spawn_agent`'
}

failures=0
record_case "code-review.outcome-routing.testing-contract" "testing reviewer and specialist share the durable test-maintenance contract" run_testing_specialist_contract_probe
record_case "code-review.outcome-routing.focused" "focused lens scope with forced specialists passed" run_focused_lens_probe
record_case "code-review.outcome-routing.follow-up" "follow-up validation and affected lens scope passed" run_follow_up_probe
record_case "code-review.outcome-routing.pre-merge" "pre-merge gate mandatory forced specialists passed" run_pre_merge_gate_probe
record_case "code-review.cli-command-contract-policy" "delivery skill CLI command blocks require pinned-surface dry-run contract evidence" run_cli_command_contract_policy_probe
record_case "code-review.outcome-routing.quick" "quick-pass scope sizing probe passed" run_quick_pass_probe
record_case "code-review.code-review-specialists" "review-specialists scope, validate, merge, and render probes passed" run_code_review_specialists_probe
record_case "code-review.outcome-routing.contract" "one review outcome selects quick, focused, specialist, follow-up, and pre-merge modes internally" run_code_review_outcome_routing_probe

exit "$failures"
