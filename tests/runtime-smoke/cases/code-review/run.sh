#!/usr/bin/env bash
# Deterministic probes for code review workflow skills.
# shellcheck disable=SC2016,SC2329

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

run_codex_reviewer_profile_contract_probe() {
  local repo_out="$CODE_REVIEW_ARTIFACTS_DIR/reviewer-profile-repo.txt"
  local fixture_out="$CODE_REVIEW_ARTIFACTS_DIR/reviewer-profile-fixture.txt"

  bash "$REPO_ROOT/scripts/ci/skill-governance-audit.sh" >"$repo_out" 2>&1
  bash "$REPO_ROOT/scripts/ci/skill-governance-audit.sh" --fixture reviewer-profile >"$fixture_out" 2>&1

  grep -Fq 'skill-governance-audit: repo OK' "$repo_out"
  grep -Fq 'manifest_inventory=true' "$fixture_out"
  grep -Fq 'missing_field_rejected=true' "$fixture_out"
  grep -Fq 'generic_fallback_rejected=true' "$fixture_out"
}

run_portable_review_identity_contract_probe() {
  local gate="$REPO_ROOT/core/skills/code-review/code-review-specialists/references/DELIVERY_SPECIALIST_REVIEW_GATE.md"
  local posting="$REPO_ROOT/core/skills/code-review/code-review-specialists/references/REVIEW_OUTCOME_POSTING_CONTRACT.md"
  local delivery="$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  local tracking="$REPO_ROOT/core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera"

  if grep -R -E 'FORGE_BOT_PROFILE|lens bot profile|same lens bot profile|review-testing-bot|review-maintainability|dobi-bot' \
    "$REPO_ROOT/core/skills"; then
    return 1
  fi
  grep -Fq 'FINAL_SUBMIT_REVIEW' "$posting"
  grep -Fq 'AGENT_RUNTIME_FORGE_IDENTITY_ROUTER_REQUIRED' "$posting"
  grep -Fq -- '--profile provider-review' "$posting"
  grep -Fq -- '--specialist-report' "$posting"
  grep -Fq -- '--metadata-only' "$posting"
  grep -Fq -- '--native-review-url' "$posting"
  grep -Fq -- '--native-review-author' "$posting"
  grep -Fq 'complete report body exactly once' "$posting"
  grep -Fq 'must not pass `--comment-file`' "$posting"
  grep -Fq 'ISSUE_MIRROR_ARGS=()' "$posting"
  grep -Fq '[[ -n "${ISSUE:-}" ]]' "$posting"
  grep -Fq '"${ISSUE_MIRROR_ARGS[@]}"' "$posting"
  bash -u -c 'ISSUE_MIRROR_ARGS=(); if [[ -n "${ISSUE:-}" ]]; then ISSUE_MIRROR_ARGS=(--issue "$ISSUE" --mirror-issue); fi; ((${#ISSUE_MIRROR_ARGS[@]} == 0))'
  ISSUE=65 bash -u -c 'ISSUE_MIRROR_ARGS=(); if [[ -n "${ISSUE:-}" ]]; then ISSUE_MIRROR_ARGS=(--issue "$ISSUE" --mirror-issue); fi; [[ "${ISSUE_MIRROR_ARGS[*]}" == "--issue 65 --mirror-issue" ]]'
  grep -Fq 'For a clean quick pass' "$posting"
  grep -Fq 'with `--lens quick`; there is no finding to preserve before repair' "$posting"
  grep -Fq 'unsupported review profile: $REVIEW_PROFILE' "$posting"
  grep -Fq 'FINAL_SUBMIT_REVIEW' "$delivery"
  grep -Fq 'SELECTED_REVIEW_LENSES=(quick)' "$delivery"
  grep -Fq 'SELECTED_REVIEW_LENSES=(testing maintainability)' "$delivery"
  grep -Fq 'unsupported review profile: $REVIEW_PROFILE' "$delivery"
  grep -Fq 'governed-vs-portable publication branch' "$delivery"
  grep -Fq 'explicit no-publisher portable' "$delivery"
  grep -Fq 'SELECTED_REVIEW_LENSES=(testing maintainability)' "$tracking"
  grep -Fq 'TRACKING_LENS_ARGS+=(--review-lens "$selected_lens")' "$tracking"
  grep -Fq 'governed `forge-review-publish` path' "$tracking"
  grep -Fq 'explicit no-publisher portable fallback' "$tracking"
  grep -Fq -- '--decision comments-only' "$gate"

  if sed -n '29,125p' "$REPO_ROOT/docs/source/nils-cli-surface.md" \
    | grep -Eq 'is the compatibility minimum|remains the compatibility minimum|minimum stays where it is'; then
    echo 'runtime-smoke code-review: historical nils entries claim a current compatibility minimum' >&2
    return 1
  fi
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
{"severity":"HIGH","confidence":0.82,"path":"src/api.py","line":1,"category":"api-contract","summary":"Runtime smoke finding.","evidence":"Fixture evidence anchors the changed API file.","recommendation":"Keep the fixture stable.","specialist":"api-contract","test_suggestion":"Keep a focused smoke test.","actionable":true}
{"severity":"MEDIUM","confidence":0.78,"path":"tests/test_api.py","category":"testing","summary":"Runtime smoke file finding.","evidence":"Fixture evidence anchors a file-level test concern.","recommendation":"Keep the file-level fixture stable.","specialist":"testing","test_suggestion":"Keep a file-level smoke test.","actionable":true}
JSONL
}

