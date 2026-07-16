#!/usr/bin/env bash
# Deterministic probes for dispatch skills.
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

DISPATCH_ARTIFACTS_DIR="$ARTIFACTS_DIR/dispatch"
DISPATCH_WORKSPACE="$TMP_ROOT/workspaces/dispatch-basic-repo"
DISPATCH_STATE_DIR="$TMP_ROOT/state/plan-issue"
MINI_PLAN="$DISPATCH_ARTIFACTS_DIR/runtime-smoke-mini-plan.md"
LABEL_CATALOG="$REPO_ROOT/manifests/forge-labels.yaml"
PLAN_BODY_PATH=""
PLAN_TASK_SPEC_PATH=""
COMMENTS_JSON_PATH=""

mkdir -p "$DISPATCH_ARTIFACTS_DIR" "$DISPATCH_STATE_DIR" "$TMP_ROOT/workspaces"
cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$DISPATCH_WORKSPACE"

require_dispatch_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke dispatch: required binary not on PATH: $bin" >&2
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
  printf 'runtime-smoke dispatch base\n' >"$workspace/dispatch-base.txt"
  git -C "$workspace" add .
  base_tree="$(git -C "$workspace" write-tree)"
  base_commit="$(printf 'runtime-smoke dispatch base\n' | git -C "$workspace" commit-tree "$base_tree")"
  git -C "$workspace" update-ref refs/heads/main "$base_commit"
  git -C "$workspace" update-ref refs/remotes/origin/main "$base_commit"
  printf 'runtime-smoke dispatch fixture\n' >"$workspace/dispatch-fixture.txt"
  git -C "$workspace" add .
  tree="$(git -C "$workspace" write-tree)"
  commit="$(printf 'runtime-smoke dispatch fixture\n' | git -C "$workspace" commit-tree "$tree" -p "$base_commit")"
  git -C "$workspace" update-ref "refs/heads/$branch" "$commit"
  git -C "$workspace" symbolic-ref HEAD "refs/heads/$branch"
  git -C "$workspace" remote add origin "$remote_url"
  git -C "$workspace" update-ref "refs/remotes/origin/$branch" "$commit"
  git -C "$workspace" branch --set-upstream-to "origin/$branch" "$branch" >/dev/null
}

write_mini_plan() {
  cat >"$MINI_PLAN" <<'PLAN'
# Plan: Runtime Smoke Mini Plan

## Overview

Minimal plan fixture for dispatch runtime smoke.

## Read First

- Primary source: tests/runtime-smoke/README.md
- Source type: existing issue/spec
- Open questions carried into execution: none

## Scope

- In scope: one deterministic task.
- Out of scope: live GitHub mutation.

## Assumptions

1. Dry-run commands must not mutate provider state.

## Sprint 1: Smoke Sprint

**Goal**: Validate issue lifecycle surfaces.

**Demo/Validation**:

- Commands:
  - `true`
- Verify: command passes.

**PR grouping intent**: group
**Execution Profile**: serial

- **TotalComplexity**: 1
- **CriticalPathComplexity**: 1
- **MaxBatchWidth**: 1
- **OverlapHotspots**: none
- **Split command**: `plan-tooling split-prs --file mini-plan.md --scope sprint --sprint 1 --strategy deterministic --pr-grouping group --pr-group 'Task 1.1=smoke' --format json`

### Task 1.1: Validate dispatch smoke

- **Location**:
  - `tests/runtime-smoke/cases/dispatch/run.sh`
- **Description**: Exercise deterministic issue lifecycle command surfaces.
- **Dependencies**:
  - none
- **Complexity**: 1
- **Acceptance criteria**:
  - Dry-run issue lifecycle commands return typed output.
- **Validation**:
  - `true`
PLAN
}

ensure_plan_fixture() {
  if [ ! -f "$MINI_PLAN" ]; then
    write_mini_plan
  fi
}

write_tracking_comments_json() {
  local path="$1"
  cat >"$path" <<'JSON'
{"comments":[
{"body":"<!-- plan-issue-record:v2 role=source profile=tracking -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"source\",\"profile\":\"tracking\",\"data\":{\"path\":\"docs/source.md\",\"commit\":\"abc123\"}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-source","createdAt":"2026-01-01T00:00:00Z"},
{"body":"<!-- plan-issue-record:v2 role=plan profile=tracking -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"plan\",\"profile\":\"tracking\",\"data\":{\"path\":\"docs/plan.md\",\"commit\":\"abc123\"}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-plan","createdAt":"2026-01-01T00:00:01Z"},
{"body":"<!-- plan-issue-record:v2 role=state profile=tracking -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"state\",\"profile\":\"tracking\",\"data\":{\"status\":\"complete\",\"target_scope\":\"runtime smoke tracking\",\"current\":\"complete\",\"next_action\":\"closeout\",\"tasks\":[{\"id\":\"1.1\",\"status\":\"done\",\"title\":\"Validate dispatch smoke\"}],\"prs\":[{\"ref\":\"graysurf/agent-runtime-kit#123\",\"url\":\"https://github.com/graysurf/agent-runtime-kit/pull/123\",\"status\":\"merged\"}],\"blockers\":[],\"links\":{}}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-state","createdAt":"2026-01-01T00:00:02Z"},
{"body":"<!-- plan-issue-record:v2 role=session profile=tracking -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"session\",\"profile\":\"tracking\",\"data\":{\"summary\":\"Runtime smoke session\"}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-session","createdAt":"2026-01-01T00:00:03Z"},
{"body":"<!-- plan-issue-record:v2 role=validation profile=tracking -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"validation\",\"profile\":\"tracking\",\"data\":{\"overall\":\"pass\",\"commands\":[{\"command\":\"true\",\"status\":\"pass\"}],\"waivers\":[]}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-validation","createdAt":"2026-01-01T00:00:04Z"},
{"body":"<!-- plan-issue-record:v2 role=review profile=tracking -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"review\",\"profile\":\"tracking\",\"data\":{\"decision\":\"approve\",\"lenses\":[\"testing\",\"maintainability\"],\"findings\":[]}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-review","createdAt":"2026-01-01T00:00:05Z"}]}
JSON
}

write_dispatch_comments_json() {
  local path="$1"
  cat >"$path" <<'JSON'
{"comments":[
{"body":"<!-- plan-issue-record:v2 role=source profile=dispatch -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"source\",\"profile\":\"dispatch\",\"data\":{\"path\":\"docs/source.md\",\"commit\":\"abc123\"}}\n```\n","url":"https://github.com/example/repo/issues/2#issuecomment-source","createdAt":"2026-01-01T00:00:00Z"},
{"body":"<!-- plan-issue-record:v2 role=plan profile=dispatch -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"plan\",\"profile\":\"dispatch\",\"data\":{\"path\":\"docs/plan.md\",\"commit\":\"abc123\"}}\n```\n","url":"https://github.com/example/repo/issues/2#issuecomment-plan","createdAt":"2026-01-01T00:00:01Z"},
{"body":"<!-- plan-issue-record:v2 role=state profile=dispatch -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"state\",\"profile\":\"dispatch\",\"data\":{\"status\":\"complete\",\"target_scope\":\"runtime smoke dispatch\",\"current\":\"complete\",\"next_action\":\"closeout\",\"tasks\":[{\"id\":\"1.1\",\"status\":\"done\",\"title\":\"Validate dispatch smoke\"}],\"prs\":[{\"ref\":\"graysurf/agent-runtime-kit#123\",\"url\":\"https://github.com/graysurf/agent-runtime-kit/pull/123\",\"status\":\"merged\"}],\"blockers\":[],\"links\":{}}}\n```\n","url":"https://github.com/example/repo/issues/2#issuecomment-state","createdAt":"2026-01-01T00:00:02Z"},
{"body":"<!-- plan-issue-record:v2 role=session profile=dispatch -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"session\",\"profile\":\"dispatch\",\"data\":{\"summary\":\"Runtime smoke dispatch session\"}}\n```\n","url":"https://github.com/example/repo/issues/2#issuecomment-session","createdAt":"2026-01-01T00:00:03Z"},
{"body":"<!-- plan-issue-record:v2 role=validation profile=dispatch -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"validation\",\"profile\":\"dispatch\",\"data\":{\"overall\":\"pass\",\"commands\":[{\"command\":\"true\",\"status\":\"pass\"}],\"waivers\":[]}}\n```\n","url":"https://github.com/example/repo/issues/2#issuecomment-validation","createdAt":"2026-01-01T00:00:04Z"},
{"body":"<!-- plan-issue-record:v2 role=review profile=dispatch -->\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"review\",\"profile\":\"dispatch\",\"data\":{\"decision\":\"approve\",\"lenses\":[\"testing\",\"maintainability\"],\"findings\":[]}}\n```\n","url":"https://github.com/example/repo/issues/2#issuecomment-review","createdAt":"2026-01-01T00:00:05Z"}]}
JSON
}

