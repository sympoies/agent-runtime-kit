#!/usr/bin/env bash
# Deterministic probes for provider issue workflow skills.
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
# shellcheck disable=SC1091
# shellcheck source=tests/runtime-smoke/lib/tracker-commands.sh
. "$SCRIPT_DIR/lib/tracker-commands.sh"

ISSUE_ARTIFACTS_DIR="$ARTIFACTS_DIR/issue"
ISSUE_TRACKER_MODE="$(tracker_commands_mode)"
mkdir -p "$ISSUE_ARTIFACTS_DIR"

require_issue_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "runtime-smoke issue: required binary not on PATH: $bin" >&2
    return 1
  fi
}

record_case() {
  results_record_case "$@"
}

run_issue_follow_up_probe() {
  local body="$ISSUE_ARTIFACTS_DIR/issue-body.md"
  local comment="$ISSUE_ARTIFACTS_DIR/comment.md"
  local create_out="$ISSUE_ARTIFACTS_DIR/create.json"
  local view_out="$ISSUE_ARTIFACTS_DIR/view.json"
  local comment_out="$ISSUE_ARTIFACTS_DIR/comment.json"
  require_issue_bin forge-cli || return 1

  printf 'Runtime smoke issue follow-up body.\n' >"$body"
  printf 'Runtime smoke follow-up checkpoint.\n' >"$comment"

  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    issue create \
    --title "Runtime smoke issue follow-up" \
    --body-file "$body" \
    --label type::bug \
    --label area::runtime \
    --label state::needs-triage \
    --label workflow::follow-up \
    --label issue >"$create_out" 2>&1
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    issue view 123 >"$view_out" 2>&1
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    issue comment 123 \
    --body-file "$comment" >"$comment_out" 2>&1

  grep -q '"schema_version":"cli.forge-cli.issue.create.v1"' "$create_out"
  grep -q '"type::bug"' "$create_out"
  grep -q '"area::runtime"' "$create_out"
  grep -q '"state::needs-triage"' "$create_out"
  grep -q '"workflow::follow-up"' "$create_out"
  grep -q '"schema_version":"cli.forge-cli.issue.view.v1"' "$view_out"
  grep -q '"schema_version":"cli.forge-cli.issue.comment.v1"' "$comment_out"
}

run_issue_triage_probe() {
  local status_out="$ISSUE_ARTIFACTS_DIR/inbox-status.json"
  local list_out="$ISSUE_ARTIFACTS_DIR/inbox-list.json"
  local next_out="$ISSUE_ARTIFACTS_DIR/inbox-next.json"
  local view_out="$ISSUE_ARTIFACTS_DIR/triage-view.json"
  require_issue_bin forge-cli || return 1

  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    inbox status \
    --item-type issue >"$status_out" 2>&1
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    inbox list \
    --item-type issue >"$list_out" 2>&1
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    inbox next \
    --item-type issue \
    --limit 3 >"$next_out" 2>&1
  forge-cli --provider github --repo graysurf/agent-runtime-kit \
    --dry-run --format json \
    issue view 123 >"$view_out" 2>&1

  grep -q '"schema_version":"cli.forge-cli.inbox.status.v1"' "$status_out"
  grep -q '"schema_version":"cli.forge-cli.inbox.list.v1"' "$list_out"
  grep -q '"schema_version":"cli.forge-cli.inbox.next.v1"' "$next_out"
  grep -q '"schema_version":"cli.forge-cli.issue.view.v1"' "$view_out"
}

run_issue_outcome_routing_probe() {
  local skill="$REPO_ROOT/core/skills/issue/issue-follow-up/SKILL.md.tera"

  grep -Fq 'forge-cli issue' "$skill"
  grep -Fq '### Program Mode' "$skill"
  ! grep -Fq 'Plan-Family Finding Mode' "$skill"
  rendered_contract_assert_skill issue issue-follow-up
  rendered_contract_assert_all_contain issue issue-follow-up '### Program Mode'
  rendered_contract_assert_all_omit issue issue-follow-up 'plan-issue-finding'
}

