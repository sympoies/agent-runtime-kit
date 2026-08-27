#!/usr/bin/env bash
# Shape-only assertions on the tracking issue for the current run phase.
#
# Phases:
#   create    — issue exists; labels match; source/plan/state markers
#               present in body+comments at least once each.
#   execute   — issue still open; ≥2 distinct state-role comments.
#   deliver   — issue still open; ≥1 review-role comment posted; the
#               final state body still carries the full Task Ledger; and
#               the linked PR (resolved by head branch) is MERGED with a
#               real merge SHA. (Only used by fixtures that declare
#               FIXTURE_EXPECTED_ROLES_DELIVER.)
#   closeout  — issue closed; closeout-role comment present;
#               state label transitioned to FIXTURE_EXPECTED_FINAL_STATE.
#
# Output is PASS / FAIL lines per check, plus a final summary line. A
# non-zero exit means at least one check failed.

set -euo pipefail

DRIVER_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
. "${DRIVER_ROOT}/lib/common.sh"

phase="${1:?phase required: create | execute | closeout}"
state_load

# Profile-aware defaults so tracking fixtures (which omit these) keep
# working unchanged. The dispatch fixture sets them in its manifest.
FIXTURE_PROFILE="${FIXTURE_PROFILE:-tracking}"
FIXTURE_LANES="${FIXTURE_LANES:-}"
FIXTURE_LANE_BRANCHES="${FIXTURE_LANE_BRANCHES:-}"

require_cmd forge-cli
require_cmd jq

snap_dir="${STATE_DIR}/snapshots/${phase}"
mkdir -p "${snap_dir}"

log "looking up tracking issue by title…"
issue_number=$(tb_issue_find_by_title "${FIXTURE_TITLE}")

if [ -z "${issue_number}" ]; then
  echo "FAIL: no tracking issue found with title '${FIXTURE_TITLE}'"
  exit 1
fi

log "found issue #${issue_number}; snapshotting…"
tb_issue_snapshot "${issue_number}" "${snap_dir}/issue.json"

state_update "ISSUE_NUMBER=${issue_number}"

# ---- Collect facts ----------------------------------------------------

issue_state=$(jq -r '.state' "${snap_dir}/issue.json")
label_names=$(jq -r '.labels[].name' "${snap_dir}/issue.json" | sort -u)

# Extract role markers from body + all comment bodies. Markers look
# like `<!-- plan-issue-record:v2 role=<role> ... -->`.
{
  jq -r '.body' "${snap_dir}/issue.json"
  jq -r '.comments[].body' "${snap_dir}/issue.json"
} >"${snap_dir}/all-text.md"

roles_present=$(grep -oE 'plan-issue-record:v[0-9]+ role=[a-z][a-z0-9_-]*' \
  "${snap_dir}/all-text.md" |
  sed -E 's/.*role=//' |
  sort -u)

role_counts=$(grep -oE 'plan-issue-record:v[0-9]+ role=[a-z][a-z0-9_-]*' \
  "${snap_dir}/all-text.md" |
  sed -E 's/.*role=//' |
  sort | uniq -c | awk '{print $2"="$1}')

printf 'phase: %s\n' "${phase}"
printf 'issue: #%s (%s)\n' "${issue_number}" "${issue_state}"
printf 'labels:\n'
# Intentional word-splitting: each name on its own line.
# shellcheck disable=SC2086
printf '  %s\n' ${label_names}
printf 'role markers (unique):\n'
# shellcheck disable=SC2086
printf '  %s\n' ${roles_present}
printf 'role counts:\n'
# shellcheck disable=SC2086
printf '  %s\n' ${role_counts}
printf '\n'

# ---- Generic checks (every phase) -------------------------------------

fail_count=0
pass() { printf 'PASS: %s\n' "$*"; }
fail() {
  printf 'FAIL: %s\n' "$*"
  fail_count=$((fail_count + 1))
}

check_label_present() {
  local label="$1"
  if echo "${label_names}" | grep -qx "${label}"; then
    pass "label present: ${label}"
  else
    fail "label missing: ${label}"
  fi
}

check_role_present() {
  local role="$1"
  if echo "${roles_present}" | grep -qx "${role}"; then
    pass "role marker present: ${role}"
  else
    fail "role marker missing: ${role}"
  fi
}

check_role_min_count() {
  local role="$1" min="$2"
  local n
  n=$(echo "${role_counts}" | awk -F= -v r="${role}" '$1==r{print $2}')
  n="${n:-0}"
  if [ "${n}" -ge "${min}" ]; then
    pass "role count >= ${min}: ${role} (got ${n})"
  else
    fail "role count <${min}: ${role} (got ${n})"
  fi
}