run_recording_publisher_probe() {
  local report="$1"
  local threads="$2"
  local recorder="$CODE_REVIEW_ARTIFACTS_DIR/recording-forge-review-publish"
  local calls="$CODE_REVIEW_ARTIFACTS_DIR/recorded-publication"
  local expected_head='0123456789abcdef0123456789abcdef01234567'

  mkdir -p "$calls"
  cat >"$recorder" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
: "${RECORD_CALLS:?}"
repo=''
pr=''
decision=''
head=''
comment_file=''
thread_file=''
lens=''
submit=0
while (($#)); do
  case "$1" in
    --provider|--format) shift 2 ;;
    --repo) repo="$2"; shift 2 ;;
    --decision) decision="$2"; shift 2 ;;
    --expected-head) head="$2"; shift 2 ;;
    --comment-file) comment_file="$2"; shift 2 ;;
    --thread-file) thread_file="$2"; shift 2 ;;
    --lens) lens="$2"; shift 2 ;;
    --submit-review) submit=1; shift ;;
    pr)
      [[ "${2:-}" == review-publish && "${3:-}" =~ ^[0-9]+$ ]]
      pr="$3"
      shift 3
      ;;
    *) echo "recording publisher: unsupported argument $1" >&2; exit 64 ;;
  esac
done
[[ -n "$repo" && -n "$pr" && -n "$decision" && -n "$head" && -s "$comment_file" && -s "$thread_file" && -n "$lens" && "$submit" == 1 ]]
native_url="https://github.com/$repo/pull/$pr#pullrequestreview-1"
native_author='sympoies-agent-runtime-reviewer[bot]'
printf '%s\n' --repo "$repo" pr review "$pr" --decision "$decision" \
  --expected-head "$head" --comment-file "$comment_file" \
  --thread-file "$thread_file" --submit-review >"$RECORD_CALLS/app.argv"
printf '%s\n' --repo "$repo" pr review "$pr" --decision "$decision" \
  --metadata-only --expected-head "$head" --native-review-url "$native_url" \
  --native-review-author "$native_author" --lens "$lens" >"$RECORD_CALLS/personal.argv"
