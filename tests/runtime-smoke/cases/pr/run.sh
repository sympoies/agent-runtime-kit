#!/usr/bin/env bash
# Deterministic probes for PR/MR skills.
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

PR_ARTIFACTS_DIR="$ARTIFACTS_DIR/pr"
PR_WORKSPACE="$TMP_ROOT/workspaces/pr-basic-repo"
LABEL_CATALOG="$REPO_ROOT/manifests/forge-labels.yaml"
mkdir -p "$PR_ARTIFACTS_DIR" "$TMP_ROOT/workspaces"
cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$PR_WORKSPACE"

require_pr_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke pr: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

init_pushed_branch_fixture() {
  local workspace="$1"
  local branch="$2"
  local remote_url="$3"
  local base_tree base_commit tree commit

  git -C "$workspace" init -q
  git -C "$workspace" config user.email runtime-smoke@example.invalid
  git -C "$workspace" config user.name "Runtime Smoke"
  printf 'runtime-smoke pr base\n' >"$workspace/pr-base.txt"
  git -C "$workspace" add .
  base_tree="$(git -C "$workspace" write-tree)"
  base_commit="$(printf 'runtime-smoke pr base\n' | git -C "$workspace" commit-tree "$base_tree")"
  git -C "$workspace" update-ref refs/heads/main "$base_commit"
  git -C "$workspace" update-ref refs/remotes/origin/main "$base_commit"
  printf 'runtime-smoke pr fixture\n' >"$workspace/pr-fixture.txt"
  git -C "$workspace" add .
  tree="$(git -C "$workspace" write-tree)"
  commit="$(printf 'runtime-smoke fixture\n' | git -C "$workspace" commit-tree "$tree" -p "$base_commit")"
  git -C "$workspace" update-ref "refs/heads/$branch" "$commit"
  git -C "$workspace" symbolic-ref HEAD "refs/heads/$branch"
  git -C "$workspace" remote add origin "$remote_url"
  git -C "$workspace" update-ref "refs/remotes/origin/$branch" "$commit"
  git -C "$workspace" branch --set-upstream-to "origin/$branch" "$branch" >/dev/null
}

write_pr_body() {
  local path="$1"
  cat >"$path" <<'BODY'
## Summary

Runtime smoke validates the forge-cli PR create dry-run contract.

## Test plan

- forge-cli dry-run (pass)
BODY
}

write_dispatch_session_record() {
  local path="$1"
  cat >"$path" <<'BODY'
## Dispatch Lane PR

- Lane: L1
- PR: https://github.com/graysurf/agent-runtime-kit/pull/123
- Status: draft PR created
- Validation: forge-cli dry-run (pass)
BODY
}

assert_provider_payload_local_path_gate() {
  local path="$1"
  local raw_path="$2"

  grep -q '"code":"local_path_present"' "$path" || return 1
  grep -q '[$]HOME/project' "$path" || return 1
  ! grep -q "$raw_path" "$path" || return 1
}

# Every retained PR/MR outcome that directly opens a feature/bug record must thread the
# forge-cli test-first gate flag (--test-first-evidence) into its documented
# create/deliver invocation. Without it, an operator with [test_first].require =
# true (repo or user-global) hits test_first_evidence_required at the documented
# gate even with a valid record (agent-runtime-kit#341). Assert the flag is
# present in each delivery skill body.
assert_delivery_skills_thread_test_first_evidence() {
  local rc=0 skill
  for skill in \
    core/skills/pr/deliver-pr/SKILL.md.tera \
    core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera; do
    if ! grep -q -- '--test-first-evidence' "$REPO_ROOT/$skill"; then
      echo "runtime-smoke pr: $skill omits --test-first-evidence gate threading" >&2
      rc=1
    fi
  done
  return "$rc"
}

run_pr_comment_provider_payload_privacy_gate_probe() {
  local body="$PR_ARTIFACTS_DIR/pr-comment-local-path.md"
  local out="$PR_ARTIFACTS_DIR/pr-comment-local-path-gate.json"
  local raw_path="/U""sers/example/project"
  local rc
  require_pr_bin forge-cli || return 1
  printf 'Runtime smoke should not publish %s\n' "$raw_path" >"$body"

  set +e
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    pr comment 123 \
    --body-file "$body" >"$out" 2>&1
  rc="$?"
  set -e

  [ "$rc" -ne 0 ] || return 1
  assert_provider_payload_local_path_gate "$out" "$raw_path"
}