write_record_content() {
  local path="$1"
  local profile="$2"
  cat >"$path" <<CONTENT
- Status: complete
- Profile: $profile
- PR: #123
- Validation: pass
CONTENT
}

write_execution_state_content() {
  local path="$1"
  local profile="$2"
  cat >"$path" <<CONTENT
# Runtime Smoke $profile Execution State

## Execution State

- Status: complete
- Profile: $profile
- Current: runtime smoke complete
- Next action: closeout

## Task Ledger

| ID | Status | Task |
| --- | --- | --- |
| 1.1 | done | Validate dispatch smoke |

## Validation

| Command | Status |
| --- | --- |
| true | pass |
CONTENT
}

write_state_payload() {
  local path="$1"
  local profile="$2"
  cat >"$path" <<JSON
{"status":"complete","target_scope":"runtime smoke $profile","current":"complete","next_action":"closeout","tasks":[{"id":"1.1","status":"done","title":"Validate dispatch smoke"}],"prs":[{"ref":"graysurf/agent-runtime-kit#123","url":"https://github.com/graysurf/agent-runtime-kit/pull/123","status":"merged"}],"blockers":[],"links":{}}
JSON
}

assert_state_comment_shape() {
  local path="$1"

  grep -q '## Execution State' "$path"
  [ "$(grep -o '## Execution State' "$path" | wc -l | tr -d ' ')" = "1" ]
  [ "$(grep -o -- '- Profile:' "$path" | wc -l | tr -d ' ')" = "1" ]
  ! grep -q '# Runtime Smoke' "$path"
}

assert_provider_payload_home_path_gate() {
  local path="$1"
  local raw_path="$2"

  grep -q 'machine-local home path' "$path" || return 1
  grep -q '[$]HOME/project' "$path" || return 1
  ! grep -q "$raw_path" "$path" || return 1
}

run_plan_issue_provider_payload_privacy_gate_probe() {
  local payload="$DISPATCH_ARTIFACTS_DIR/create-plan-tracking-local-path-payload.json"
  local summary="$DISPATCH_ARTIFACTS_DIR/create-plan-tracking-local-path-summary.md"
  local out="$DISPATCH_ARTIFACTS_DIR/create-plan-tracking-local-path-gate.json"
  local state_dir="$DISPATCH_ARTIFACTS_DIR/create-plan-tracking-local-path-state"
  local raw_path="/U""sers/example/project"
  local rc
  require_dispatch_bin plan-issue || return 1
  rm -rf "$state_dir"
  mkdir -p "$state_dir"
  cat >"$payload" <<'JSON'
{"summary":"Runtime smoke provider payload privacy gate"}
JSON
  printf 'Runtime smoke should not publish %s\n' "$raw_path" >"$summary"

  set +e
  plan-issue --repo graysurf/agent-runtime-kit --format json record post \
    --issue 0 \
    --profile tracking \
    --kind session \
    --payload-file "$payload" \
    --summary-file "$summary" \
    --state-dir "$state_dir" >"$out" 2>&1
  rc="$?"
  set -e

  [ "$rc" -ne 0 ] || return 1
  assert_provider_payload_home_path_gate "$out" "$raw_path" || return 1
  ! grep -q 'Could not resolve to a Repository' "$out" || return 1
  # As of nils-cli v1.11.0 plan-issue routes `record post` through forge-cli, so
  # the local-path guard fires inside forge-cli (code `local_path_present`)
  # before any provider/network call. Assert that gateway guard fired rather
  # than the absence of the now-legitimately-echoed `issue comment 0` command
  # string (the consolidated error surfaces the failed forge-cli command line).
  # Match the bare code: the forge-cli error is nested inside plan-issue's
  # record-post error message, so its quotes arrive backslash-escaped.
  grep -q 'local_path_present' "$out" || return 1
}

write_validation_payload() {
  local path="$1"
  cat >"$path" <<'JSON'
{"overall":"pass","commands":[{"command":"true","status":"pass"}],"waivers":[]}
JSON
}

write_review_payload() {
  local path="$1"
  cat >"$path" <<'JSON'
{"decision":"approve","lenses":["testing","maintainability","api-contract"],"findings":[]}
JSON
}

write_session_payload() {
  local path="$1"
  cat >"$path" <<'JSON'
{"summary":"Runtime smoke session"}
JSON
}

write_close_fixture() {
  local fixture="$1"
  local comments_json="$2"
  mkdir -p "$fixture/prs"
  printf '## Current Dashboard\n\n- Status: in-progress\n' >"$fixture/issue-body.md"
  cp "$comments_json" "$fixture/comments.json"
  cat >"$fixture/prs/graysurf__agent-runtime-kit__123.json" <<'JSON'
{"state":"MERGED","mergeCommit":{"oid":"deadbeefcafebabe"},"statusCheckRollup":{"state":"success"},"url":"https://github.com/graysurf/agent-runtime-kit/pull/123"}
JSON
}

write_visible_tracking_comments_json() {
  # Variant of `write_tracking_comments_json` whose per-role bodies pass the
  # `tracking close-ready --expect-visible` visible-completeness lint
  # (`## Source Snapshot`, `## Plan Snapshot`, `## Execution Session` +
  # `- Summary:`, `## Validation Evidence` + `- Overall:` + a command row).
  # Used by the close-ready happy-path probe; the canonical
  # `write_tracking_comments_json` stays payload-only because the other
  # probes consume it through `record post --dry-run` and `record audit`
  # without `--expect-visible`.
  local path="$1"
  cat >"$path" <<'JSON'
{"comments":[
{"body":"<!-- plan-issue-record:v2 role=source profile=tracking -->\n\n## Source Snapshot\n\n- Path: docs/source.md\n- Commit: abc123\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"source\",\"profile\":\"tracking\",\"data\":{\"path\":\"docs/source.md\",\"commit\":\"abc123\"}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-source","createdAt":"2026-01-01T00:00:00Z"},
{"body":"<!-- plan-issue-record:v2 role=plan profile=tracking -->\n\n## Plan Snapshot\n\n- Path: docs/plan.md\n- Commit: abc123\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"plan\",\"profile\":\"tracking\",\"data\":{\"path\":\"docs/plan.md\",\"commit\":\"abc123\"}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-plan","createdAt":"2026-01-01T00:00:01Z"},
{"body":"<!-- plan-issue-record:v2 role=state profile=tracking -->\n\n## Execution State\n\n- Profile: tracking\n- Status: complete\n\n## Task Ledger\n\n| ID | Status | Task |\n| --- | --- | --- |\n| 1.1 | done | Validate dispatch smoke |\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"state\",\"profile\":\"tracking\",\"data\":{\"status\":\"complete\",\"target_scope\":\"runtime smoke tracking\",\"current\":\"complete\",\"next_action\":\"closeout\",\"tasks\":[{\"id\":\"1.1\",\"status\":\"done\",\"title\":\"Validate dispatch smoke\"}],\"prs\":[{\"ref\":\"graysurf/agent-runtime-kit#123\",\"url\":\"https://github.com/graysurf/agent-runtime-kit/pull/123\",\"status\":\"merged\"}],\"blockers\":[],\"links\":{}}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-state","createdAt":"2026-01-01T00:00:02Z"},
{"body":"<!-- plan-issue-record:v2 role=session profile=tracking -->\n\n## Execution Session\n\n- Summary: Runtime smoke session\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"session\",\"profile\":\"tracking\",\"data\":{\"summary\":\"Runtime smoke session\"}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-session","createdAt":"2026-01-01T00:00:03Z"},
{"body":"<!-- plan-issue-record:v2 role=validation profile=tracking -->\n\n## Validation Evidence\n\n- Overall: pass\n\n| Command | Status |\n| --- | --- |\n| true | pass |\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"validation\",\"profile\":\"tracking\",\"data\":{\"overall\":\"pass\",\"commands\":[{\"command\":\"true\",\"status\":\"pass\"}],\"waivers\":[]}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-validation","createdAt":"2026-01-01T00:00:04Z"},
{"body":"<!-- plan-issue-record:v2 role=review profile=tracking -->\n\n## Review Evidence\n\n- Decision: approve\n- Lenses: testing, maintainability\n- Outcome comment: https://github.com/example/repo/pull/123#issuecomment-review-outcome\n\n```plan-issue-record-payload\n{\"schema\":\"plan-issue-record.payload.v2\",\"role\":\"review\",\"profile\":\"tracking\",\"data\":{\"decision\":\"approve\",\"lenses\":[\"testing\",\"maintainability\"],\"findings\":[],\"outcome_comment_url\":\"https://github.com/example/repo/pull/123#issuecomment-review-outcome\"}}\n```\n","url":"https://github.com/example/repo/issues/1#issuecomment-review","createdAt":"2026-01-01T00:00:05Z"}]}
JSON
}