# Concatenate every state-role comment body into a single blob so the
# rendered `## Task Ledger` row can be matched against expected task ids
# regardless of which checkpoint posted it.
state_bodies_blob() {
  local out="${snap_dir}/state-bodies.md"
  jq -r '
    .comments[]
    | select(.body | test("plan-issue-record:v[0-9]+ role=state"))
    | .body
  ' "${snap_dir}/issue.json" >"${out}"
  printf '%s\n' "${out}"
}

check_state_body_contains_ledger_row() {
  local task_id="$1"
  local bodies
  bodies="$(state_bodies_blob)"
  # Match a pipe-table row whose first cell is exactly the task id, in
  # any state lifecycle body. Status column is intentionally not pinned
  # (rows transition pending → in-progress → done).
  if grep -E -q "^\| ${task_id} \|" "${bodies}"; then
    pass "state body has ledger row: ${task_id}"
  else
    fail "state body missing ledger row: ${task_id}"
  fi
}

check_state_body_not_synthesized_fallback() {
  # Finding #9 / graysurf/plan-tracking-testbed#37 regression guard: when no
  # execution-state file is wired into the run state, the renderer emits a
  # single synthesized row whose task cell is literally `selected` — either
  # `| Task <id> | <status> | selected |` (older shape) or the bare-id
  # `| <id> | <status> | selected |` (current shape). Real per-task ledger
  # rows carry the task title in the third cell, never `selected`, so the
  # `| selected |` cell uniquely marks the fallback. Match both id shapes.
  local bodies
  bodies="$(state_bodies_blob)"
  if grep -E -q '^\| (Task )?[0-9.]+ \| [a-z-]+ \| selected \|' "${bodies}"; then
    fail "state body regressed to synthesized fallback ledger row (finding #9 / #37)"
  else
    pass "state body has no synthesized fallback ledger row"
  fi
}

# ---- Dashboard / state freshness guards (#54) -------------------------
#
# graysurf/plan-tracking-testbed#54: on a clean happy-path run the Final
# Dashboard still read `Target scope: in-progress`, `Current task: 1.1`,
# `Next action:` (blank) after both tasks were done, and every rendered
# Execution State body kept its pre-flight header verbatim
# (`Status: ready-to-start`, `Tracking issue: tbd`, `… snapshot: pending`).
# Root cause is in the nils-cli renderer/controller, not these skills: the
# dashboard is derived from the latest state payload, but `tracking
# checkpoint` fills target_scope with the phase word, never advances
# current/next_action, and the visible state header is echoed verbatim from
# the canonical execution-state.md (only its `## Task Ledger` rows are
# patched by `plan-tooling ledger-update`). These guards encode the
# correctness contract the renderer must satisfy; they are red until the CLI
# derives these human-visible fields from durable evidence.

# Lifecycle status/phase vocabulary that must never appear *as* a scope value.
DASHBOARD_STATUS_WORDS='pending in-progress in_progress complete completed blocked ready-for-close ready_for_close done validating implementing'

dashboard_field() {
  # Echo the trimmed value of a `- <Field>:` line from the issue body.
  local field="$1" body
  body=$(jq -r '.body' "${snap_dir}/issue.json")
  printf '%s\n' "${body}" |
    grep -iE "^[-*]?[[:space:]]*${field}:" |
    head -1 |
    sed -E "s/^[-*]?[[:space:]]*${field}:[[:space:]]*//I" |
    sed -E 's/[[:space:]]+$//'
}

check_dashboard_target_scope_fresh() {
  local val val_lc
  val="$(dashboard_field 'Target scope')"
  if [ -z "${val}" ]; then
    fail "dashboard: no 'Target scope' field found"
    return
  fi
  val_lc=$(printf '%s' "${val}" | tr '[:upper:]' '[:lower:]')
  # IFS-independent membership test against the space-padded word list.
  case " ${DASHBOARD_STATUS_WORDS} " in
    *" ${val_lc} "*)
      fail "dashboard 'Target scope' is lifecycle status word '${val}' (stale derivation; #54) — expected plan scope text"
      ;;
    *)
      pass "dashboard 'Target scope' is real scope text, not a status word"
      ;;
  esac
}

check_dashboard_current_task_fresh() {
  # At closeout every ledger row is terminal, so a bare task id in
  # 'Current task' means the field never advanced past the first selected
  # task. A closed plan's dashboard must read a terminal value.
  local val
  val="$(dashboard_field 'Current task')"
  if [ -z "${val}" ]; then
    fail "dashboard: no 'Current task' field found"
    return
  fi
  if printf '%s' "${val}" | grep -qE '^(Task[[:space:]]+)?[0-9]+(\.[0-9]+)*$'; then
    fail "dashboard 'Current task' still names task '${val}' on a closed plan (never advanced to a terminal value; #54)"
  else
    pass "dashboard 'Current task' reads a terminal value (${val})"
  fi
}