run_specialist_scope_probe() {
  local workspace="$1"
  local out="$2"
  shift 2
  require_pr_bin review-specialists || return 1
  review-specialists scope \
    --repo "$workspace" \
    --base main \
    "$@" \
    --format json >"$out" 2>&1
  grep -q '"schema_version": "cli.review-specialists.scope.v1"' "$out"
}

run_create_github_probe() {
  local workspace="$PR_WORKSPACE/create-github"
  local body="$PR_ARTIFACTS_DIR/create-github-body.md"
  local out="$PR_ARTIFACTS_DIR/create-github.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-github" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr create \
      --kind feature \
      --base main \
      --title "Runtime smoke GitHub PR" \
      --body-file "$body" \
      --label type::feature \
      --label area::runtime \
      --label size::s \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels \
      --no-draft
  ) >"$out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.create.v1"' "$out"
  grep -q '"provider":"github"' "$out"
  grep -q '"type::feature"' "$out"
  grep -q '"area::runtime"' "$out"
  grep -q '"size::s"' "$out"
  grep -q '"gh"' "$out"
}

run_create_gitlab_probe() {
  local workspace="$PR_WORKSPACE/create-gitlab"
  local body="$PR_ARTIFACTS_DIR/create-gitlab-body.md"
  local out="$PR_ARTIFACTS_DIR/create-gitlab.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-gitlab" \
    "git@gitlab.com:group/project.git"
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider gitlab --repo group/project \
      --dry-run --format json \
      pr create \
      --kind feature \
      --base main \
      --title "Runtime smoke GitLab MR" \
      --body-file "$body" \
      --label type::feature \
      --label area::runtime \
      --label size::s \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels
  ) >"$out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.create.v1"' "$out"
  grep -q '"provider":"gitlab"' "$out"
  grep -q '"type::feature"' "$out"
  grep -q '"area::runtime"' "$out"
  grep -q '"size::s"' "$out"
  grep -q '"glab"' "$out"
}

run_create_dispatch_lane_probe() {
  local workspace="$PR_WORKSPACE/create-dispatch"
  local body="$PR_ARTIFACTS_DIR/create-dispatch-body.md"
  local out="$PR_ARTIFACTS_DIR/create-dispatch.json"
  local session="$PR_ARTIFACTS_DIR/create-dispatch-session.md"
  local session_payload="$PR_ARTIFACTS_DIR/create-dispatch-session-payload.json"
  local post_out="$PR_ARTIFACTS_DIR/create-dispatch-session-post.json"
  require_pr_bin forge-cli || return 1
  require_pr_bin plan-issue || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/dispatch-lane-runtime-smoke" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr create \
      --kind feature \
      --base plan/issue-26 \
      --title "Runtime smoke dispatch lane" \
      --body-file "$body" \
      --label type::feature \
      --label area::skills \
      --label size::s \
      --label workflow::dispatch \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels
  ) >"$out" 2>&1
  write_dispatch_session_record "$session"
  cat >"$session_payload" <<'JSON'
{"summary":"Runtime smoke dispatch lane PR created"}
JSON
  plan-issue record post \
    --dry-run \
    --issue 50 \
    --profile dispatch \
    --kind session \
    --payload-file "$session_payload" \
    --summary-file "$session" \
    --format json >"$post_out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.create.v1"' "$out"
  grep -q '"provider":"github"' "$out"
  grep -q '"workflow::dispatch"' "$out"
  grep -q '"size::s"' "$out"
  grep -q '"schema_version":"plan-issue.record.post.v2"' "$post_out"
  grep -q '<!-- plan-issue-record:v2 role=session profile=dispatch -->' "$post_out"
}