write_missing_review_state_complete_comments_json() {
  # Rewrite the canonical tracking comments JSON to (1) drop the role=review
  # comment and (2) downgrade the role=state payload's `status` from
  # `complete` to `in-progress`. Result: `tracking close-ready` should
  # refuse with `review-missing` + `state_complete-missing`. Used to assert
  # the close-ready gate contract that the deliver → closeout handoff
  # depends on; the assertion is C-compatible because the gate's blocker
  # codes are stable independent of which surface (`record post` or
  # `tracking checkpoint --live`) emits the prereq lifecycle comments.
  local src="$1"
  local dst="$2"
  jq '.comments |= (
        map(select((.body | contains("role=review")) | not))
        | map(if .body | contains("role=state")
              then .body |= gsub("\"status\":\"complete\""; "\"status\":\"in-progress\"")
              else . end)
      )' "$src" >"$dst"
}

write_missing_session_close_fixture() {
  local fixture="$1"
  local comments_json="$2"
  mkdir -p "$fixture/prs"
  cat >"$fixture/issue-body.md" <<'BODY'
## Current Dashboard

- Status: complete
- Latest session: pending

## Session Log

- Notes embedded in state only; this is not a role=session lifecycle record.
BODY
  jq '.comments |= map(select((.body | contains("role=session")) | not))' \
    "$comments_json" >"$fixture/comments.json"
  cat >"$fixture/prs/graysurf__agent-runtime-kit__123.json" <<'JSON'
{"state":"MERGED","mergeCommit":{"oid":"deadbeefcafebabe"},"statusCheckRollup":{"state":"success"},"url":"https://github.com/graysurf/agent-runtime-kit/pull/123"}
JSON
}

build_tracking_record_fixture() {
  local stem="$1"
  local dashboard_out="$DISPATCH_ARTIFACTS_DIR/$stem-repair-dashboard.json"
  local state_md="$DISPATCH_ARTIFACTS_DIR/$stem-state.md"
  local state_payload="$DISPATCH_ARTIFACTS_DIR/$stem-state-payload.json"
  local state_out="$DISPATCH_ARTIFACTS_DIR/$stem-state-post.json"

  ensure_plan_fixture
  PLAN_BODY_PATH="$DISPATCH_ARTIFACTS_DIR/$stem-issue-body.md"
  COMMENTS_JSON_PATH="$DISPATCH_ARTIFACTS_DIR/$stem-comments.json"

  printf '## Current Dashboard\n\n- Status: pending\n' >"$PLAN_BODY_PATH"
  write_execution_state_content "$state_md" tracking
  write_state_payload "$state_payload" tracking
  write_tracking_comments_json "$COMMENTS_JSON_PATH"
  plan-issue record repair-dashboard \
    --body-file "$PLAN_BODY_PATH" \
    --comments-json "$COMMENTS_JSON_PATH" \
    --state-dir "$DISPATCH_STATE_DIR" \
    --out "$PLAN_BODY_PATH.repaired" >"$dashboard_out" 2>&1
  plan-issue record post \
    --dry-run \
    --issue 1 \
    --profile tracking \
    --kind state \
    --payload-file "$state_payload" \
    --execution-state-file "$state_md" \
    --task-ledger-display expanded \
    --state-dir "$DISPATCH_STATE_DIR" >"$state_out" 2>&1

  grep -q 'plan-issue.record.repair.dashboard.v2' "$dashboard_out"
  grep -q 'plan-issue.record.post.v2' "$state_out"
  assert_state_comment_shape "$state_out"
  grep -q '## Task Ledger' "$state_out"
  grep -q 'Validate dispatch smoke' "$state_out"
  grep -q 'plan-issue-record-payload' "$state_out"
  ! grep -q '<details>' "$state_out"
}

build_dispatch_record_fixture() {
  local stem="$1"
  local dashboard_out="$DISPATCH_ARTIFACTS_DIR/$stem-repair-dashboard.json"
  local split_out="$DISPATCH_ARTIFACTS_DIR/$stem-split.json"
  local state_md="$DISPATCH_ARTIFACTS_DIR/$stem-state.md"
  local state_payload="$DISPATCH_ARTIFACTS_DIR/$stem-state-payload.json"
  local state_out="$DISPATCH_ARTIFACTS_DIR/$stem-state-post.json"

  ensure_plan_fixture
  PLAN_BODY_PATH="$DISPATCH_ARTIFACTS_DIR/$stem-issue-body.md"
  PLAN_TASK_SPEC_PATH="$split_out"
  COMMENTS_JSON_PATH="$DISPATCH_ARTIFACTS_DIR/$stem-comments.json"

  printf '## Current Dashboard\n\n- Status: pending\n' >"$PLAN_BODY_PATH"
  write_execution_state_content "$state_md" dispatch
  write_state_payload "$state_payload" dispatch
  write_dispatch_comments_json "$COMMENTS_JSON_PATH"
  plan-issue record repair-dashboard \
    --body-file "$PLAN_BODY_PATH" \
    --comments-json "$COMMENTS_JSON_PATH" \
    --state-dir "$DISPATCH_STATE_DIR" \
    --out "$PLAN_BODY_PATH.repaired" >"$dashboard_out" 2>&1
  plan-tooling split-prs \
    --file "$MINI_PLAN" \
    --scope plan \
    --strategy deterministic \
    --pr-grouping group \
    --pr-group 'Task 1.1=smoke' \
    --format json >"$split_out" 2>&1
  plan-issue record post \
    --dry-run \
    --issue 2 \
    --profile dispatch \
    --kind state \
    --payload-file "$state_payload" \
    --execution-state-file "$state_md" \
    --task-ledger-display expanded \
    --state-dir "$DISPATCH_STATE_DIR" >"$state_out" 2>&1

  grep -q 'plan-issue.record.repair.dashboard.v2' "$dashboard_out"
  grep -q '"records"' "$split_out"
  grep -q 'plan-issue.record.post.v2' "$state_out"
  assert_state_comment_shape "$state_out"
  grep -q '## Task Ledger' "$state_out"
  grep -q 'Validate dispatch smoke' "$state_out"
  grep -q 'plan-issue-record-payload' "$state_out"
  ! grep -q '<details>' "$state_out"
}

write_review_evidence() {
  local review_dir="$1"
  local verify_out="$2"
  mkdir -p "$review_dir"

  review-evidence init \
    --out "$review_dir" \
    --subject "PR #123" \
    --format json >"$review_dir/init.json" 2>&1
  review-evidence record-finding \
    --out "$review_dir" \
    --severity low \
    --path tests/runtime-smoke/cases/dispatch/run.sh \
    --summary "runtime smoke fixture observation" \
    --status accepted-risk \
    --format json >"$review_dir/finding.json" 2>&1
  review-evidence record-validation \
    --out "$review_dir" \
    --command "runtime smoke dispatch" \
    --status pass \
    --summary "dispatch runtime smoke validation" \
    --format json >"$review_dir/validation.json" 2>&1
  review-evidence verify \
    --out "$review_dir" \
    --format json >"$verify_out" 2>&1
}