SH
  chmod 700 "$recorder"
  RECORD_CALLS="$calls" "$recorder" \
    --provider github --repo sympoies/agent-runtime-kit \
    pr review-publish 123 --decision comments-only --submit-review \
    --expected-head "$expected_head" --comment-file "$report" \
    --thread-file "$threads" --lens api-contract --format json

  [[ "$(grep -Fxc -- '--comment-file' "$calls/app.argv")" == 1 ]]
  [[ "$(grep -Fxc -- '--thread-file' "$calls/app.argv")" == 1 ]]
  grep -Fxq -- "$report" "$calls/app.argv"
  grep -Fxq -- "$threads" "$calls/app.argv"
  grep -Fxq -- "$expected_head" "$calls/app.argv"
  grep -Fxq -- '--metadata-only' "$calls/personal.argv"
  grep -Fxq -- "$expected_head" "$calls/personal.argv"
  grep -Fxq -- 'https://github.com/sympoies/agent-runtime-kit/pull/123#pullrequestreview-1' "$calls/personal.argv"
  grep -Fxq -- 'sympoies-agent-runtime-reviewer[bot]' "$calls/personal.argv"
  ! grep -Fxq -- '--comment-file' "$calls/personal.argv"
  ! grep -Fxq -- '--thread-file' "$calls/personal.argv"
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
  local bundle_out="$CODE_REVIEW_ARTIFACTS_DIR/provider-bundle.json"
  local bundle_dir="$CODE_REVIEW_ARTIFACTS_DIR/provider-bundle"
  local provider_report="$bundle_dir/provider-review.md"
  local provider_threads="$bundle_dir/review-threads.json"
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
  review-specialists bundle \
    --input "$findings" \
    --out-dir "$bundle_dir" \
    --profile provider-review \
    --repo sympoies/agent-runtime-kit \
    --ref runtime-smoke \
    --reviewable 'PR #123' \
    --lens api-contract \
    --lens-verdict findings \
    --scope 'runtime smoke provider review contract' \
    --evidence-reviewed 'deterministic fixture' \
    --format json >"$bundle_out" 2>&1

  grep -q '"schema_version": "cli.review-specialists.scope.v1"' "$scope_out"
  grep -q '"schema_version": "cli.review-specialists.validate.v1"' "$validate_out"
  grep -q '"schema_version": "cli.review-specialists.merge.v1"' "$merge_out"
  grep -q '"schema_version": "cli.review-specialists.render.v1"' "$render_out"
  grep -q 'Runtime smoke finding' "$summary_out"
  grep -q 'Specialist Review Report' "$rendered_report"
  grep -q '"profile": "provider-review"' "$bundle_out"
  grep -Fq '<!-- agent-kit:specialist-review-report:v1 -->' "$provider_report"
  grep -Fq '| Finding | Severity | Confidence | Evidence | Recommendation |' "$provider_report"
  jq -e 'length == 2
    and .[0].path == "src/api.py" and .[0].line == 1
    and .[1].path == "tests/test_api.py" and (.[1] | has("line") | not)' \
    "$provider_threads" >/dev/null
  run_recording_publisher_probe "$provider_report" "$provider_threads"
}