check_dashboard_next_action_present() {
  local val
  val="$(dashboard_field 'Next action')"
  if [ -z "${val}" ]; then
    fail "dashboard 'Next action' is empty on a closed plan (#54) — expected a terminal action (closeout / complete / none)"
  else
    pass "dashboard 'Next action' is populated (${val})"
  fi
}

check_state_body_not_frozen_preflight() {
  # Only the LATEST state comment must reflect live progress. The initial
  # `record open` state comment legitimately preserves the authored pre-flight
  # header — the CLI re-renders the header from the payload only on the
  # `tracking checkpoint` path (nils-cli v0.31.2 / sympoies/nils-cli#703), not
  # on `record open`/`record post`. Checking every state body false-positives
  # on that initial snapshot; the #54 bug was that the *latest* checkpoint
  # state stayed frozen, so only the latest body is the meaningful subject.
  local latest="${snap_dir}/latest-state-body.md"
  jq -r '
    [ .comments[]
      | select(.body | test("plan-issue-record:v[0-9]+ role=state"))
      | .body ] | last // ""
  ' "${snap_dir}/issue.json" >"${latest}"
  if grep -qiE 'Status:[[:space:]]*ready-to-start' "${latest}"; then
    fail "latest state body still says 'Status: ready-to-start' on an opened/closed issue (frozen header; #54)"
  elif grep -qiE 'Tracking issue:[[:space:]]*tbd' "${latest}"; then
    fail "latest state body still says 'Tracking issue: tbd' after the issue was opened (frozen header; #54)"
  elif grep -qiE 'snapshot:[[:space:]]*pending' "${latest}"; then
    fail "latest state body still marks a snapshot 'pending' after snapshots were posted (frozen header; #54)"
  else
    pass "latest state body header is not frozen at pre-flight placeholders"
  fi
}

check_linked_pr_merged() {
  # Finding #16 (deliver scope): a deliver run must produce a *merged* PR
  # with a real merge SHA. The lifecycle markers alone do not prove the PR
  # actually landed. Resolve the PR by its head branch (retained on the PR
  # record even after the branch is auto-deleted on merge); newest first.
  local pr_json pr_number pr_state merge_sha
  pr_json=$(tb_pr_resolve_by_head "${FIXTURE_BRANCH}")
  if [ -z "${pr_json}" ]; then
    fail "no PR found for head branch ${FIXTURE_BRANCH}"
    return
  fi
  pr_number=$(echo "${pr_json}" | jq -r '.number')
  pr_state=$(echo "${pr_json}" | jq -r '.state')
  merge_sha=$(echo "${pr_json}" | jq -r '.mergeCommit.oid // empty')
  if [ "${pr_state}" = "MERGED" ]; then
    pass "linked PR #${pr_number} merged"
  else
    fail "linked PR #${pr_number} state ${pr_state} (expected MERGED)"
  fi
  if [ -n "${merge_sha}" ]; then
    pass "linked PR #${pr_number} has merge SHA (${merge_sha:0:7})"
  else
    fail "linked PR #${pr_number} missing merge SHA"
  fi
}

# ---- Dispatch-profile checks ------------------------------------------

check_all_markers_profile() {
  # Every lifecycle marker must carry the expected profile. Guards against
  # the class of drift fixed by graysurf/plan-tracking-testbed#28, where a
  # dispatch checkpoint emitted `profile=tracking` markers.
  local want="$1" total wrong
  total=$(grep -oE 'plan-issue-record:v[0-9]+ role=[a-z][a-z0-9_-]* profile=[a-z]+' \
    "${snap_dir}/all-text.md" | wc -l | tr -d ' ')
  wrong=$(grep -oE 'plan-issue-record:v[0-9]+ role=[a-z][a-z0-9_-]* profile=[a-z]+' \
    "${snap_dir}/all-text.md" | grep -vc "profile=${want}" || true)
  if [ "${total}" -gt 0 ] && [ "${wrong}" -eq 0 ]; then
    pass "all ${total} lifecycle markers carry profile=${want}"
  else
    fail "expected every lifecycle marker profile=${want} (total=${total}, wrong=${wrong})"
  fi
}