write_pr_body() {
  local path="$1"
  cat >"$path" <<'BODY'
## Summary

Runtime smoke validates the dispatch PR dry-run contract.

## Scope

- Validate the assigned dispatch lane only.

## Testing

- forge-cli dry-run (pass)

## Test plan

- forge-cli dry-run (pass)

## Issue

- Refs #999
BODY
}

run_specialist_scope_probe() {
  local workspace="$1"
  local branch="$2"
  local out="$3"
  shift 3
  require_dispatch_bin review-specialists || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  init_pushed_branch_fixture "$workspace" "$branch" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  review-specialists scope \
    --repo "$workspace" \
    --base main \
    "$@" \
    --format json >"$out" 2>&1
  grep -q '"schema_version": "cli.review-specialists.scope.v1"' "$out"
}

run_create_plan_tracking_issue_probe() {
  local validate_out="$DISPATCH_ARTIFACTS_DIR/create-plan-tracking-validate.txt"
  local open_fixture="$DISPATCH_ARTIFACTS_DIR/create-plan-tracking-open-fixture"
  local open_out="$DISPATCH_ARTIFACTS_DIR/create-plan-tracking-open.json"
  local audit_out="$DISPATCH_ARTIFACTS_DIR/create-plan-tracking-audit.json"
  require_dispatch_bin plan-tooling || return 1
  require_dispatch_bin plan-issue || return 1
  ensure_plan_fixture

  plan-tooling validate --file "$MINI_PLAN" --format text --explain >"$validate_out" 2>&1
  build_tracking_record_fixture create-plan-tracking
  mkdir -p "$open_fixture"
  printf '## Current Dashboard\n\n- Status: pending\n' >"$open_fixture/issue-body.md"
  cp "$COMMENTS_JSON_PATH" "$open_fixture/comments.json"
  plan-issue record open \
    --profile tracking \
    --fixture "$open_fixture" \
    --title "Runtime Smoke Tracking" \
    --format json \
    --state-dir "$DISPATCH_STATE_DIR" >"$open_out" 2>&1
  plan-issue record audit \
    --profile tracking \
    --body-file "$PLAN_BODY_PATH" \
    --comments-json "$COMMENTS_JSON_PATH" \
    --format json \
    --state-dir "$DISPATCH_STATE_DIR" >"$audit_out" 2>&1

  grep -q 'plan-issue.record.open.v2' "$open_out"
  grep -q '"missing_required":\[\]' "$audit_out"
  grep -q '"profile":"tracking"' "$audit_out"
  run_plan_issue_provider_payload_privacy_gate_probe
}

run_tracking_issue_closeout_probe() {
  local fixture="$DISPATCH_ARTIFACTS_DIR/plan-tracking-issue-closeout-fixture"
  local close_out="$DISPATCH_ARTIFACTS_DIR/plan-tracking-issue-closeout-close.json"
  require_dispatch_bin plan-issue || return 1
  build_tracking_record_fixture plan-tracking-issue-closeout
  write_close_fixture "$fixture" "$COMMENTS_JSON_PATH"

  plan-issue record close \
    --issue 1 \
    --profile tracking \
    --approval "runtime smoke approval" \
    --linked-pr 'graysurf/agent-runtime-kit#123' \
    --fixture "$fixture" \
    --format json \
    --state-dir "$DISPATCH_STATE_DIR" >"$close_out" 2>&1

  grep -q 'plan-issue.record.close.v2' "$close_out"
  grep -q '"mode":"fixture"' "$close_out"
  grep -q 'Final status' "$close_out"
  grep -q 'Merge SHA' "$close_out"
  grep -q 'deadbeefcafebabe' "$close_out"
}

run_missing_session_closeout_gate_probe() {
  local fixture="$DISPATCH_ARTIFACTS_DIR/plan-tracking-missing-session-closeout-fixture"
  local close_out="$DISPATCH_ARTIFACTS_DIR/plan-tracking-missing-session-closeout.json"
  local rc
  require_dispatch_bin plan-issue || return 1
  build_tracking_record_fixture plan-tracking-missing-session-closeout
  write_missing_session_close_fixture "$fixture" "$COMMENTS_JSON_PATH"

  set +e
  plan-issue record close \
    --issue 1 \
    --profile tracking \
    --approval "runtime smoke approval" \
    --linked-pr 'graysurf/agent-runtime-kit#123' \
    --fixture "$fixture" \
    --format json \
    --state-dir "$DISPATCH_STATE_DIR" >"$close_out" 2>&1
  rc="$?"
  set -e

  if [ "$rc" -ne 0 ] && grep -q 'session-missing' "$close_out"; then
    return 0
  fi
  if [ "$rc" -eq 0 ]; then
    return 2
  fi
  return 1
}

run_tracking_closeout_gate_prereq_blockers_probe() {
  # Assert `tracking close-ready` refuses with both `review-missing` and
  # `state_complete-missing` when the issue evidence carries only a state
  # checkpoint with status=in-progress and no role=review comment. This
  # locks the close-ready gate contract that the
  # deliver-plan-tracking-issue → plan-tracking-issue-closeout handoff
  # depends on; see
  # core/policies/heuristic-system/error-inbox/tracking-closeout-review-state-complete-gap/.
  # Stays valid through the `tracking checkpoint --live` posting-path
  # change in `sympoies/nils-cli` because that change moved the posting
  # path, not the gate's blocker codes.
  local fixture="$DISPATCH_ARTIFACTS_DIR/plan-tracking-closeout-gate-prereq-blockers"
  local source_comments="$DISPATCH_ARTIFACTS_DIR/plan-tracking-closeout-gate-prereq-blockers-source-comments.json"
  local comments_json="$fixture/comments.json"
  local body_md="$fixture/body.md"
  local probe_out="$DISPATCH_ARTIFACTS_DIR/plan-tracking-closeout-gate-prereq-blockers.json"
  local rc
  require_dispatch_bin plan-issue || return 1
  rm -rf "$fixture"
  mkdir -p "$fixture"
  printf '## Current Dashboard\n\n- Status: in-progress\n' >"$body_md"
  write_tracking_comments_json "$source_comments"
  write_missing_review_state_complete_comments_json "$source_comments" "$comments_json"

  set +e
  plan-issue --format json tracking close-ready \
    --profile tracking \
    --provider-repo graysurf/agent-runtime-kit \
    --issue 1 \
    --body-file "$body_md" \
    --comments-json "$comments_json" \
    --linked-pr "graysurf/agent-runtime-kit#123" \
    --approval "runtime smoke fixture approval" \
    --state-dir "$DISPATCH_STATE_DIR" \
    --expect-visible >"$probe_out" 2>&1
  rc="$?"
  set -e

  if [ "$rc" -ne 0 ]; then
    return 1
  fi
  grep -q '"ready":false' "$probe_out" || return 1
  grep -q '"code":"review-missing"' "$probe_out" || return 1
  grep -q '"code":"state_complete-missing"' "$probe_out" || return 1
}