run_code_review_outcome_routing_probe() {
  local skill="$REPO_ROOT/core/skills/code-review/code-review-specialists/SKILL.md.tera"
  local delivery_gate="$REPO_ROOT/core/skills/code-review/code-review-specialists/references/DELIVERY_SPECIALIST_REVIEW_GATE.md"

  grep -Fq '# Code Review' "$skill"
  grep -Fq '## Mode Selection' "$skill"
  grep -Fq '**Quick**' "$skill"
  grep -Fq '**Focused**' "$skill"
  grep -Fq '**Specialist**' "$skill"
  grep -Fq '**Follow-up**' "$skill"
  grep -Fq '**Pre-merge**' "$skill"
  grep -Fq 'The caller requests the review outcome; the workflow selects context and depth.' "$skill"
  grep -Fq 'must dispatch the selected reviewers' "$skill"
  grep -Fq 'Pre-merge is a delivery context, not a review depth.' "$skill"
  grep -Fq '**Quick pre-merge**' "$skill"
  grep -Fq 'A `pass` verdict is' "$skill"
  grep -Fq 'terminal review evidence for the current head' "$skill"
  grep -Fq 'A verdict of `escalate` routes to the full pre-merge' "$skill"
  grep -Fq '## Quick Pre-Merge Profile' "$delivery_gate"
  grep -Fq '## Full Pre-Merge Profile' "$delivery_gate"
  grep -Fq 'L2 or L3' "$delivery_gate"
  grep -Fq 'either `suggested_specialists` or `forced_specialists`' "$delivery_gate"

  rendered_contract_assert_skill code-review code-review-specialists
  rendered_contract_assert_all_contain code-review code-review-specialists '# Code Review'
  rendered_contract_assert_all_contain code-review code-review-specialists '## Mode Selection'
  rendered_contract_assert_all_contain code-review code-review-specialists '**Quick pre-merge**'
  rendered_contract_assert_all_contain code-review code-review-specialists 'Pre-merge is a delivery context, not a review depth.'
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

run_review_convergence_contract_probe() {
  local home_policy="$REPO_ROOT/AGENT_HOME.md"
  local skill="$REPO_ROOT/core/skills/code-review/code-review-specialists/SKILL.md.tera"
  local gate="$REPO_ROOT/core/skills/code-review/code-review-specialists/references/DELIVERY_SPECIALIST_REVIEW_GATE.md"
  local contract="$REPO_ROOT/core/skills/code-review/code-review-specialists/references/SPECIALIST_REVIEW_CONTRACT.md"
  local convergence="$REPO_ROOT/core/policies/review-thread-convergence.md"
  local quick="$REPO_ROOT/core/agents/code-review/reviewer-quick/AGENT.md.tera"
  local deliver="$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  local tracking="$REPO_ROOT/core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera"
  local dispatch="$REPO_ROOT/core/skills/dispatch/deliver-dispatch-plan/SKILL.md.tera"

  grep -Fq 'possible improvement is not incompleteness' "$home_policy"
  grep -Fq 'Each discovery generation has at most one broad review.' "$convergence"
  grep -Fq 'new discovery generation' "$convergence"
  grep -Fq 'closed-set closure review' "$skill"
  grep -Fq 'Evidence alone does not make a concern blocking.' "$contract"
  grep -Fq 'smallest sufficient local repair' "$contract"
  grep -Fq 'Low and informational observations never block delivery.' "$gate"
  grep -Fq 'Raw diff size alone never activates red-team.' "$gate"
  grep -Fq 'Do not list skipped areas for completeness.' "$quick"
  grep -Fq 'closed-set closure' "$deliver"
  grep -Fq 'finite unresolved admitted finding set' "$deliver"
  grep -Fq 'every actionable current-head summary under the' "$deliver"
  grep -Fq 'the new evidence under the closed-set admission rule' "$deliver"
  grep -Fq 'the new current-head evidence under the closed-set admission' "$deliver"
  grep -Fq 'affected lenses as closed-set closure' "$tracking"
  grep -Fq 'every actionable current-head summary under the closed-set' "$tracking"
  grep -Fq 'the new evidence under the closed-set admission rule' "$tracking"
  grep -Fq 'affected lenses as closed-set closure' "$dispatch"
  grep -Fq 'summaries under the closed-set admission rule' "$dispatch"
  grep -Fq 'under the closed-set admission rule, and refresh lane' "$dispatch"
  grep -Fq 'Admitted genuine defect' "$convergence"
  grep -Fq 'do not extend the current repair loop' "$convergence"

  if grep -Fq 'Treat evidence-backed quick or specialist findings as blocking before merge.' "$gate"; then
    return 1
  fi
  if grep -Fq 'Repeat review and repair until no concrete unresolved findings remain' "$gate"; then
    return 1
  fi
  if grep -Fq 'otherwise switch to full.' "$deliver"; then
    return 1
  fi
  if grep -Fq 'disposition the new current-head evidence, refresh' "$deliver"; then
    return 1
  fi
}

failures=0
record_case "code-review.outcome-routing.testing-contract" "testing reviewer and specialist share the durable test-maintenance contract" run_testing_specialist_contract_probe
record_case "code-review.outcome-routing.reviewer-profiles" "manifest-driven Codex reviewer profiles and custom-agent dispatch contract passed" run_codex_reviewer_profile_contract_probe
record_case "code-review.outcome-routing.portable-identity" "public review workflows preserve ambient identity, independent native approval, and selected lenses" run_portable_review_identity_contract_probe
record_case "code-review.outcome-routing.focused" "focused lens scope with forced specialists passed" run_focused_lens_probe
record_case "code-review.outcome-routing.follow-up" "follow-up validation and affected lens scope passed" run_follow_up_probe
record_case "code-review.outcome-routing.pre-merge" "full pre-merge profile forced specialists passed" run_pre_merge_gate_probe
record_case "code-review.cli-command-contract-policy" "delivery skill CLI command blocks require pinned-surface dry-run contract evidence" run_cli_command_contract_policy_probe
record_case "code-review.outcome-routing.quick" "quick-pass scope sizing probe passed" run_quick_pass_probe
record_case "code-review.code-review-specialists" "review-specialists scope, validate, merge, and render probes passed" run_code_review_specialists_probe
record_case "code-review.outcome-routing.contract" "one review outcome selects delivery context and risk-appropriate review depth" run_code_review_outcome_routing_probe
record_case "code-review.convergence.contract" "review discovery, closure, blocking admission, and stopping rules are bounded" run_review_convergence_contract_probe

exit "$failures"