check_lane_prs_merged() {
  # Dispatch close gate: every lane PR must be merged with a real merge
  # SHA. Resolve each by its lane head branch (FIXTURE_LANE_BRANCHES).
  local branch pr_json pr_number pr_state merge_sha
  for branch in ${FIXTURE_LANE_BRANCHES}; do
    pr_json=$(tb_pr_resolve_by_head "${branch}")
    if [ -z "${pr_json}" ]; then
      fail "no lane PR found for head branch ${branch}"
      continue
    fi
    pr_number=$(echo "${pr_json}" | jq -r '.number')
    pr_state=$(echo "${pr_json}" | jq -r '.state')
    merge_sha=$(echo "${pr_json}" | jq -r '.mergeCommit.oid // empty')
    if [ "${pr_state}" = "MERGED" ] && [ -n "${merge_sha}" ]; then
      pass "lane PR #${pr_number} (${branch}) merged (${merge_sha:0:7})"
    else
      fail "lane PR #${pr_number} (${branch}) state ${pr_state} sha '${merge_sha:-none}'"
    fi
  done
}

check_dispatch_dashboard_names_lanes() {
  # The dispatch dashboard's structured `Linked PRs` field must name every
  # lane PR so a reader sees the full fan-out at a glance. We assert against
  # the field itself, not the whole body — otherwise the check passes
  # incidentally when some other line (the approval / closeout summary)
  # happens to mention a PR number. Since `record close --linked-pr ... ` and
  # `tracking checkpoint --repair-dashboard` now populate the dashboard's
  # `prs[]` from the accumulative run-state linked PRs
  # (sympoies/nils-cli#642), the `Linked PRs` line lists every lane.
  local body linked_line branch pr_number
  body=$(jq -r '.body' "${snap_dir}/issue.json")
  # The dashboard renders a single "Linked PRs:" line listing every linked PR.
  linked_line=$(printf '%s\n' "${body}" |
    grep -iE '^[-*]?[[:space:]]*Linked PRs?:' | head -1)
  if [ -z "${linked_line}" ]; then
    fail "dispatch dashboard: no structured 'Linked PRs' field found"
    return
  fi
  for branch in ${FIXTURE_LANE_BRANCHES}; do
    pr_number=$(tb_pr_resolve_by_head "${branch}" | jq -r '.number // empty')
    if [ -z "${pr_number}" ]; then
      fail "dispatch dashboard: no PR resolved for lane branch ${branch}"
      continue
    fi
    if printf '%s' "${linked_line}" | grep -qE "#${pr_number}([^0-9]|\$)"; then
      pass "dispatch dashboard 'Linked PRs' names lane PR #${pr_number} (${branch})"
    else
      fail "dispatch dashboard 'Linked PRs' field omits lane PR #${pr_number} (${branch}); field: ${linked_line}"
    fi
  done
}

# ---- Per-phase checks -------------------------------------------------