run_issue_program_mode_probe() {
  local store="$TMP_ROOT/issue-program-store"
  local dir="$ISSUE_ARTIFACTS_DIR/program"
  local forge=(forge-cli --provider local --store-root "$store" --repo local:program-demo --format json)
  local tracker child_a child_b n
  require_issue_bin forge-cli || return 1
  if [ "$ISSUE_TRACKER_MODE" = missing ]; then
    echo "runtime-smoke issue: forge-cli is newer than minimum_supported_tag but 'issue tracker' is unavailable" >&2
    return 1
  fi
  rm -rf "$store"
  mkdir -p "$dir"

  grep -Fq '### Program Mode' "$REPO_ROOT/core/skills/issue/issue-follow-up/SKILL.md.tera"
  grep -Fq '## Tracker Template' "$REPO_ROOT/core/skills/issue/issue-follow-up/references/program-mode.md"
  grep -Fq '## Child Template' "$REPO_ROOT/core/skills/issue/issue-follow-up/references/program-mode.md"
  rendered_contract_assert_all_contain issue issue-follow-up '### Program Mode'

  # Tracker placeholder first, so children can link to its number.
  printf 'Program tracker placeholder.\n' >"$dir/tracker-placeholder.md"
  "${forge[@]}" issue create --title "Track demo program" \
    --body-file "$dir/tracker-placeholder.md" \
    --label workflow::tracking >"$dir/tracker-create.json" 2>&1
  tracker="$(sed -n 's/.*"number":\([0-9][0-9]*\).*/\1/p' "$dir/tracker-create.json")"
  [ -n "$tracker" ] || return 1

  for n in A B; do
    printf '## Program\n\nProgram key `demo`, item **%s**. Tracker: #%s.\n' "$n" "$tracker" >"$dir/child-$n.md"
    "${forge[@]}" issue create --title "Demo child $n" \
      --body-file "$dir/child-$n.md" \
      --label workflow::follow-up >"$dir/child-$n-create.json" 2>&1
  done
  child_a="$(sed -n 's/.*"number":\([0-9][0-9]*\).*/\1/p' "$dir/child-A-create.json")"
  child_b="$(sed -n 's/.*"number":\([0-9][0-9]*\).*/\1/p' "$dir/child-B-create.json")"
  [ -n "$child_a" ] && [ -n "$child_b" ] || return 1

  # Fill the tracker with the real child numbers.
  printf '## Phase table\n\n- [ ] **A** Demo child A: #%s\n- [ ] **B** Demo child B: #%s · after A\n' "$child_a" "$child_b" >"$dir/tracker.md"
  if [ "$ISSUE_TRACKER_MODE" = tracker ]; then
    # forge-cli 1.31.2+ generates the dependency graph into the draft.
    "${forge[@]}" issue tracker graph --body-file "$dir/tracker.md" --write >"$dir/tracker-graph.json" 2>&1
    grep -Fq '  A --> B' "$dir/tracker.md"
  fi
  "${forge[@]}" issue edit "$tracker" --body-file "$dir/tracker.md" >"$dir/tracker-edit.json" 2>&1
  "${forge[@]}" issue view "$tracker" >"$dir/tracker-view.json" 2>&1
  "${forge[@]}" issue view "$child_a" >"$dir/child-a-view.json" 2>&1

  grep -q '"workflow::tracking"' "$dir/tracker-view.json"
  grep -Fq "#$child_a" "$dir/tracker-view.json"
  grep -Fq "#$child_b" "$dir/tracker-view.json"
  grep -q '"workflow::follow-up"' "$dir/child-a-view.json"
  grep -Fq "Tracker: #$tracker" "$dir/child-a-view.json"
  [ "$ISSUE_TRACKER_MODE" = tracker ] || return 0

  # Lint the filled tracker, tick a closed child with its PR and checkpoint,
  # then confirm every row agrees with its issue's state.
  "${forge[@]}" issue tracker lint "$tracker" | jq -e '.ok == true and .data.row_count == 2' >/dev/null
  "${forge[@]}" issue close "$child_a" >/dev/null
  if "${forge[@]}" issue tracker lint "$tracker" --check-state >"$dir/tracker-lint-stale.json" 2>&1; then
    return 1
  fi
  jq -e '.error.code == "tracker_findings" and
    (.data.findings | map(.code) == ["state-mismatch"])' "$dir/tracker-lint-stale.json" >/dev/null
  printf 'Child A closed; PR #7 merged.\n' >"$dir/tick-a.md"
  "${forge[@]}" issue tracker tick "$tracker" --item A --pr '#7' --comment-file "$dir/tick-a.md" |
    jq -e --arg row "- [x] **A** Demo child A: #$child_a (PR #7)" \
      '.ok == true and .data.row_after == $row and .data.comment_posted == true' >/dev/null
  # Read the stored tracker back: the ticked row and the checkpoint persisted.
  "${forge[@]}" issue view "$tracker" --with-comments |
    jq -e --arg row "- [x] **A** Demo child A: #$child_a (PR #7)" \
      '.ok == true and (.data.body | split("\n") | index($row) != null) and
        (.data.comments | any(.body | contains("Child A closed; PR #7 merged.")))' >/dev/null
  "${forge[@]}" issue tracker lint "$tracker" --check-state | jq -e '.ok == true and .data.findings == []' >/dev/null
}

failures=0
record_case "issue.issue-follow-up" "forge-cli issue create/view/comment dry-run probes passed" run_issue_follow_up_probe
record_case "issue.issue-triage" "forge-cli inbox issue triage dry-run probes passed" run_issue_triage_probe
record_case "issue.outcome-routing.contract" "generic issue follow-up routes program children without plan-family mode" run_issue_outcome_routing_probe
record_case "issue.program-mode.contract" "program mode opens a tracker placeholder, linked children, and a filled tracker on the local provider (tracker path: $ISSUE_TRACKER_MODE)" run_issue_program_mode_probe

exit "$failures"