run_close_github_probe() {
  local workspace="$PR_WORKSPACE/close-github"
  local out="$PR_ARTIFACTS_DIR/close-github.jsonl"
  local review_out="$PR_ARTIFACTS_DIR/close-github-specialist-scope.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-close-github" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  run_specialist_scope_probe "$workspace" "$review_out"
  (
    cd "$workspace"
    {
      forge-cli --provider github --repo graysurf/agent-runtime-kit \
        --dry-run --format json pr checks 123
      forge-cli --provider github --repo graysurf/agent-runtime-kit \
        --dry-run --format json pr ready 123
      forge-cli --provider github --repo graysurf/agent-runtime-kit \
        --dry-run --format json pr merge 123 --method merge
      forge-cli --provider github --repo graysurf/agent-runtime-kit \
        --dry-run --format json pr close 123
    } >"$out" 2>&1
  )
  grep -q '"schema_version":"cli.forge-cli.pr.checks.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.ready.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.merge.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.close.v1"' "$out"
  grep -q '"provider":"github"' "$out"
  grep -q '"suggested_specialists"' "$review_out"
}

run_close_gitlab_probe() {
  local workspace="$PR_WORKSPACE/close-gitlab"
  local out="$PR_ARTIFACTS_DIR/close-gitlab.jsonl"
  local review_out="$PR_ARTIFACTS_DIR/close-gitlab-specialist-scope.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-close-gitlab" \
    "git@gitlab.com:group/project.git"
  run_specialist_scope_probe "$workspace" "$review_out"
  (
    cd "$workspace"
    {
      forge-cli --provider gitlab --repo group/project \
        --dry-run --format json pr checks 123
      forge-cli --provider gitlab --repo group/project \
        --dry-run --format json pr ready 123
      forge-cli --provider gitlab --repo group/project \
        --dry-run --format json pr merge 123 --method merge
      forge-cli --provider gitlab --repo group/project \
        --dry-run --format json pr close 123
    } >"$out" 2>&1
  )
  grep -q '"schema_version":"cli.forge-cli.pr.checks.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.ready.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.merge.v1"' "$out"
  grep -q '"schema_version":"cli.forge-cli.pr.close.v1"' "$out"
  grep -q '"provider":"gitlab"' "$out"
  grep -q '"suggested_specialists"' "$review_out"
}

run_deliver_github_probe() {
  local workspace="$PR_WORKSPACE/deliver-github"
  local body="$PR_ARTIFACTS_DIR/deliver-github-body.md"
  local review_body="$PR_ARTIFACTS_DIR/deliver-github-review.md"
  local review_threads="$PR_ARTIFACTS_DIR/deliver-github-review-threads.json"
  local out="$PR_ARTIFACTS_DIR/deliver-github.json"
  local provider_review_out="$PR_ARTIFACTS_DIR/deliver-github-provider-review.json"
  local review_out="$PR_ARTIFACTS_DIR/deliver-github-specialist-scope.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-deliver-github" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  run_specialist_scope_probe "$workspace" "$review_out" --testing --maintainability
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr deliver \
      --kind feature \
      --base main \
      --title "Runtime smoke GitHub delivery" \
      --body-file "$body" \
      --label type::feature \
      --label area::runtime \
      --label size::m \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels \
      --no-merge
  ) >"$out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.deliver.v1"' "$out"
  grep -q '"provider":"github"' "$out"
  grep -q '"wait_checks"' "$out"
  grep -q '"type::feature"' "$out"
  grep -q '"area::runtime"' "$out"
  grep -q '"size::m"' "$out"
  grep -q '"gh"' "$out"
  grep -q '"forced_specialists"' "$review_out"
  grep -q '"maintainability"' "$review_out"
  grep -q '"testing"' "$review_out"
  grep -q 'lifecycle readiness is also a pre-merge gate' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  grep -q 'plan-issue --format json record audit' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  grep -q 'role=session' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  printf 'Runtime smoke deliver-pr specialist review.\n' >"$review_body"
  printf '[{"path":"pr-fixture.txt","line":1,"body":"Runtime smoke deliver-pr actionable finding thread."}]\n' >"$review_threads"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr review 123 \
      --decision comments-only \
      --submit-review \
      --thread-file "$review_threads" \
      --comment-file "$review_body" \
      --lens testing
  ) >"$provider_review_out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.review.v1"' "$provider_review_out"
  grep -q '"decision":"comments-only"' "$provider_review_out"
  grep -q '"planned_review_threads"' "$provider_review_out"
}