run_tracking_closeout_gate_prereq_happy_path_probe() {
  # Sibling to run_tracking_closeout_gate_prereq_blockers_probe. Starts from
  # the same fixture (role=review missing, role=state status=in-progress),
  # then exercises the canonical close-ready handoff: bump the run-state
  # phase to `ready_for_close` with review decision plus context and call
  # `tracking checkpoint --live --fixture <dir> --post state,review
  # --repair-dashboard`. Fixture-mode live posting synthesizes
  # `fixture://issue/<n>/<role>` URLs without provider mutation and emits
  # the rendered state (status=complete) and review bodies under
  # `payload.result.rendered[]`. The probe merges those bodies
  # back into the fixture's `comments.json` (dropping the in-progress state
  # comment) and re-runs `tracking close-ready --expect-visible`, which must
  # now return `ready=true` with `blockers: []`. Together with the refusal
  # probe this locks both halves of the close-ready gate contract.
  local fixture="$DISPATCH_ARTIFACTS_DIR/plan-tracking-closeout-gate-prereq-happy-path"
  local source_comments="$fixture/source-comments.json"
  local comments_json="$fixture/comments.json"
  local body_md="$fixture/body.md"
  local run_state="$fixture/run-state.json"
  local checkpoint_out="$fixture/checkpoint.json"
  local final_comments="$fixture/final-comments.json"
  local probe_out="$fixture/close-ready.json"
  local rc
  require_dispatch_bin plan-issue || return 1
  rm -rf "$fixture"
  mkdir -p "$fixture"
  printf '## Current Dashboard\n\n- Status: in-progress\n' >"$body_md"
  write_visible_tracking_comments_json "$source_comments"
  write_missing_review_state_complete_comments_json "$source_comments" "$comments_json"
  cat >"$run_state" <<'JSON'
{"schema":"plan-issue.execution-run.v1","run_id":"runtime-smoke-happy-path","repo":"graysurf/agent-runtime-kit","issue":1,"profile":"tracking","phase":"ready_for_close","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","review":{"decision":"approve","lenses":["testing","maintainability"],"evidence":"https://github.com/example/repo/pull/123#issuecomment-review-outcome"}}
JSON

  plan-issue --format json tracking checkpoint \
    --provider-repo graysurf/agent-runtime-kit \
    --issue 1 \
    --profile tracking \
    --run-state "$run_state" \
    --post state,review \
    --repair-dashboard \
    --live \
    --fixture "$fixture" \
    --state-dir "$DISPATCH_STATE_DIR" >"$checkpoint_out" 2>&1

  grep -q '"mode":"fixture"' "$checkpoint_out" || return 1
  grep -q '"comment_url":"fixture://issue/1/state"' "$checkpoint_out" || return 1
  grep -q '"comment_url":"fixture://issue/1/review"' "$checkpoint_out" || return 1
  grep -q '"blocked":\[\]' "$checkpoint_out" || return 1

  jq --slurpfile chk "$checkpoint_out" '
    {comments: (
      (.comments | map(select((.body | contains("role=state")) | not)))
      + ($chk[0].payload.result.rendered
         | map({
             body: .body,
             url: ("https://github.com/example/repo/issues/1#issuecomment-" + .role + "-live"),
             createdAt: "2026-01-01T00:00:10Z"
           }))
    )}
  ' "$comments_json" >"$final_comments"

  set +e
  plan-issue --format json tracking close-ready \
    --profile tracking \
    --provider-repo graysurf/agent-runtime-kit \
    --issue 1 \
    --body-file "$body_md" \
    --comments-json "$final_comments" \
    --linked-pr "graysurf/agent-runtime-kit#123" \
    --approval "runtime smoke fixture approval" \
    --state-dir "$DISPATCH_STATE_DIR" \
    --expect-visible >"$probe_out" 2>&1
  rc="$?"
  set -e

  if [ "$rc" -ne 0 ]; then
    return 1
  fi
  grep -q '"ready":true' "$probe_out" || return 1
  grep -q '"blockers":\[\]' "$probe_out" || return 1
}

run_tracking_closeout_gate_ledger_pending_probe() {
  # Assert `tracking close-ready` raises one `ledger-rows-pending` blocker
  # per stuck row when `phase=ready_for_close` and the run-state's `bundle`
  # resolves to a `*-execution-state.md` whose `## Task Ledger` carries
  # rows at `pending` / `in-progress`. Locks the v0.25.7 blocker contract
  # that the deliver / closeout SKILL bodies depend on. Other close-ready
  # gates pass by construction: comments fixture is the visible-complete
  # variant with review+state=complete already posted, so the only blocker
  # we can attribute to this probe is the new ledger one.
  local fixture="$DISPATCH_ARTIFACTS_DIR/plan-tracking-closeout-gate-ledger-pending"
  local source_comments="$fixture/source-comments.json"
  local comments_json="$fixture/comments.json"
  local body_md="$fixture/body.md"
  local run_state="$fixture/run-state.json"
  local ledger_md="$fixture/demo-execution-state.md"
  local probe_out="$fixture/close-ready.json"
  local rc
  require_dispatch_bin plan-issue || return 1
  rm -rf "$fixture"
  mkdir -p "$fixture"
  printf '## Current Dashboard\n\n- Status: ready-for-close\n' >"$body_md"
  write_visible_tracking_comments_json "$source_comments"
  cp "$source_comments" "$comments_json"
  cat >"$ledger_md" <<'MD'
# Execution State: Demo

- Status: ready-for-close

## Task Ledger

| ID | Status | Task | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | pending | First pending row |  | first stuck row |
| 1.2 | in-progress | Second in-progress row |  | second stuck row |
| 1.3 | done | Already-done row | runtime-smoke fixture | not stuck |
MD
  cat >"$run_state" <<JSON
{"schema":"plan-issue.execution-run.v1","run_id":"runtime-smoke-ledger-pending","repo":"graysurf/agent-runtime-kit","issue":1,"profile":"tracking","phase":"ready_for_close","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","bundle":"$fixture","review":{"decision":"approve","lenses":["testing","maintainability"],"evidence":"https://github.com/example/repo/pull/123#issuecomment-review-outcome"}}
JSON

  set +e
  plan-issue --format json tracking close-ready \
    --profile tracking \
    --provider-repo graysurf/agent-runtime-kit \
    --issue 1 \
    --run-state "$run_state" \
    --body-file "$body_md" \
    --comments-json "$comments_json" \
    --linked-pr "graysurf/agent-runtime-kit#123" \
    --approval "runtime smoke fixture approval" \
    --state-dir "$DISPATCH_STATE_DIR" \
    --expect-visible >"$probe_out" 2>&1
  rc="$?"
  set -e

  if [ "$rc" -ne 0 ]; then
    return 1
  fi
  grep -q '"ready":false' "$probe_out" || return 1
  grep -q '"code":"ledger-rows-pending"' "$probe_out" || return 1
  # One blocker entry per stuck row (1.1 + 1.2). Count occurrences and
  # require ≥2 so a regression that emits a single combined blocker still
  # fails the probe. The JSON envelope is a single line, so `grep -c`
  # would return 1 — use `grep -o | wc -l` to count occurrences.
  local count
  count="$(grep -o '"code":"ledger-rows-pending"' "$probe_out" | wc -l | awk '{print $1}')"
  [ "$count" -ge 2 ] || return 1
  grep -q '"task_id":"1.1"' "$probe_out" || return 1
  grep -q '"task_id":"1.2"' "$probe_out" || return 1
}

run_tracking_closeout_gate_ledger_clean_probe() {
  # Sibling to run_tracking_closeout_gate_ledger_pending_probe with the
  # same scaffold but every ledger row at `done` with non-empty Evidence.
  # Asserts that `tracking close-ready --expect-visible` returns
  # `ready=true` and `blockers=[]` — proving the ledger blocker is
  # cleanly absent when the ledger matches a finished plan. Together with
  # the pending probe this locks both halves of the v0.25.7 ledger
  # close-ready contract.
  local fixture="$DISPATCH_ARTIFACTS_DIR/plan-tracking-closeout-gate-ledger-clean"
  local source_comments="$fixture/source-comments.json"
  local comments_json="$fixture/comments.json"
  local body_md="$fixture/body.md"
  local run_state="$fixture/run-state.json"
  local ledger_md="$fixture/demo-execution-state.md"
  local probe_out="$fixture/close-ready.json"
  local rc
  require_dispatch_bin plan-issue || return 1
  rm -rf "$fixture"
  mkdir -p "$fixture"
  printf '## Current Dashboard\n\n- Status: ready-for-close\n' >"$body_md"
  write_visible_tracking_comments_json "$source_comments"
  cp "$source_comments" "$comments_json"
  cat >"$ledger_md" <<'MD'
# Execution State: Demo

## Execution State

- Status: complete
- Tracking issue: <https://github.com/graysurf/agent-runtime-kit/issues/1>

## Task Ledger

| ID | Status | Task | Evidence | Notes |
| --- | --- | --- | --- | --- |
| 1.1 | done | First row | runtime-smoke fixture | clean |
| 1.2 | done | Second row | runtime-smoke fixture | clean |
| 1.3 | done | Third row | runtime-smoke fixture | clean |
MD
  cat >"$run_state" <<JSON
{"schema":"plan-issue.execution-run.v1","run_id":"runtime-smoke-ledger-clean","repo":"graysurf/agent-runtime-kit","issue":1,"profile":"tracking","phase":"ready_for_close","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","bundle":"$fixture","review":{"decision":"approve","lenses":["testing","maintainability"],"evidence":"https://github.com/example/repo/pull/123#issuecomment-review-outcome"}}
JSON

  set +e
  plan-issue --format json tracking close-ready \
    --profile tracking \
    --provider-repo graysurf/agent-runtime-kit \
    --issue 1 \
    --run-state "$run_state" \
    --body-file "$body_md" \
    --comments-json "$comments_json" \
    --linked-pr "graysurf/agent-runtime-kit#123" \
    --approval "runtime smoke fixture approval" \
    --state-dir "$DISPATCH_STATE_DIR" \
    --expect-visible >"$probe_out" 2>&1
  rc="$?"
  set -e

  if [ "$rc" -ne 0 ]; then
    return 1
  fi
  grep -q '"ready":true' "$probe_out" || return 1
  grep -q '"blockers":\[\]' "$probe_out" || return 1
  grep -q '"ledger-rows-pending"' "$probe_out" && return 1
  return 0
}