case "${phase}" in
  create)
    # Issue must be OPEN.
    if [ "${issue_state}" = "OPEN" ]; then
      pass "issue state OPEN"
    else
      fail "issue state ${issue_state} (expected OPEN)"
    fi
    # All expected labels.
    # shellcheck disable=SC2153  # FIXTURE_LABELS is set by the sourced fixture manifest/state.
    IFS=',' read -ra labels_arr <<<"${FIXTURE_LABELS}"
    for l in "${labels_arr[@]+"${labels_arr[@]}"}"; do
      check_label_present "${l}"
    done
    # Source / plan / state roles, each at least once.
    for r in ${FIXTURE_EXPECTED_ROLES_CREATE}; do
      check_role_present "${r}"
    done
    # Dispatch: the open snapshots must already be marked profile=dispatch.
    if [ "${FIXTURE_PROFILE}" = "dispatch" ]; then
      check_all_markers_profile dispatch
    fi
    ;;
  execute)
    if [ "${issue_state}" = "OPEN" ]; then
      pass "issue state OPEN"
    else
      fail "issue state ${issue_state} (expected OPEN)"
    fi
    # State role should have grown to at least 2 (initial + per-task).
    check_role_min_count state 2
    # Original roles still present.
    for r in source plan; do
      check_role_present "${r}"
    done
    # Rendered state body must carry every expected per-task ledger row.
    for tid in ${FIXTURE_EXPECTED_LEDGER_TASK_IDS}; do
      check_state_body_contains_ledger_row "${tid}"
    done
    check_state_body_not_synthesized_fallback
    # Tracking: the rendered state header must already reflect the open issue,
    # not its pre-flight placeholders (#54).
    if [ "${FIXTURE_PROFILE}" != "dispatch" ]; then
      check_state_body_not_frozen_preflight
    fi
    # Dispatch multi-lane proof: the initial state plus one lane-scoped
    # state / session / validation checkpoint per lane.
    if [ "${FIXTURE_PROFILE}" = "dispatch" ]; then
      check_role_min_count state 3
      check_role_min_count session 2
      check_role_min_count validation 2
      check_all_markers_profile dispatch
    fi
    ;;
  deliver)
    if [ -z "${FIXTURE_EXPECTED_ROLES_DELIVER:-}" ]; then
      die "fixture ${FIXTURE_NAME} has no deliver phase (no FIXTURE_EXPECTED_ROLES_DELIVER)"
    fi
    if [ "${issue_state}" = "OPEN" ]; then
      pass "issue state OPEN"
    else
      fail "issue state ${issue_state} (expected OPEN — closeout has not run yet)"
    fi
    # Every role the fixture expects by deliver (data-driven so dispatch can
    # additionally require session / validation rollups).
    # shellcheck disable=SC2086  # intentional word-splitting of the role list.
    for r in ${FIXTURE_EXPECTED_ROLES_DELIVER}; do
      check_role_present "${r}"
    done
    # State role should have grown further (initial + per-task + final
    # state-complete after phase=ready_for_close), so require >= 2.
    check_role_min_count state 2
    # The final state body must still carry the per-task ledger.
    for tid in ${FIXTURE_EXPECTED_LEDGER_TASK_IDS}; do
      check_state_body_contains_ledger_row "${tid}"
    done
    check_state_body_not_synthesized_fallback
    # The delivery must have landed. Dispatch: every lane PR merged.
    # Tracking: the single linked PR merged. The dispatch run-state now
    # accumulates every lane's linked PR (sympoies/nils-cli#642), so once the
    # dashboard is repaired the `Linked PRs` field names every lane — the
    # authoritative dashboard-naming assertion still runs at closeout against
    # the Final Dashboard built by `record close --linked-pr ... --linked-pr ...`.
    if [ "${FIXTURE_PROFILE}" = "dispatch" ]; then
      check_lane_prs_merged
      check_all_markers_profile dispatch
    else
      check_linked_pr_merged
    fi
    ;;
  closeout)
    if [ "${issue_state}" = "CLOSED" ]; then
      pass "issue state CLOSED"
    else
      fail "issue state ${issue_state} (expected CLOSED)"
    fi
    check_role_present closeout
    check_label_present "${FIXTURE_EXPECTED_FINAL_STATE}"
    # Every role the fixture expects at closeout must be present, including
    # `review`: the lightweight happy-path records its completion review at
    # closeout (the plan-tracking-issue-closeout preflight posts it when
    # close-ready reports `review-missing`), and the deliver flow records the
    # PR review upstream — so both carry `review` by closeout.
    # shellcheck disable=SC2086  # intentional word-splitting of the role list.
    for r in ${FIXTURE_EXPECTED_ROLES_CLOSEOUT}; do
      check_role_present "${r}"
    done
    # Deliver fixtures additionally require the linked PR(s) to remain merged.
    if [ -n "${FIXTURE_EXPECTED_ROLES_DELIVER:-}" ]; then
      if [ "${FIXTURE_PROFILE}" = "dispatch" ]; then
        check_lane_prs_merged
      else
        check_linked_pr_merged
      fi
    fi
    # Dispatch markers must stay profile=dispatch through closeout, and the
    # Final Dashboard must name every lane PR.
    if [ "${FIXTURE_PROFILE}" = "dispatch" ]; then
      check_all_markers_profile dispatch
      check_dispatch_dashboard_names_lanes
    fi
    # Final state body must also reflect the full per-task ledger.
    for tid in ${FIXTURE_EXPECTED_LEDGER_TASK_IDS}; do
      check_state_body_contains_ledger_row "${tid}"
    done
    check_state_body_not_synthesized_fallback
    # Tracking Final Dashboard freshness (#54): on a closed plan the
    # derived dashboard fields and the rendered state header must reflect
    # completion, not the pre-flight authoring.
    if [ "${FIXTURE_PROFILE}" != "dispatch" ]; then
      check_dashboard_target_scope_fresh
      check_dashboard_current_task_fresh
      check_dashboard_next_action_present
      check_state_body_not_frozen_preflight
    fi
    ;;
  *)
    die "unknown phase: ${phase}"
    ;;
esac

printf '\n'
if [ "${fail_count}" -eq 0 ]; then
  printf 'SUMMARY: %s phase PASS\n' "${phase}"
  state_update "PHASE=${phase}"
  exit 0
else
  printf 'SUMMARY: %s phase FAIL (%d check(s) failed)\n' "${phase}" "${fail_count}"
  exit 1
fi