run_deliver_gitlab_probe() {
  local workspace="$PR_WORKSPACE/deliver-gitlab"
  local body="$PR_ARTIFACTS_DIR/deliver-gitlab-body.md"
  local out="$PR_ARTIFACTS_DIR/deliver-gitlab.json"
  local review_out="$PR_ARTIFACTS_DIR/deliver-gitlab-specialist-scope.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-deliver-gitlab" \
    "git@gitlab.com:group/project.git"
  run_specialist_scope_probe "$workspace" "$review_out" --testing --maintainability
  write_pr_body "$body"
  (
    cd "$workspace"
    forge-cli --provider gitlab --repo group/project \
      --dry-run --format json \
      pr deliver \
      --kind feature \
      --base main \
      --title "Runtime smoke GitLab delivery" \
      --body-file "$body" \
      --label type::feature \
      --label area::runtime \
      --label size::m \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels \
      --no-merge
  ) >"$out" 2>&1
  grep -q '"schema_version":"cli.forge-cli.pr.deliver.v1"' "$out"
  grep -q '"provider":"gitlab"' "$out"
  grep -q '"wait_checks"' "$out"
  grep -q '"type::feature"' "$out"
  grep -q '"area::runtime"' "$out"
  grep -q '"size::m"' "$out"
  grep -q '"glab"' "$out"
  grep -q '"forced_specialists"' "$review_out"
  grep -q '"maintainability"' "$review_out"
  grep -q '"testing"' "$review_out"
  grep -q 'lifecycle readiness is also a pre-merge gate' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  grep -q 'plan-issue --format json record audit' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  grep -q 'role=session' \
    "$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
}

# The provider-neutral deliver-pr outcome covers the complete lifecycle for both
# providers, so each case exercises the GitHub and GitLab probe and fails if
# either provider regresses.
run_create_pr_probe() {
  local rc=0
  run_create_github_probe || rc=1
  run_create_gitlab_probe || rc=1
  return "$rc"
}

run_close_pr_probe() {
  local rc=0
  run_close_github_probe || rc=1
  run_close_gitlab_probe || rc=1
  return "$rc"
}

run_deliver_pr_probe() {
  local rc=0
  run_deliver_github_probe || rc=1
  run_deliver_gitlab_probe || rc=1
  run_pr_comment_provider_payload_privacy_gate_probe || rc=1
  assert_delivery_skills_thread_test_first_evidence || rc=1
  return "$rc"
}

# review-thread-cleanup wraps the forge-cli `pr review-threads` group: `list`
# (provider-aware read) plus the GitHub-only `resolve` / `reply` write surfaces.
# The probe exercises the GitHub write-surface dry-runs (which plan offline),
# asserts GitLab resolve fails closed with provider_unsupported, and asserts the
# shared skill documents the read + write invocations and cites the convergence
# policy as its judgment contract.
#
# NB: `pr review-threads list --dry-run` is intentionally NOT probed here. In
# forge-cli v1.9.1 the `list` dry-run still issues a live `gh` PR-view call
# before reaching the dry-run plan branch, so probing it would make this
# deterministic smoke depend on network / `gh` auth / a live PR (it would fail
# closed on a host without them). Tracked upstream (nils-cli); restore the `list`
# dry-run assertion once it plans offline like `resolve` / `reply`.
run_review_thread_cleanup_github_probe() {
  local workspace="$PR_WORKSPACE/review-thread-cleanup-github"
  local resolve_out="$PR_ARTIFACTS_DIR/review-thread-cleanup-resolve.json"
  local reply_out="$PR_ARTIFACTS_DIR/review-thread-cleanup-reply.json"
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-review-thread-cleanup" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json pr review-threads resolve 123 \
      --thread PRRT_runtimesmoke --note "Resolved per convergence policy." >"$resolve_out" 2>&1
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json pr review-threads reply 123 \
      --thread PRRT_runtimesmoke --body "Acknowledged." >"$reply_out" 2>&1
  )
  grep -q '"schema_version":"cli.forge-cli.pr.review-threads.resolve.v1"' "$resolve_out"
  grep -q '"schema_version":"cli.forge-cli.pr.review-threads.reply.v1"' "$reply_out"
  grep -q 'resolveReviewThread' "$resolve_out"
  grep -q 'addPullRequestReviewThreadReply' "$reply_out"
}