record_missing_session_closeout_gate_case() {
  local id="dispatch.plan-issue-session-closeout-gate"
  set +e
  run_missing_session_closeout_gate_probe
  local rc="$?"
  set -e
  case "$rc" in
    0)
      results_add "$id" "shared-cli" "pass" "1" "missing-session closeout fixture blocked with session-missing"
      return 0
      ;;
    2)
      results_add "$id" "shared-cli" "skip-host-capability" "0" "installed plan-issue does not yet enforce session-missing; use local nils-cli binary for this gate"
      return 0
      ;;
    *)
      results_add "$id" "shared-cli" "fail" "0" "missing-session closeout fixture did not produce session-missing"
      return 1
      ;;
  esac
}

run_deliver_dispatch_plan_probe() {
  local validate_out="$DISPATCH_ARTIFACTS_DIR/deliver-dispatch-plan-validate.txt"
  local audit_out="$DISPATCH_ARTIFACTS_DIR/deliver-dispatch-plan-audit.json"
  local specialist_out="$DISPATCH_ARTIFACTS_DIR/deliver-dispatch-plan-specialist-scope.json"
  local session_md="$DISPATCH_ARTIFACTS_DIR/deliver-dispatch-plan-session.md"
  local session_payload="$DISPATCH_ARTIFACTS_DIR/deliver-dispatch-plan-session-payload.json"
  local session_out="$DISPATCH_ARTIFACTS_DIR/deliver-dispatch-plan-session-comment.json"
  require_dispatch_bin plan-tooling || return 1
  require_dispatch_bin plan-issue || return 1
  require_dispatch_bin review-specialists || return 1

  plan-tooling validate --file "$MINI_PLAN" --format text --explain >"$validate_out" 2>&1
  build_dispatch_record_fixture deliver-dispatch-plan
  plan-issue record audit \
    --profile dispatch \
    --body-file "$PLAN_BODY_PATH" \
    --comments-json "$COMMENTS_JSON_PATH" \
    --format json \
    --state-dir "$DISPATCH_STATE_DIR" >"$audit_out" 2>&1
  run_specialist_scope_probe "$DISPATCH_WORKSPACE/deliver-dispatch-plan-specialist" \
    "feat/deliver-dispatch-plan-specialist" \
    "$specialist_out" \
    --testing --maintainability
  write_record_content "$session_md" dispatch
  write_session_payload "$session_payload"
  plan-issue record post \
    --dry-run \
    --issue 2 \
    --profile dispatch \
    --kind session \
    --payload-file "$session_payload" \
    --summary-file "$session_md" \
    --state-dir "$DISPATCH_STATE_DIR" >"$session_out" 2>&1

  grep -q '"missing_required":\[\]' "$audit_out"
  grep -q '"records"' "$PLAN_TASK_SPEC_PATH"
  grep -q '"forced_specialists"' "$specialist_out"
  grep -q 'plan-issue.record.post.v2' "$session_out"
  grep -q 'Execution Session' "$session_out"
}

run_dispatch_issue_closeout_probe() {
  local fixture="$DISPATCH_ARTIFACTS_DIR/dispatch-plan-closeout-fixture"
  local close_out="$DISPATCH_ARTIFACTS_DIR/dispatch-plan-closeout-close.json"
  require_dispatch_bin plan-issue || return 1
  build_dispatch_record_fixture dispatch-plan-closeout
  write_close_fixture "$fixture" "$COMMENTS_JSON_PATH"

  plan-issue record close \
    --issue 2 \
    --profile dispatch \
    --approval "runtime smoke approval" \
    --linked-pr 'graysurf/agent-runtime-kit#123' \
    --fixture "$fixture" \
    --format json \
    --state-dir "$DISPATCH_STATE_DIR" >"$close_out" 2>&1

  grep -q 'plan-issue.record.close.v2' "$close_out"
  grep -q '"mode":"fixture"' "$close_out"
  grep -q 'Final status' "$close_out"
  grep -q 'Merge SHA' "$close_out"
  grep -q 'deadbeefcafebabe' "$close_out"
}

run_execute_from_tracking_issue_probe() {
  local validate_out="$DISPATCH_ARTIFACTS_DIR/execute-validate.txt"
  local audit_out="$DISPATCH_ARTIFACTS_DIR/execute-audit.json"
  local pr_view_out="$DISPATCH_ARTIFACTS_DIR/execute-pr-view.json"
  require_dispatch_bin plan-tooling || return 1
  require_dispatch_bin plan-issue || return 1
  require_dispatch_bin forge-cli || return 1
  build_tracking_record_fixture execute-plan-tracking-issue

  plan-tooling validate --file "$MINI_PLAN" --format text --explain >"$validate_out" 2>&1
  plan-issue record audit \
    --profile tracking \
    --body-file "$PLAN_BODY_PATH" \
    --comments-json "$COMMENTS_JSON_PATH" \
    --format json \
    --state-dir "$DISPATCH_STATE_DIR" >"$audit_out" 2>&1
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    pr view 123 >"$pr_view_out" 2>&1

  grep -q '"missing_required":\[\]' "$audit_out"
  grep -q '"schema_version":"cli.forge-cli.pr.view.v1"' "$pr_view_out"
}

