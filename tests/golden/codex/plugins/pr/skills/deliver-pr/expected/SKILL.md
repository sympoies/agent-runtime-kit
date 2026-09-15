---
name: deliver-pr
description: >
  Deliver GitHub pull requests or GitLab merge requests end to end through the released nils-cli `forge-cli pr deliver` macro.
---

# Deliver PR / MR

## Contract

Prereqs:

- `agent-runtime`, `forge-cli >=1.28.30`, `git-cli >=1.25.13`,
  `plan-issue >=1.1.0`, and `review-specialists >=1.27.27` are installed from the
  released nils-cli package and available on `PATH`. The `forge-cli` floor is
  1.28.30 because this workflow delegates its review-loop compare-and-swap and
  its pending-review recovery to `--auto-state`, `--preflight`, and
  `--recover-pending`; an older host rejects all three at parse time.
- `pr merge` fails closed with `review_state_conflict` ("bounded review delivery
  requires an explicit genesis ledger observation") unless the review loop was
  recorded, so the Workflow below cannot merge without it. This workflow relies
  on the faithful non-mutating `review-loop observe --preflight` sweep, which
  runs the same checks `--dry-run` reports and refuses to append when any fail.
- Shared provider, branch, body, and label rules in
  `references/pr-lifecycle.md` are satisfied.
- The working tree contains only the intended delivery changes.
- Local validation and review findings have been resolved before merge.
- Implementation changes have been committed through `semantic-commit`; commit
  mutation is an internal delivery prerequisite, not a user-selected workflow.
- For every lifecycle mode except close-unmerged, if executable
  `.agents/scripts/pre-pr.sh` exists, run it through the repository dispatcher
  before the first provider mutation. Abandon-close is a remote terminal route
  and must not depend on unrelated local pre-PR validation.

Inputs:

- Provider: `github` or `gitlab` (let `forge-cli` detect it from the remote, or
  pass `--provider` explicitly).
- Delivery kind: `feature`, `bug`, `chore`, `docs`, `ci`, or `refactor`;
  it must match the branch prefix.
- PR/MR title and body section files for `agent-runtime pr-body render`.
- Optional head branch, base branch, merge method, reviewers, and timeout.
- Requested lifecycle outcome: create only, deliver to readiness, repair review
  findings, merge, or close an unmerged record.
- Required labels selected from the shared taxonomy.
- Optional `--no-merge` when the workflow should stop after checks.
- Optional `--no-closeout` to stop after delivery readiness checks and before
  linked issue closeout.
- Mandatory generic code review in pre-merge context. The caller may prefer
  quick or full review, but scope and risk own the final profile selection.
- On GitHub, `REVIEW_LEDGER_FINDINGS`, the delivery-mode `findings.merged.json` produced
  by `review-specialists bundle --mode delivery` for the reviewed head. A clean
  review still supplies the generated envelope with `data.findings: []` so the
  required genesis observation is deterministic.
- On GitHub, `REVIEW_LEDGER_DISPOSITIONS`, a bare observation array for every finding
  repaired or dispositioned after genesis. Omit it only when the genesis
  envelope is empty; otherwise every row carries the same
  `lifecycle_fingerprint` and a released disposition.
- Local terminal identity captured before merge: checkout root, branch,
  delivered head SHA, base ref, and whether the checkout is primary or a
  managed linked worktree. When an outer L2/L3 or requested post-merge workflow
  still owns terminal duties, pass this identity outward instead of cleaning
  early.
- If the body references a linked tracking or dispatch issue, use non-closing
  references such as `Refs #<issue>`; provider auto-close keywords are refused.
  Carry the references through `pr-body render --issues-file` — rendered as
  `## Issues` after `## Summary` for every kind (`bug` keeps its required
  `## Issues Found` section) — instead of hand-placing them in the summary.
- If the body references a linked tracking or dispatch issue, lifecycle
  readiness is also a pre-merge gate: source, plan, complete state, latest
  `role=session`, validation, and review evidence must be present before merge.

Outputs:

- A draft or ready GitHub PR or GitLab MR opened from the current branch.
- Required checks / pipeline state waited through `forge-cli pr wait-checks`.
- A generic pre-merge review result completed before merge: either an eligible
  quick `pass` for the current head, or a full review with at least `testing`
  and `maintainability`.
- Compact quick-finding or specialist reviews posted to the PR/MR as each
  blocking reviewer result returns
  (native `COMMENT` review events on GitHub via `--submit-review`, outcome notes
  on GitLab). These use portable `--decision comments-only` and `--lens`
  semantics and report findings and evidence only; the active environment owns
  any optional identity mapping. On GitHub, actionable findings that require owner
  changes are also passed through `--thread-file` so the owning agent can fix and
  resolve them; no-finding reports omit `--thread-file` and stay summary-only.
  If a linked tracking or dispatch issue is present, mirror the compact review
  URL breadcrumb to that issue.
- Every provider-visible specialist body is the canonical
  `review-specialists bundle --profile provider-review` artifact. The complete
  report uses the marker and five-column table; actionable GitHub threads come
  from the same bundle. `pr-comment` is only an alias for this profile, never a
  second bullet renderer. That bundle call must bind `--mode delivery`,
  `--reviewable`, `--lens`, `--lens-verdict`, `--scope`, and
  `--evidence-reviewed`; from nils-cli v1.28.0 an absent or placeholder value
  for any of those but `--lens-verdict` fails the render with
  `provider-review-metadata-required`, and `--evidence-reviewed` must be a
  portable identifier rather than an absolute local path.
- A delivery review outcome posted to the PR/MR before merge through
  `forge-cli pr review`; combined owner outcomes use the final `--decision`
  plus repeated selected lenses and own final finding dispositions. GitHub uses
  a native `APPROVE` / `REQUEST_CHANGES` review only when an environment-owned
  router guarantees an identity independent from the PR author; other paths use
  the outcome-note form.
- On GitHub, current-head native review summaries inspected through
  `forge-cli pr reviews` and semantically dispositioned before the final owner
  outcome. Stale-head reviews remain informational.
- On GitHub, a durable `forge-cli.review-loop.v1` chain recording each reviewed head and
  its finding dispositions, appended through `forge-cli pr review-loop observe`
  before each repair is pushed.
- Mechanical convergence, review-ledger, unresolved-thread, unchecked-task, and
  provider-head
  gates executed by `forge-cli pr merge`. A typed gate failure routes to the
  matching read/disposition/retry path instead of an agent-authored polling
  loop.
- A merged PR/MR through `forge-cli pr merge`, unless `--no-merge` is supplied.
- When a linked issue closeout runs, `plan-issue record close` posts closeout
  evidence, repairs the dashboard, verifies linked records, and closes the
  issue.
- When this is the outermost successful workflow, a terminal local cleanup
  result: the clean primary checkout is restored to base, or the safe merged
  managed worktree is removed through `git-cli worktree remove`; retained
  unsafe state includes its reason and recovery command.

Failure modes:

- Provider auth fails, the branch has no published upstream (publish it with
  `git-cli push`), or the base branch is not the intended target.
- Required checks / pipeline checks fail, time out, remain pending, or are
  missing without an explicit no-checks decision.
- Selected labels fail catalog validation or the provider rejects label
  application.
- Mandatory quick or full pre-merge review findings are unresolved or
  undispositioned.
- Current-head native review summaries are unread or contain actionable
  feedback that has not been repaired, accepted with rationale, or moved to a
  follow-up.
- A GitHub native review submission with `--recover-pending` refuses to recover.
  `github_pending_review_exists` means no single viewer-owned deletable node
  could be named; a `pending_review_*` code names the guard that rejected the
  one candidate, and `pending_review_body_mismatch` specifically means the
  pending review is not the attempt this submission would have replaced. Stop
  and read it rather than deleting review state by hand or falling back to an
  outcome note.
- `forge-cli pr merge` returns `review_changes_requested`,
  `review_convergence_activity_changed`, `review_convergence_head_changed`,
  `review_convergence_timeout`, `review_snapshot_incomplete`,
  `unresolved_review_threads`, `unchecked_task_items`, or
  `review_state_conflict`. A `review_state_conflict` at merge means the
  review-loop ledger has no observation for this head; it cannot be backfilled
  at an earlier head, so record what is true at the current head and treat the
  lost rounds as a reporting gap rather than reconstructing them. Read and
  disposition
  the matching provider evidence before retrying; do not replace the CLI gate
  with a custom timing loop.
- Unchecked `- [ ]` task-list items remain in the PR/MR description at merge
  time. The description is the delivery contract; `forge-cli pr merge` fails
  closed with `unchecked_task_items`, and the task-list sweep is how the
  workflow dispositions them before that gate trips.
- Delivery review outcome posting fails.
- `local_path_present`: rewrite useful evidence paths in provider-visible PR
  bodies, delivery outcome comments, or linked issue closeout records to
  `$HOME/...` and omit remote-useless local artifact paths before retrying.
- A PR/MR body uses a provider auto-close keyword against a linked
  plan-tracking or dispatch issue.
- A linked tracking or dispatch issue is missing lifecycle readiness before
  merge. Route to `deliver-plan-tracking-issue` or `deliver-dispatch-plan`
  instead of merging and backfilling after the fact.
- `plan-issue record close` rejects linked issue closeout.
- Terminal cleanup cannot prove a clean checkout, provider-confirmed merge of
  the captured delivered head, or safe ownership. Retain the worktree and
  branch, report the failed proof, and do not force removal.

## Lifecycle Mode Selection

The user requests the PR/MR outcome, not a lifecycle helper.

- **Create only** — render and validate the body, create the draft provider
  record with `forge-cli pr create`, return its URL, and stop before checks,
  review, merge, or linked-issue closeout.
- **Deliver** — create or adopt the record, wait for checks, run the mandatory
  risk-selected review gate, inspect and disposition native summaries, then
  merge through the CLI-owned convergence/thread/task gates unless the user
  requested a readiness stop.
- **Review repair** — adopt the existing record, classify unresolved review
  threads, make authorized fixes, rerun validation, and recheck affected review
  modes as closed-set closure before returning to the delivery gates.
- **Merge** — adopt an existing ready record, inspect native review evidence,
  and satisfy every remaining semantic, linked-lifecycle, and provider gate
  before `forge-cli pr merge`.
- **Close unmerged** — only when the user explicitly abandons the record; read
  current state, record the reason, and call `forge-cli pr close` without
  pretending delivery succeeded.

Dispatch lane PR creation remains an internal L3 dispatch role because its
plan-branch target and lane checkpoint authority belong to that outcome.

## Review Profile Selection

Pre-merge remains mandatory. Select the smallest safe profile after checks and
scope detection; a user request such as "PR quick merge" expresses a preference,
not permission to bypass escalation.

- **Quick merge** — available for an L0 or L1 PR only when the diff is bounded,
  required validation and checks pass, scope suggests or forces no risk
  specialist, no unresolved current-head review state exists, and `reviewer-quick` has
  enough confidence to inspect the complete change. A clean `pass` is terminal
  review evidence for the current head; post one final outcome with `--lens
  quick`, then continue through the ordinary merge gates.
- **Quick findings** — post concrete findings before repair, block merge, rerun
  affected validation, and use quick follow-up only while the scope stays
  bounded.
- **Full review** — mandatory for L2 or L3 delivery, any specialist trigger,
  existing unresolved review state, insufficient quick-review confidence, or a
  quick `escalate` verdict. It routes to the full pre-merge profile without changing the work tier
  or requiring another user decision.

The quick profile changes review depth only. It never skips checks, final
provider review-state inspection, convergence, unresolved-thread, unchecked-task,
expected-head, linked-lifecycle, or terminal cleanup gates.

## Review-Loop Ledger

On GitHub, `forge-cli pr merge` fails closed unless the repair loop was recorded
in the durable `forge-cli.review-loop.v1` chain. GitLab has neither the ledger
surface nor this merge gate in v1; it keeps the outcome-note flow and passes
`--review-convergence=false` without calling `pr review-loop`. Two GitHub rules
interact, and getting the order wrong is unrecoverable:

- an observation can only be appended at the **current provider head**, so
  history cannot be backfilled — a past head is rejected with `the provider
  pull-request head differs from --expected-head`;
- a `fixed` disposition requires a **repaired head**, so re-declaring a finding
  fixed at the head where it was first recorded is rejected with `a fixed
  disposition requires a repaired head`.

Together they force the observation to happen *before* the repair is pushed.
The no-finding path still appends genesis: merge requires an observation for
the current head even when the generated delivery envelope contains no rows.

For a GitHub finding-bearing round:

1. review returns findings;
2. `forge-cli pr review-loop observe --expected-head <reviewed head>`, with the
   findings recorded as `open`;
3. repair, then publish the repair with `git-cli push --format json`;
4. `forge-cli pr review-loop observe --expected-head <repaired head>`, with the
   repaired findings recorded as `fixed`;
5. merge at that same repaired head.

Doing every repair first and then trying to record the history cannot be
repaired: the pre-repair head is gone, so the round count and the
`no_progress_rounds` budget cannot be reconstructed. The real find→fix history
then survives only in PR comments, not in the ledger.

`--findings-file` accepts two shapes, and they are not interchangeable. Produce
the genesis envelope through `review-specialists bundle --mode delivery`; do
not hand-author a lookalike empty payload for a clean quick pass:

| Shape | When | Requirements |
| --- | --- | --- |
| `review-specialists merge --mode delivery` envelope | the genesis observation | each row needs `evidence`, `recommendation`, and a `lifecycle_fingerprint` of the form `<category>:<component>:<invariant>` whose category segment equals the row's `category`; the schema **rejects** `disposition` as an unknown field |
| bare observation array | any round that carries dispositions | each row needs `lifecycle_fingerprint` and accepts `disposition` (`open`, `fixed`, `accepted`, `preference`, `follow-up`) |

A finding that reappears is submitted as `open`, not `reopened`. The state
machine decides whether that transition is a reopen and may stop with the typed
`review_finding_reopened` gate; `reopened` is not an input disposition.

Every round runs one `observe` carrying `--preflight`, which performs the same
reads and validation `--dry-run` reports and aborts before writing if any rule
fails — naming every failing rule, not the first. A live `observe` appends
durable, provider-visible state on success, so it is never a probe.

The two rounds differ in how they name the chain tip, and the difference is not
stylistic:

- **Genesis** uses `--auto-state`. There is no earlier digest to assert, so
  letting the CLI read the tip removes an `inspect` call and a `jq` extraction
  without giving anything up.
- **The closing observation** keeps `--expected-state`, set to the digest the
  genesis append returned. That digest is a claim about a tip this workflow
  already saw, and it is the only thing that catches a resumed shell reusing
  genesis state or a second actor advancing the chain in between. `--auto-state`
  re-reads and would accept both silently, so do not use it here.

## Body Format

Use `agent-runtime pr-body render` as the canonical formatter. The shared
PR/MR lifecycle reference owns minimum headings, label selection, and
non-closing issue references.

## Entrypoint

Render the body with `agent-runtime` before calling the delivery macro:

```bash
agent-runtime pr-body render \
  --kind feature \
  --summary-file "$SUMMARY_FILE" \
  --changes-file "$CHANGES_FILE" \
  --test-first-file "$TEST_FIRST_FILE" \
  --test-plan-file "$TEST_PLAN_FILE" \
  --risk-file "$RISK_FILE" \
  --out "$PR_BODY"
```

Add `--issues-file "$ISSUES_FILE"` when the PR references a linked issue: it is
required for `--kind bug` and optional for every other kind, rendering the
non-closing references as `## Issues`. Kind-specific files passed with a
non-owning kind are rejected (`--changes-file` is feature-only;
`--problem-file`, `--reproduction-file`, and `--fix-approach-file` are
bug-only) instead of being silently dropped.

Use the released provider CLI directly. `forge-cli` detects the provider from
the remote; pass `--provider "$PROVIDER"` to pin it (`github` or `gitlab`):

```bash
forge-cli pr deliver \
  --provider "$PROVIDER" \
  --kind feature \
  --title "$PR_TITLE" \
  --body-file "$PR_BODY" \
  --base main \
  --method squash \
  --label type::feature \
  --label area::runtime \
  --label size::m \
  --label-catalog manifests/forge-labels.yaml \
  --strict-labels \
  --test-first-evidence "$EVIDENCE_DIR" \
  --no-merge
```

When the test-first gate is enabled — `[test_first].require = true` in a repo
`.forge-cli.toml` or the user-global
`${XDG_CONFIG_HOME:-~/.config}/forge-cli/config.toml` — a `--kind feature` /
`bug` deliver (the create, adopt, and `--dry-run` preflight steps) also requires
`--test-first-evidence "$EVIDENCE_DIR"`, pointing at the `verify`-clean directory
the policy-owned `test-first-evidence` CLI flow produces. Omit it for the exempt kinds (`docs` /
`chore` / `ci` / `refactor`); without it delivery fails closed with
`test_first_evidence_required`.

Run the generic code-review outcome in pre-merge context before merge. Start
without forced lenses so scope can admit quick review; when quick is ineligible
or returns `escalate`, rerun scope with the full profile's minimum lenses:

```bash
REVIEWED_PR="$(
  forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" \
    --format json pr view "$PR_NUMBER"
)"
REVIEWED_HEAD="$(
  printf '%s\n' "$REVIEWED_PR" |
    jq -er 'select(.ok == true) | .data.head_sha'
)" || exit $?
readonly REVIEWED_HEAD

review-specialists scope \
  --base "$BASE_REF" \
  --format json

# Full-profile route only: L2/L3, a risk trigger, unresolved review state, or
# quick-review escalation.
review-specialists scope \
  --base "$BASE_REF" \
  --testing \
  --maintainability \
  --format json

# After the selected quick or specialist review has been merged with
# `review-specialists bundle --mode delivery`, bind its generated envelope.
# GitHub-only review-loop ledger: GitLab v1 has no ledger surface or merge gate.
if [ "$PROVIDER" = github ]; then
: "${REVIEW_LEDGER_FINDINGS:?set to delivery-mode findings.merged.json}"
# Review-loop genesis: before any repair, with the CLI-owned preflight sweep.
# `--preflight` runs the full non-mutating sweep and fails with every rejecting
# rule named, so no separate `--dry-run` call is needed. `--auto-state` reads the
# tip: genesis holds no digest from an earlier round, so there is no claim for
# `--expected-state` to make here. The closing observation is the opposite case.
REVIEW_LEDGER_GENESIS="$(
  forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json \
    pr review-loop observe "$PR_NUMBER" \
    --expected-head "$REVIEWED_HEAD" \
    --auto-state \
    --preflight \
    --findings-file "$REVIEW_LEDGER_FINDINGS"
)" || exit $?
REVIEW_LEDGER_STATE_TIP="$(
  printf '%s\n' "$REVIEW_LEDGER_GENESIS" |
    jq -er 'select(.ok == true) | .data.state_tip_digest'
)" || exit $?
REVIEW_LEDGER_OPEN_COUNT="$(
  printf '%s\n' "$REVIEW_LEDGER_GENESIS" |
    jq -er '[.data.state.findings[] | select(.status == "open")] | length'
)" || exit $?
fi

# On GitHub, stop here when findings are open. Repair them, publish with
# `git-cli push --format json`, rerun validation and affected review, then
# produce REVIEW_LEDGER_DISPOSITIONS as a bare array.
# Read native review bodies after specialist posting and repair. Current-head
# summaries are semantic evidence; stale-head summaries are informational.
PRE_SUBMIT_PR="$(
  forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" \
    --format json pr view "$PR_NUMBER"
)"
EXPECTED_REVIEW_HEAD="$(
  printf '%s\n' "$PRE_SUBMIT_PR" |
    jq -er 'select(.ok == true) | .data.head_sha'
)" || exit $?
readonly EXPECTED_REVIEW_HEAD

# Review-loop closing observation: after repair/push and before merge.
if [ "$PROVIDER" = github ] && [ "${REVIEW_LEDGER_OPEN_COUNT:-0}" -gt 0 ]; then
  : "${REVIEW_LEDGER_DISPOSITIONS:?set repaired/accepted finding dispositions}"
  # Keep `--expected-state` here and do NOT use `--auto-state`. This digest came
  # back from the genesis append, so it is a claim about a tip this workflow
  # already saw, and it is the only thing that catches a resumed shell reusing
  # genesis state. `--auto-state` re-reads and would silently accept a chain
  # someone else advanced in between.
  REVIEW_LEDGER_CLOSE="$(
    forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json \
      pr review-loop observe "$PR_NUMBER" \
      --expected-head "$EXPECTED_REVIEW_HEAD" \
      --expected-state "$REVIEW_LEDGER_STATE_TIP" \
      --preflight \
      --findings-file "$REVIEW_LEDGER_DISPOSITIONS"
  )" || exit $?
  REVIEW_LEDGER_STATE_TIP="$(
    printf '%s\n' "$REVIEW_LEDGER_CLOSE" |
      jq -er 'select(.ok == true) | .data.state_tip_digest'
  )" || exit $?
  printf '%s\n' "$REVIEW_LEDGER_CLOSE" |
    jq -e '.ok == true and ([.data.state.findings[].status] | index("open") | not)' \
      >/dev/null
fi
if [ "$PROVIDER" = github ]; then
  PRE_SUBMIT_REVIEWS="$(
    forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" \
      --format json pr reviews "$PR_NUMBER"
  )"
  printf '%s\n' "$PRE_SUBMIT_REVIEWS"
  printf '%s\n' "$PRE_SUBMIT_REVIEWS" |
    jq -e --arg head "$EXPECTED_REVIEW_HEAD" \
      '.ok == true and .data.head_sha == $head' >/dev/null
fi
# Reuse the complete selected lens set for the final provider outcome. Quick
# uses one final semantic lens; full starts with testing + maintainability and
# appends every risk lens selected by review-specialists scope.
case "$REVIEW_PROFILE" in
  quick) SELECTED_REVIEW_LENSES=(quick) ;;
  full) SELECTED_REVIEW_LENSES=(testing maintainability) ;;
  *) echo "unsupported review profile: $REVIEW_PROFILE" >&2; exit 64 ;;
esac
REVIEW_LENS_ARGS=()
for selected_lens in "${SELECTED_REVIEW_LENSES[@]}"; do
  REVIEW_LENS_ARGS+=(--lens "$selected_lens")
done
# Resolve REVIEW_PUBLICATION_MODE with the tri-state guard in
# REVIEW_OUTCOME_POSTING_CONTRACT.md before entering this direct branch.
# Governed native outcomes use forge-review-publish and do not enter it.
NATIVE_REVIEW_DECISION="$REVIEW_DECISION"
PERSONAL_ESCAPE_SUBMIT_REVIEW=()
case "${REVIEW_PUBLICATION_MODE:-}" in
  portable) ;;
  personal-escape)
    : "${REVIEW_PERSONAL_ESCAPE_REASON:?personal escape needs a reason}"
    [ "${REVIEW_PUBLISHER_FAILURE_STATE:-}" = no-native-mutation ] || exit 69
    [ "$(git rev-parse HEAD)" = "$EXPECTED_REVIEW_HEAD" ] || exit 65
    NATIVE_REVIEW_DECISION=comments-only
    # `--recover-pending` clears one exact abandoned viewer-owned pending review
    # from an earlier attempt of this same submission. The CLI owns the guard:
    # exactly one viewer-authored deletable node, still bound to this head, with
    # no inline drafts and a byte-identical body, deleted under its own lease and
    # confirmed gone. Do not re-implement that guard here — a defect in it
    # deletes somebody else's review, and it is not undoable.
    PERSONAL_ESCAPE_SUBMIT_REVIEW=(
      --submit-review
      --expected-head "$EXPECTED_REVIEW_HEAD"
      --recover-pending
    )
    ;;
  governed)
    echo "governed final outcomes use forge-review-publish" >&2
    exit 64
    ;;
  *) echo "review publication mode was not resolved" >&2; exit 64 ;;
esac
# Observed convergence is GitHub-only in v1. Preserve GitLab delivery even when
# the user's global forge-cli config enables it.
REVIEW_CONVERGENCE_ARGS=()
[ "$PROVIDER" = gitlab ] && REVIEW_CONVERGENCE_ARGS=(--review-convergence=false)

# Capture the outcome bytes once. Initial submission, guarded recovery, and
# the single retry must all use this immutable value rather than rereading a
# mutable file path. Preserve capture failures before freezing the value, and
# use `--option=value` below so hyphen-leading Markdown remains one argv value.
EXPECTED_REVIEW_BODY="$(cat "$DELIVERY_REVIEW_OUTCOME")" || exit $?
readonly EXPECTED_REVIEW_BODY
if [ "$REVIEW_PUBLICATION_MODE" = personal-escape ]; then
  printf '%s\n' "$EXPECTED_REVIEW_BODY" |
    grep -Fq -- "$REVIEW_PERSONAL_ESCAPE_REASON" &&
    printf '%s\n' "$EXPECTED_REVIEW_BODY" |
      grep -Fq -- 'independent review identity: unavailable' || {
        echo "personal escape outcome lacks required provenance" >&2
        exit 65
      }
fi
NATIVE_REVIEW_IDENTITY=()
if [ "$REVIEW_PUBLICATION_MODE" = personal-escape ]; then
  NATIVE_REVIEW_IDENTITY=(env FORGE_AS=user)
fi
NATIVE_REVIEW_CMD=(
  "${NATIVE_REVIEW_IDENTITY[@]}"
  forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json
  pr review "$PR_NUMBER"
  --decision "$NATIVE_REVIEW_DECISION"
  "${PERSONAL_ESCAPE_SUBMIT_REVIEW[@]}"
  --comment="$EXPECTED_REVIEW_BODY"
  "${REVIEW_LENS_ARGS[@]}"
)
# `--recover-pending` above makes `github_pending_review_exists` recoverable
# inside the command, so there is no conflict branch, no jq node selection, and
# no retry to sequence here. A refusal names the guard that rejected it
# (`pending_review_body_mismatch` means the pending review is not the one this
# submission would have replaced) and must be read, not worked around.
NATIVE_REVIEW_JSON="$("${NATIVE_REVIEW_CMD[@]}")" || exit $?
printf '%s\n' "$NATIVE_REVIEW_JSON"
if [ "$REVIEW_PUBLICATION_MODE" = personal-escape ]; then
  PERSONAL_ESCAPE_PR="$(
    forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json \
      pr view "$PR_NUMBER"
  )" || exit $?
  PERSONAL_ESCAPE_HEAD="$(
    printf '%s\n' "$PERSONAL_ESCAPE_PR" |
      jq -er 'select(.ok == true) | .data.head_sha'
  )" || exit $?
  [ "$PERSONAL_ESCAPE_HEAD" = "$EXPECTED_REVIEW_HEAD" ] || {
    echo "pull request head changed before personal escape outcome" >&2
    exit 65
  }
  PERSONAL_ESCAPE_OUTCOME_JSON="$(
    env FORGE_AS=user forge-cli \
      --provider "$PROVIDER" --repo "$OWNER_REPO" --format json \
      pr review "$PR_NUMBER" \
      --decision "$REVIEW_DECISION" \
      --comment="$EXPECTED_REVIEW_BODY" \
      "${REVIEW_LENS_ARGS[@]}"
  )" || exit $?
  printf '%s\n' "$PERSONAL_ESCAPE_OUTCOME_JSON"
fi
# Keep merge on the same provider head that was inspected and reviewed.
forge-cli --provider "$PROVIDER" pr merge "$PR_NUMBER" --method squash \
  --expected-head "$EXPECTED_REVIEW_HEAD" \
  "${REVIEW_CONVERGENCE_ARGS[@]}"
```

The command binds the native review to the inspected head with `--expected-head`
and carries `--recover-pending`, so an abandoned draft left by an earlier
attempt of this same submission is cleared by the command rather than here. The
conflict is raised by a preflight, before any provider mutation, so there is
nothing half-applied to reconcile and no retry to sequence.

Do not reconstruct that recovery in this workflow. The guard is around an
unundoable delete, and the command owns it end to end: exactly one
viewer-authored pending review the viewer may delete, re-proved under a
cross-process lease to be still bound to the expected head, free of inline draft
comments, and byte-identical to the body being submitted, then confirmed gone by
read-back. A refusal names the guard that rejected it and is the answer, not an
obstacle — recover by reading it, never by selecting a node by hand.

Map the final delivery review outcome to `approve` when delivery may merge and
`request-changes` when the review blocks. Use `comments-only` only for
specialist review comments or other non-decisional notes, not for the final
combined delivery-owner outcome. On GitHub, `--submit-review` makes this a native
pull request review event (`approve`→`APPROVE`, `request-changes`→`REQUEST_CHANGES`)
authored by the adapter-selected independent identity. Without the capability,
GitHub uses the same outcome-note path as GitLab, records the semantic decision,
and does not mutate native approval state.

For identity and issue mirroring: resolve the tri-state publication mode in
`REVIEW_OUTCOME_POSTING_CONTRACT.md` before any write. Only `portable` mode
posts a compact review after each lens and focused rerun. `governed` mode waits
for the selected wave and publishes one combined owner-App report;
`personal-escape` requires explicit authorization and publishes one combined
exact-head report followed by a non-native outcome note. Pass only the portable
`--provider`, `--decision`, and `--lens` semantics; do not set private
identity-profile environment variables in this public workflow. When the PR/MR is linked to a tracking or
dispatch issue and the issue number is available, add
`--issue "$ISSUE" --mirror-issue` so the issue activity shows review progress
without duplicating full outcome bodies.
When the specialist report has actionable GitHub findings, include
`--thread-file "$REVIEW_THREAD_FILE"` on the first specialist review post that
surfaces those findings. Omit `--thread-file` for clean reviews, informational
notes, follow-up pass summaries, and the final combined approval outcome.

Before the final owner outcome, read native provider reviews once:

```bash
if [ "$PROVIDER" = github ]; then
  forge-cli --provider "$PROVIDER" --format json pr reviews "$PR_NUMBER"
fi
```

On GitHub, treat `data.current_head_reviews[].summary` as evidence, never as a
machine verdict. Apply the closed-set admission rule: repair admitted feedback,
accept it with rationale, or move it to a follow-up; a non-admitted critical
concern requires an explicit handoff rather than another repair round. Do this
before posting the final combined owner outcome. Stale-head reviews are
informational. If `summary_truncated` is true, retrieve the full
review body through provider read tooling before disposition; stop if the full
body cannot be read. Do not poll or sleep in agent instructions; the released
`forge-cli pr merge` owns the configured observed-bot quiet period, timeout,
complete snapshot, final recheck, native `CHANGES_REQUESTED`, unresolved-thread,
unchecked-task, and provider-head gates.

If merge returns `review_convergence_activity_changed`, read `pr reviews`
again, disposition the new current-head evidence under the closed-set admission
rule, refresh the final owner outcome, and retry without extending the repair
loop for a non-admitted concern. For `review_changes_requested` or
`review_snapshot_incomplete`, inspect `pr reviews` and stop until the native
state is cleared or complete. For `unresolved_review_threads`, use
`forge-cli pr review-threads list`, then repair, reply and resolve as accepted,
or create a follow-up and resolve with its link per
`core/policies/review-thread-convergence.md`. Outdated unresolved threads are
auto-dispositioned `stale` by `pr merge` (recorded in
`data.stale_thread_dispositions`) and do not block, so this list/disposition
path applies only to the remaining non-outdated threads. For
`unchecked_task_items`, use
`forge-cli pr tasks`, then finish/check the item or rewrite it as deferred with
a follow-up ref. `review_convergence_head_changed` requires rebinding delivery
evidence to the new head, then re-run validation and affected review lenses,
read current-head summaries again, and post a new owner outcome before retrying.
Timeout failures require a stable provider state before retry. Bypass flags
remain exceptional and their rationale belongs in the delivery review outcome;
`--allow-unresolved-threads` additionally requires a paired
`--allow-unresolved-threads-reason "<why>"`, captured mechanically as
`data.unresolved_threads_override_reason`.

For linked tracking or dispatch issues, run a pre-merge lifecycle audit before
the merge. This is not closeout yet, because `record close` verifies the merged
PR/MR after merge:

```bash
forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json \
  issue view "$ISSUE" --with-comments >"$ISSUE_VIEW_JSON"
jq '{body:.data.body, comments:(.data.comments // [])}' \
  "$ISSUE_VIEW_JSON" >"$ISSUE_JSON"
jq -r .body "$ISSUE_JSON" >"$ISSUE_BODY"

plan-issue --format json record audit \
  --profile "$PROFILE" \
  --body-file "$ISSUE_BODY" \
  --comments-json "$ISSUE_JSON"
```

Stop if the audit lacks `session` evidence, if the latest state is not
`complete`, or if the dashboard still shows `Latest session: pending`.

Run linked issue closeout after merge when the body references a tracking or
dispatch issue via `Refs #<issue>` and `--no-closeout` was not supplied. Use the
provider-correct linked record ref: `$OWNER_REPO#$PR_NUMBER` on GitHub,
`$OWNER_REPO!$MR_NUMBER` on GitLab:

```bash
plan-issue --repo "$OWNER_REPO" --format json record close \
  --issue "$ISSUE" \
  --profile "$PROFILE" \
  --linked-pr "$LINKED_RECORD_REF" \
  --approval "$APPROVAL" \
  --bundle "$PLAN_BUNDLE" \
  --add-label state::closed \
  --remove-label state::needs-triage
```

Use `profile=tracking` for lightweight plan-tracking issues and
`profile=dispatch` for dispatch plan records.

## Workflow

1. Confirm the branch, base, dirty-tree scope, validation evidence, review
   outcome, and requested lifecycle mode. Ensure implementation commits were
   created through `semantic-commit`.
2. In close-unmerged mode, read the current provider record, record the abandon
   reason, run `forge-cli pr close` and stop before delivery or local pre-PR
   validation.
3. If `.agents/scripts/pre-pr.sh` is executable, run it through the repository
   dispatcher and stop on failure.
4. Inspect linked issues and closing references. For issue-backed plan work,
   use `Refs #<issue>` until `record close` has passed.
5. Render the PR/MR body with `agent-runtime pr-body render`.
6. Select labels before provider mutation; use
   `references/pr-lifecycle.md` for the shared taxonomy rule.
7. If `manifests/forge-labels.yaml` exists, validate labels with the
   appropriate `forge-cli label` surface before the first live delivery.
8. In create-only mode, run `forge-cli pr create`, return the provider URL, and
   stop. Otherwise run `forge-cli pr deliver` with selected `--label` flags,
   `--label-catalog manifests/forge-labels.yaml` when present, and
   `--no-merge` so checks / pipelines complete before the mandatory review gate.
9. Run the generic code-review outcome in pre-merge context. Start with
   unforced scope detection and select quick or full through **Review Profile
   Selection**. Quick requires an eligible L0/L1 change and a `pass`; L2/L3,
   risk signals, unresolved current-head review state, or `escalate` select full.
10. Keep review workers read-only. For a clean quick pass, defer the review
   outcome write to step 15; the required ledger genesis in step 11 is separate
   workflow state. As each full-profile lens or blocking quick finding returns,
   add it to the delivery ledger input. In the portable fallback, post one
   compact review comment through `forge-cli pr review` (a native `COMMENT`
   review event via `--submit-review` on GitHub) with `--decision comments-only`
   and that semantic `--lens` (`quick` for a quick finding). In a governed
   GitHub environment, do not post per-lens full reports through the personal identity.
   After the selected lens wave completes and before repair, publish
   one combined pre-repair report through `forge-review-publish`; its personal
   phase is metadata-only. The parent delivery workflow posts; reviewer
   subagents never call the provider. In either route, provider-visible finding
   evidence must exist before the repair in step 12 (see
   `REVIEW_OUTCOME_POSTING_CONTRACT.md`, posting order). On GitHub, attach
   `--thread-file` for actionable findings so the fix can close a native review
   thread; summary-only reviews omit it. Render both the body and thread file
   through `review-specialists bundle --profile provider-review`, then validate
   the body with `forge-cli pr review validate --specialist-report` before the
   provider write.
11. On GitHub, produce `REVIEW_LEDGER_FINDINGS` with `review-specialists bundle --mode
    delivery`, including its generated empty envelope for a clean review. Record
    the genesis ledger observation **before** repairing anything, at the head
    the review actually ran against:
    `forge-cli pr review-loop observe "$PR_NUMBER" --expected-head "$REVIEWED_HEAD"
    --findings-file "$REVIEW_LEDGER_FINDINGS"`. Finding rows are `open` at this
    point; an empty envelope records the clean quick/full pass. The head is
    a compare-and-swap input and history cannot be backfilled, so this step has
    no second chance once the repair is pushed — see **Review-Loop Ledger** for
    both accepted `--findings-file` shapes and the ordering rules. Validate with
    `--dry-run` first; a live `observe` writes durable provider state. On GitLab,
    do not require ledger artifacts or call `pr review-loop`; retain the
    outcome-note path and pass `--review-convergence=false` to merge.
12. Repair admitted findings in this delivery workflow, publish the repair with
   `git-cli push --format json`, then rerun validation, checks, and affected
   review as closed-set closure. Post each focused follow-up review comment with
   the same semantic lens through the same governed-vs-portable publication
   branch before continuing. A changed head or ordinary repair
   never switches quick closure to full discovery. Start a new discovery
   generation only for a user-requested fresh review or a repair that materially
   changes the accepted design, public contract, trust boundary, or migration
   strategy.
13. On GitHub, after that publish, create `REVIEW_LEDGER_DISPOSITIONS` as a bare
    array and append the closing observation at the repaired head with
    `disposition: fixed` (or an evidence-backed terminal disposition), passing
    `--expected-state <current tip>`.
    A `fixed` disposition is rejected at the head where the finding was first
    recorded, which is why step 11 had to precede the push. Repeat the closure
    mechanics only for the finite unresolved admitted finding set, inspecting
    the current tip before each round and replacing it with each live append's
    returned digest. Do not reopen full-diff discovery for an ordinary repair.
14. On GitHub, read `forge-cli pr reviews` once after specialist repairs and
    semantically disposition every actionable current-head summary under the
    closed-set admission rule. A new concern that is not admitted becomes
    follow-up or an explicit critical-risk handoff; it does not extend the
    current repair loop. Stale-head reviews are informational. When
    `summary_truncated` is true, obtain the full review body and
    stop if it is unavailable. Do not implement a polling or sleep loop in the
    workflow.
15. Post the final combined delivery review outcome body produced by the
   selected pre-merge profile through the same governed-vs-portable publication
   branch before merge. Use the
   final `--decision` and repeat every selected `--lens` (`quick` for quick
   merge; the complete specialist set for full); add native GitHub
   approval only through the declared independent-identity capability, and keep
   identity selection outside the public skill. Native submission carries
   `--recover-pending`, so an abandoned draft from an earlier attempt is cleared
   by the command; a refusal names the guard that rejected it. Do not delete
   drafts by hand or downgrade the outcome to a note.
   On GitHub, resolve the tri-state publication mode before any write.
   `governed` requires `forge-review-publish`; `portable` is automatic only
   when the installation declares no governed publisher or identity capability;
   `personal-escape` is an explicit, guarded exception after a proven
   pre-mutation publisher failure. Direct `forge-cli pr review` is never an
   implicit fallback from `governed`. The
   governed publisher posts the complete
   canonical body exactly once through the owner App and records only
   exact-head-verified `--metadata-only` provenance through the personal
   identity; the personal call never receives the report `--comment-file`.
   A required-but-missing or failed publisher blocks by default. Only after
   explicit maintainer authorization, a non-empty reason, and proof of
   `no-native-mutation` may delivery publish the combined report as an
   exact-head personal `comments-only` review. Record the reason and
   `independent review identity: unavailable` in provider-visible evidence,
   then keep the final combined decision as a non-native outcome note. Never
   take this escape after an indeterminate mutation or a pending/resumable
   publisher receipt.
16. Before merge, if the PR/MR references a linked tracking or dispatch issue,
    audit it and confirm lifecycle readiness: source/plan snapshots, complete
    state, latest `role=session`, validation, review, and dashboard links are
    present. If not, stop and route to the matching plan delivery workflow.
17. Merge with `forge-cli --provider "$PROVIDER" pr merge "$PR_NUMBER"` unless
    `--no-merge` is the requested final stop. The CLI owns observed quiet
    timing, complete/final native-review reads, native change requests,
    thread/task gates, and head CAS. On
    `review_convergence_activity_changed`, re-read `pr reviews`, disposition
    the new evidence under the closed-set admission rule, refresh the final
    owner outcome, and retry without extending the repair loop for a
    non-admitted concern. Route other
    typed review/thread/task failures through the matching read surface and the
    same repair/accept/follow-up discipline before retrying.
    `review_convergence_head_changed` additionally requires delivery-evidence
    rebinding, validation and affected-review reruns, and a new owner outcome on
    the new head before retry.
18. After merge, if the body referenced a linked tracking or dispatch issue
    and `--no-closeout` was not supplied, run `plan-issue record close` with
    the correct profile. On gate fail, leave the issue open with the blocked
    code surfaced by `plan-issue` and route to the matching closeout skill.
19. Record the PR/MR URL, labels, check/pipeline evidence, review outcome, merge
    commit, chained closeout result, and any fallback used in delivery notes.
20. If this workflow is the outermost terminal owner, finish any requested
    post-merge deployment, activation, archive, evidence, and local closeout
    duties, then apply `core/policies/git-delivery.md` terminal cleanup. Recheck
    status and provider merge/head truth. Restore a clean primary checkout to
    base, or invoke `git-cli worktree remove <path-or-slug> --format json` from
    the primary checkout through the supported hooked shell; the target-aware
    lease guard must confirm no live foreign owner before removal. If that proof
    or hook is unavailable, retain the worktree. Delete the local
    branch only when its tip equals the provider-confirmed delivered head;
    otherwise retain and report it. When the merge left the primary checkout's
    default branch behind its remote, advance it with
    `git-cli sync-default --format json`; that surface owns the remote-bound
    fast-forward, and raw `git merge` / `git pull` on the default branch stay
    refused even with `--ff-only` because local state cannot prove publication.
    If an outer L2/L3 workflow remains, hand it the captured identity and defer
    this step.

## Boundary

`forge-cli` owns provider create, checks/pipeline wait, ready, native-review
convergence, thread/task enforcement, provider-head binding, and merge calls.
`plan-issue record` owns linked issue lifecycle closeout. The workflow owner
owns scope judgment, code changes, local validation, review-profile and
pre-merge gate decisions,
repair loops, delivery outcome comments, and any temporary provider fallback
decision. The outermost workflow also owns terminal local cleanup after all
downstream duties; child delivery workflows hand off rather than clean early.
Provider auto-close keywords against issue-backed plan records remain banned.