run_review_thread_cleanup_gitlab_probe() {
  local workspace="$PR_WORKSPACE/review-thread-cleanup-gitlab"
  local out="$PR_ARTIFACTS_DIR/review-thread-cleanup-gitlab-resolve.json"
  local rc
  require_pr_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "feat/runtime-smoke-review-thread-cleanup-gitlab" \
    "git@gitlab.com:group/project.git"
  set +e
  (
    cd "$workspace"
    forge-cli --provider gitlab --repo group/project \
      --dry-run --format json pr review-threads resolve 123 --thread PRRT_x
  ) >"$out" 2>&1
  rc="$?"
  set -e
  [ "$rc" -ne 0 ] || return 1
  grep -q '"code":"provider_unsupported"' "$out"
}

assert_review_thread_cleanup_skill_documents_surface() {
  local skill="$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  local rc=0
  if [ ! -f "$skill" ]; then
    echo "runtime-smoke pr: missing $skill" >&2
    return 1
  fi
  grep -q 'pr review-threads list' "$skill" || rc=1
  grep -q 'reply and' "$skill" || rc=1
  grep -q 'resolve' "$skill" || rc=1
  grep -q 'review-thread-convergence' "$skill" || rc=1
  if [ "$rc" -ne 0 ]; then
    echo "runtime-smoke pr: $skill omits read/write surface or convergence policy reference" >&2
  fi
  return "$rc"
}

run_review_thread_cleanup_probe() {
  local rc=0
  run_review_thread_cleanup_github_probe || rc=1
  run_review_thread_cleanup_gitlab_probe || rc=1
  assert_review_thread_cleanup_skill_documents_surface || rc=1
  return "$rc"
}

run_pr_outcome_routing_probe() {
  local skill="$REPO_ROOT/core/skills/pr/deliver-pr/SKILL.md.tera"
  local rendered_helper="$REPO_ROOT/tests/runtime-smoke/lib/rendered-contract.sh"

  grep -Fq '## Lifecycle Mode Selection' "$skill"
  grep -Fq '**Create only**' "$skill"
  grep -Fq '**Deliver**' "$skill"
  grep -Fq '**Review repair**' "$skill"
  grep -Fq '**Merge**' "$skill"
  grep -Fq '**Close unmerged**' "$skill"
  grep -Fq '.agents/scripts/pre-pr.sh' "$skill"
  grep -Fq 'semantic-commit' "$skill"
  grep -Fq 'The user requests the PR/MR outcome, not a lifecycle helper.' "$skill"
  awk '
    /^## Workflow/ { in_workflow = 1; next }
    /^## Boundary/ { in_workflow = 0 }
    in_workflow && /close-unmerged mode/ { close_line = NR }
    in_workflow && /\.agents\/scripts\/pre-pr\.sh/ { pre_pr_line = NR }
    END { exit !(close_line && pre_pr_line && close_line < pre_pr_line) }
  ' "$skill"

  # Every rendered assertion must be able to bootstrap its product surface in
  # a standalone deterministic domain run from a clean checkout.
  grep -Fq 'rendered_contract_prepare_product "$product"' "$rendered_helper"

  rendered_contract_assert_skill pr deliver-pr
  rendered_contract_assert_all_contain pr deliver-pr '## Lifecycle Mode Selection'
  rendered_contract_assert_all_contain pr deliver-pr '**Close unmerged**'
  rendered_contract_assert_all_contain pr deliver-pr 'run `forge-cli pr close` and stop before delivery'
}

failures=0
record_case "pr.outcome-routing.create" "forge-cli GitHub+GitLab pr create dry-run passed" run_create_pr_probe
record_case "pr.outcome-routing.dispatch-lane" "forge-cli dispatch lane pr create dry-run passed" run_create_dispatch_lane_probe
record_case "pr.outcome-routing.close" "forge-cli GitHub+GitLab close dry-runs and optional specialist scope passed" run_close_pr_probe
record_case "pr.deliver-pr" "forge-cli GitHub+GitLab delivery macro and mandatory specialist scope passed" run_deliver_pr_probe
record_case "pr.outcome-routing.review-threads" "forge-cli review-threads resolve/reply offline dry-runs, GitLab fail-closed, and documented shared skill surface" run_review_thread_cleanup_probe
record_case "pr.outcome-routing.contract" "one governed PR/MR outcome selects create, deliver, repair, merge, and close modes internally" run_pr_outcome_routing_probe

exit "$failures"