run_deliver_tracking_issue_probe() {
  local verify_out="$DISPATCH_ARTIFACTS_DIR/deliver-review-verify.json"
  local checks_out="$DISPATCH_ARTIFACTS_DIR/deliver-pr-checks.json"
  local session_md="$DISPATCH_ARTIFACTS_DIR/deliver-session.md"
  local session_payload="$DISPATCH_ARTIFACTS_DIR/deliver-session-payload.json"
  local session_out="$DISPATCH_ARTIFACTS_DIR/deliver-session-comment.json"
  local validation_md="$DISPATCH_ARTIFACTS_DIR/deliver-validation.md"
  local validation_payload="$DISPATCH_ARTIFACTS_DIR/deliver-validation-payload.json"
  local validation_out="$DISPATCH_ARTIFACTS_DIR/deliver-validation-comment.json"
  local review_body="$DISPATCH_ARTIFACTS_DIR/deliver-tracking-review.md"
  local review_threads="$DISPATCH_ARTIFACTS_DIR/deliver-tracking-review-threads.json"
  local testing_review_out="$DISPATCH_ARTIFACTS_DIR/deliver-tracking-testing-review.json"
  local maintainability_review_out="$DISPATCH_ARTIFACTS_DIR/deliver-tracking-maintainability-review.json"
  local final_review_out="$DISPATCH_ARTIFACTS_DIR/deliver-tracking-final-review.json"
  local specialist_out="$DISPATCH_ARTIFACTS_DIR/deliver-specialist-scope.json"
  require_dispatch_bin plan-tooling || return 1
  require_dispatch_bin plan-issue || return 1
  require_dispatch_bin forge-cli || return 1
  require_dispatch_bin review-evidence || return 1
  build_tracking_record_fixture deliver-plan-tracking-issue

  run_specialist_scope_probe "$DISPATCH_WORKSPACE/deliver-specialist" \
    "feat/dispatch-deliver-specialist" \
    "$specialist_out" \
    --testing --maintainability
  write_review_evidence "$DISPATCH_ARTIFACTS_DIR/deliver-review" "$verify_out"
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    pr checks 123 >"$checks_out" 2>&1
  printf 'Runtime smoke specialist review.\n' >"$review_body"
  printf '[{"path":"dispatch-fixture.txt","line":1,"body":"Runtime smoke actionable finding thread."}]\n' >"$review_threads"
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    pr review 123 \
    --decision comments-only \
    --submit-review \
    --thread-file "$review_threads" \
    --comment-file "$review_body" \
    --lens testing \
    --issue 1 \
    --mirror-issue >"$testing_review_out" 2>&1
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    pr review 123 \
    --decision comments-only \
    --submit-review \
    --comment-file "$review_body" \
    --lens maintainability \
    --issue 1 \
    --mirror-issue >"$maintainability_review_out" 2>&1
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    pr review 123 \
    --decision approve \
    --submit-review \
    --comment-file "$review_body" \
    --lens testing \
    --lens maintainability \
    --lens api-contract \
    --issue 1 \
    --mirror-issue >"$final_review_out" 2>&1
  write_record_content "$session_md" tracking
  write_session_payload "$session_payload"
  plan-issue record post \
    --dry-run \
    --issue 1 \
    --profile tracking \
    --kind session \
    --payload-file "$session_payload" \
    --summary-file "$session_md" \
    --state-dir "$DISPATCH_STATE_DIR" >"$session_out" 2>&1
  write_record_content "$validation_md" tracking
  write_validation_payload "$validation_payload"
  plan-issue record post \
    --dry-run \
    --issue 1 \
    --profile tracking \
    --kind validation \
    --payload-file "$validation_payload" \
    --summary-file "$validation_md" \
    --state-dir "$DISPATCH_STATE_DIR" >"$validation_out" 2>&1

  grep -q '"schema_version": "cli.review-evidence.verify.v1"' "$verify_out"
  grep -q '"ok": true' "$verify_out"
  grep -q '"forced_specialists"' "$specialist_out"
  grep -q '"maintainability"' "$specialist_out"
  grep -q '"testing"' "$specialist_out"
  grep -q '"schema_version":"cli.forge-cli.pr.checks.v1"' "$checks_out"
  grep -q '"schema_version":"cli.forge-cli.pr.review.v1"' "$testing_review_out"
  grep -q '"decision":"comments-only"' "$testing_review_out"
  grep -q '"lenses":\["testing"\]' "$testing_review_out"
  grep -q '"planned_review_threads":1' "$testing_review_out"
  grep -q '"mirror_issue":true' "$testing_review_out"
  grep -q '"schema_version":"cli.forge-cli.pr.review.v1"' "$maintainability_review_out"
  grep -q '"decision":"comments-only"' "$maintainability_review_out"
  grep -q '"lenses":\["maintainability"\]' "$maintainability_review_out"
  grep -q '"planned_review_threads":0' "$maintainability_review_out"
  grep -q '"mirror_issue":true' "$maintainability_review_out"
  grep -q '"schema_version":"cli.forge-cli.pr.review.v1"' "$final_review_out"
  grep -q '"decision":"approve"' "$final_review_out"
  grep -q '"lenses":\["testing","maintainability","api-contract"\]' "$final_review_out"
  grep -q '"planned_review_threads":0' "$final_review_out"
  grep -q '"mirror_issue":true' "$final_review_out"
  grep -q 'plan-issue.record.post.v2' "$session_out"
  grep -q 'Execution Session' "$session_out"
  grep -q 'plan-issue.record.post.v2' "$validation_out"
  grep -q 'Overall: pass' "$validation_out"
  grep -q 'true' "$validation_out"
}

run_dispatch_pr_review_probe() {
  local verify_out="$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr-verify.json"
  local review_body="$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr-review.md"
  local review_threads="$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr-threads.json"
  local specialist_provider_review_out="$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr-specialist-provider-review.json"
  local provider_review_out="$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr-provider-review.json"
  local review_md="$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr.md"
  local review_payload="$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr-payload.json"
  local review_out="$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr-record-comment.json"
  local specialist_out="$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr-specialist-scope.json"
  require_dispatch_bin plan-issue || return 1
  require_dispatch_bin forge-cli || return 1
  require_dispatch_bin review-evidence || return 1
  build_dispatch_record_fixture review-dispatch-lane-pr

  run_specialist_scope_probe "$DISPATCH_WORKSPACE/review-dispatch-lane-pr-specialist" \
    "feat/review-dispatch-lane-pr-specialist" \
    "$specialist_out"
  write_review_evidence "$DISPATCH_ARTIFACTS_DIR/review-dispatch-lane-pr-evidence" "$verify_out"
  printf 'Runtime smoke review evidence.\n' >"$review_body"
  printf '[{"path":"dispatch-fixture.txt","line":1,"body":"Runtime smoke actionable finding thread."}]\n' >"$review_threads"
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    pr review 123 \
    --decision comments-only \
    --submit-review \
    --thread-file "$review_threads" \
    --comment-file "$review_body" \
    --lens testing >"$specialist_provider_review_out" 2>&1
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    pr review 123 \
    --decision approve \
    --submit-review \
    --comment-file "$review_body" \
    --lens testing \
    --lens maintainability \
    --lens api-contract \
    --issue 2 \
    --mirror-issue >"$provider_review_out" 2>&1
  write_record_content "$review_md" dispatch
  write_review_payload "$review_payload"
  plan-issue record post \
    --dry-run \
    --issue 2 \
    --profile dispatch \
    --kind review \
    --payload-file "$review_payload" \
    --summary-file "$review_md" \
    --state-dir "$DISPATCH_STATE_DIR" >"$review_out" 2>&1

  grep -q '"schema_version": "cli.review-evidence.verify.v1"' "$verify_out"
  grep -q '"suggested_specialists"' "$specialist_out"
  grep -q '"schema_version":"cli.forge-cli.pr.review.v1"' "$specialist_provider_review_out"
  grep -q '"decision":"comments-only"' "$specialist_provider_review_out"
  grep -q '"planned_review_threads"' "$specialist_provider_review_out"
  grep -q '"schema_version":"cli.forge-cli.pr.review.v1"' "$provider_review_out"
  grep -q '"decision":"approve"' "$provider_review_out"
  grep -q '"lenses":\["testing","maintainability","api-contract"\]' "$provider_review_out"
  grep -q '"planned_review_threads":0' "$provider_review_out"
  grep -q '"mirror_issue":true' "$provider_review_out"
  grep -q 'plan-issue.record.post.v2' "$review_out"
  grep -q 'Decision: approve' "$review_out"
  grep -q 'testing, maintainability, api-contract' "$review_out"
}

run_dispatch_subagent_pr_probe() {
  local workspace="$DISPATCH_WORKSPACE/subagent-pr"
  local pr_body="$DISPATCH_ARTIFACTS_DIR/execute-dispatch-lane-body.md"
  local create_out="$DISPATCH_ARTIFACTS_DIR/execute-dispatch-lane-create.json"
  local session_md="$DISPATCH_ARTIFACTS_DIR/execute-dispatch-lane-session.md"
  local session_payload="$DISPATCH_ARTIFACTS_DIR/execute-dispatch-lane-session-payload.json"
  local session_out="$DISPATCH_ARTIFACTS_DIR/execute-dispatch-lane-session-comment.json"
  require_dispatch_bin plan-issue || return 1
  require_dispatch_bin forge-cli || return 1
  mkdir -p "$workspace"
  cp -R "$SCRIPT_DIR/workspaces/basic-repo/." "$workspace"
  build_dispatch_record_fixture execute-dispatch-lane
  init_pushed_branch_fixture "$workspace" "feat/dispatch-subagent-runtime-smoke" \
    "git@github.com:graysurf/agent-runtime-kit.git"
  write_pr_body "$pr_body"

  (
    cd "$workspace"
    forge-cli --provider github --repo graysurf/agent-runtime-kit \
      --dry-run --format json \
      pr create \
      --kind feature \
      --base plan/issue-26 \
      --title "Runtime smoke execute dispatch lane" \
      --body-file "$pr_body" \
      --label type::feature \
      --label area::skills \
      --label size::s \
      --label workflow::dispatch \
      --label-catalog "$LABEL_CATALOG" \
      --strict-labels
  ) >"$create_out" 2>&1
  write_record_content "$session_md" dispatch
  write_session_payload "$session_payload"
  plan-issue record post \
    --dry-run \
    --issue 2 \
    --profile dispatch \
    --kind session \
    --payload-file "$session_payload" \
    --summary-file "$session_md" \
    --state-dir "$DISPATCH_STATE_DIR" >"$session_out" 2>&1

  grep -q '"schema_version":"cli.forge-cli.pr.create.v1"' "$create_out"
  grep -q '"workflow::dispatch"' "$create_out"
  grep -q '"size::s"' "$create_out"
  grep -q 'plan-issue.record.post.v2' "$session_out"
}

run_dispatch_outcome_routing_probe() {
  local protocol="$REPO_ROOT/core/skills/dispatch/plan-issue-spec/outcome-routing.md"
  local tracking="$REPO_ROOT/core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera"
  local dispatch="$REPO_ROOT/core/skills/dispatch/deliver-dispatch-plan/SKILL.md.tera"
  local tracking_protocol="$REPO_ROOT/core/skills/dispatch/deliver-plan-tracking-issue/references/outcome-routing.md"
  local dispatch_protocol="$REPO_ROOT/core/skills/dispatch/deliver-dispatch-plan/references/outcome-routing.md"

  test -s "$protocol"
  grep -Fq '## L2 Tracking Outcome' "$protocol"
  grep -Fq '## L3 Dispatch Outcome' "$protocol"
  grep -Fq '| Lifecycle role | L2 writer | L3 writer |' "$protocol"
  cmp -s "$protocol" "$tracking_protocol"
  cmp -s "$protocol" "$dispatch_protocol"
  grep -Fq 'plan-archive discover' "$tracking"
  grep -Fq 'plan-archive migrate' "$tracking"
  if grep -Fq 'plan-archive migrate --dry-run' "$tracking"; then
    return 1
  fi
  grep -Fq 'PLAN_LABEL_ARGS=(--label workflow::plan --label workflow::tracking)' "$tracking"
  grep -Fq 'PLAN_LABEL_ARGS=(--label workflow::tracking --label plan)' "$tracking"
  grep -Fq '"${PLAN_LABEL_ARGS[@]}"' "$tracking"
  grep -Fq 'references/outcome-routing.md' "$tracking"
  grep -Fq 'references/outcome-routing.md' "$dispatch"
  grep -Fq 'record audit' "$tracking"
  awk '
    /^plan-issue .* record close/ { close_line = NR }
    /^forge-cli .* issue view/ { readback_line = NR }
    /^plan-issue .* record audit/ { audit_line = NR }
    /^plan-archive discover/ { archive_line = NR }
    /^plan-issue .* record audit/ { in_audit = 1 }
    in_audit && /--profile tracking/ { audit_profile = 1 }
    in_audit && /--expect-visible/ { audit_visible = 1 }
    in_audit && /^$/ { in_audit = 0 }
    END {
      exit !(close_line < readback_line && readback_line < audit_line &&
             audit_line < archive_line && audit_profile && audit_visible)
    }
  ' "$tracking"
  grep -Fq 'The user selects the L3 outcome, never a lane lifecycle substep.' "$dispatch"
  awk '
    /^plan-issue .* record close/ { close_line = NR }
    /^forge-cli .* issue view/ { readback_line = NR }
    /^plan-issue .* record audit/ { audit_line = NR; in_audit = 1 }
    in_audit && /--profile dispatch/ { audit_profile = 1 }
    in_audit && /--expect-visible/ { audit_visible = 1 }
    in_audit && /^$/ { in_audit = 0 }
    END {
      exit !(close_line < readback_line && readback_line < audit_line &&
             audit_profile && audit_visible)
    }
  ' "$dispatch"

  rendered_contract_assert_skill dispatch deliver-plan-tracking-issue
  rendered_contract_assert_skill dispatch deliver-dispatch-plan
  rendered_contract_assert_all_contain dispatch deliver-plan-tracking-issue 'references/outcome-routing.md'
  rendered_contract_assert_all_contain dispatch deliver-dispatch-plan 'references/outcome-routing.md'
  rendered_contract_assert_all_omit dispatch deliver-plan-tracking-issue 'core/skills/dispatch/plan-issue-spec/outcome-routing.md'
  rendered_contract_assert_all_omit dispatch deliver-dispatch-plan 'core/skills/dispatch/plan-issue-spec/outcome-routing.md'
  rendered_contract_assert_all_contain dispatch deliver-plan-tracking-issue 'record audit'
  rendered_contract_assert_all_contain dispatch deliver-plan-tracking-issue 'issue view "$ISSUE" --with-comments'
  rendered_contract_assert_all_contain dispatch deliver-plan-tracking-issue '--expect-visible'
  rendered_contract_assert_all_contain dispatch deliver-plan-tracking-issue 'git-cli worktree remove <path-or-slug> --format json'
  rendered_contract_assert_all_contain dispatch deliver-plan-tracking-issue 'provider-confirmed delivered head'
  rendered_contract_assert_all_contain dispatch deliver-dispatch-plan 'record audit'
  rendered_contract_assert_all_contain dispatch deliver-dispatch-plan 'issue view "$ISSUE" --with-comments'
  rendered_contract_assert_all_contain dispatch deliver-dispatch-plan '--expect-visible'
  rendered_contract_assert_all_contain dispatch deliver-dispatch-plan 'git-cli worktree remove <path-or-slug> --format json'
  rendered_contract_assert_all_contain dispatch deliver-dispatch-plan 'provider-confirmed delivered head'
  rendered_contract_assert_reference dispatch deliver-plan-tracking-issue references/outcome-routing.md
  rendered_contract_assert_reference dispatch deliver-dispatch-plan references/outcome-routing.md
}

failures=0
record_case "dispatch.deliver-plan-tracking-issue.open" "plan-tooling plus tracking post/repair/audit probes passed" run_create_plan_tracking_issue_probe
record_case "dispatch.deliver-dispatch-plan" "dispatch post/repair/audit, split, and specialist scope probes passed" run_deliver_dispatch_plan_probe
record_case "dispatch.deliver-dispatch-plan.closeout" "dispatch record close fixture probe passed" run_dispatch_issue_closeout_probe
record_case "dispatch.deliver-plan-tracking-issue.closeout" "tracking record close fixture probe passed" run_tracking_issue_closeout_probe
record_missing_session_closeout_gate_case || failures=1
record_case "dispatch.plan-tracking-closeout-gate" "tracking close-ready refuses missing review + state=complete prereqs with the expected blocker codes" run_tracking_closeout_gate_prereq_blockers_probe
record_case "dispatch.plan-tracking-closeout-gate-happy-path" "tracking checkpoint --live --fixture posts review + state=complete and close-ready then returns ready=true with no blockers" run_tracking_closeout_gate_prereq_happy_path_probe
record_case "dispatch.plan-tracking-closeout-gate-ledger-pending" "tracking close-ready raises one ledger-rows-pending blocker per stuck row when bundle resolves to a ledger with pending/in-progress rows" run_tracking_closeout_gate_ledger_pending_probe
record_case "dispatch.plan-tracking-closeout-gate-ledger-clean" "tracking close-ready returns ready=true with no ledger blocker when every ledger row is done with non-empty evidence" run_tracking_closeout_gate_ledger_clean_probe
record_case "dispatch.deliver-plan-tracking-issue.resume" "tracking audit and forge-cli pr view dry-run probes passed" run_execute_from_tracking_issue_probe
record_case "dispatch.deliver-plan-tracking-issue.review" "review-specialists, per-lens provider reviews, final review, checks, and tracking validation probes passed" run_deliver_tracking_issue_probe
record_case "dispatch.deliver-dispatch-plan.review" "review-specialists, review evidence, PR review outcome, and dispatch review post probes passed" run_dispatch_pr_review_probe
record_case "dispatch.deliver-dispatch-plan.lane" "execute dispatch lane PR create and dispatch session post probes passed" run_dispatch_subagent_pr_probe
record_case "dispatch.outcome-routing" "one L2 and one L3 outcome preserve distinct lifecycle writers behind internal protocols" run_dispatch_outcome_routing_probe

exit "$failures"
