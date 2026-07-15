---
name: deliver-pr
description: >
  Deliver GitHub pull requests or GitLab merge requests end to end through the released nils-cli `forge-cli pr deliver` macro.
---

# Deliver PR / MR

## Contract

Prereqs:

- `agent-runtime`, `forge-cli >=1.21.34`, `plan-issue >=1.1.0`, and
  `review-specialists` are installed from the released nils-cli package and
  available on `PATH`. The generic code-review outcome uses
  `review-specialists` in pre-merge mode; native review summaries and observed
  convergence need `forge-cli` 1.21.34, the review-thread merge gate needs
  1.0.16, the task-list merge gate needs 1.0.17, and
  existing-PR adoption in `pr deliver` needs 1.1.0. Linked issue closeout
  relies on the unified terminal task-row contract in `plan-issue` 1.1.0.
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
- Mandatory generic code review in pre-merge mode.
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
- A generic pre-merge review result completed before merge with at least
  `testing` and `maintainability`.
- Compact specialist reviews posted to the PR/MR as each reviewer lens returns
  (native `COMMENT` review events on GitHub via `--submit-review`, outcome notes
  on GitLab). Mapped lenses use their reviewer bot profile; unmapped specialist
  lenses use `FORGE_BOT_PROFILE=dobi`. These use `comments-only` and report
  findings and evidence only. On GitHub, actionable findings that require owner
  changes are also passed through `--thread-file` so the owning agent can fix and
  resolve them; no-finding reports omit `--thread-file` and stay summary-only.
  If a linked tracking or dispatch issue is present, mirror the compact review
  URL breadcrumb to that issue.
- A delivery review outcome posted to the PR/MR before merge through
  `forge-cli pr review` (a native `APPROVE` / `REQUEST_CHANGES` review event on
  GitHub via `--submit-review`); combined owner outcomes set
  `FORGE_BOT_PROFILE=dobi`, and own final finding dispositions.
- On GitHub, current-head native review summaries inspected through
  `forge-cli pr reviews` and semantically dispositioned before the final owner
  outcome. Stale-head reviews remain informational. GitLab retains its outcome
  note flow because native review snapshots are GitHub-only in v1.
- Mechanical convergence, unresolved-thread, unchecked-task, and provider-head
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

- Provider auth fails, the branch has no pushed upstream, or the base branch is
  not the intended target.
- Required checks / pipeline checks fail, time out, remain pending, or are
  missing without an explicit no-checks decision.
- Selected labels fail catalog validation or the provider rejects label
  application.
- Mandatory pre-merge review gate findings are unresolved or undispositioned.
- Current-head native review summaries are unread or contain actionable
  feedback that has not been repaired, accepted with rationale, or moved to a
  follow-up.
- `forge-cli pr merge` returns `review_changes_requested`,
  `review_convergence_activity_changed`, `review_convergence_head_changed`,
  `review_convergence_timeout`, `review_snapshot_incomplete`,
  `unresolved_review_threads`, or `unchecked_task_items`. Read and disposition
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
  review gate, inspect and disposition native summaries, then merge through the
  CLI-owned convergence/thread/task gates unless the user requested a readiness
  stop.
- **Review repair** — adopt the existing record, classify unresolved review
  threads, make authorized fixes, rerun validation and affected review modes,
  and return to the delivery gates.
- **Merge** — adopt an existing ready record, inspect native review evidence,
  and satisfy every remaining semantic, linked-lifecycle, and provider gate
  before `forge-cli pr merge`.
- **Close unmerged** — only when the user explicitly abandons the record; read
  current state, record the reason, and call `forge-cli pr close` without
  pretending delivery succeeded.

Dispatch lane PR creation remains an internal L3 dispatch role because its
plan-branch target and lane checkpoint authority belong to that outcome.

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

Run the generic code-review outcome in pre-merge mode before merge. Its minimum
underlying scope is:

```bash
review-specialists scope \
  --base "$BASE_REF" \
  --testing \
  --maintainability \
  --format json
# Read native review bodies after specialist posting and repair. Current-head
# summaries are semantic evidence; stale-head summaries are informational.
if [ "$PROVIDER" = github ]; then
  forge-cli --provider "$PROVIDER" --format json pr reviews "$PR_NUMBER"
fi
# Native review events are GitHub-only; GitLab posts an outcome note instead.
SUBMIT_REVIEW=()
[ "$PROVIDER" = github ] && SUBMIT_REVIEW=(--submit-review)
# Observed convergence is GitHub-only in v1. Preserve GitLab delivery even when
# the user's global forge-cli config enables it.
REVIEW_CONVERGENCE_ARGS=()
[ "$PROVIDER" = gitlab ] && REVIEW_CONVERGENCE_ARGS=(--review-convergence=false)
FORGE_BOT_PROFILE=dobi forge-cli --provider "$PROVIDER" pr review "$PR_NUMBER" \
  --decision "$REVIEW_DECISION" \
  "${SUBMIT_REVIEW[@]}" \
  --comment-file "$DELIVERY_REVIEW_OUTCOME" \
  --lens testing \
  --lens maintainability
forge-cli --provider "$PROVIDER" pr merge "$PR_NUMBER" --method squash \
  "${REVIEW_CONVERGENCE_ARGS[@]}"
```

Map the final delivery review outcome to `approve` when delivery may merge and
`request-changes` when the review blocks. Use `comments-only` only for
specialist review comments or other non-decisional notes, not for the final
combined delivery-owner outcome. On GitHub, `--submit-review` makes this a native
pull request review event (`approve`→`APPROVE`, `request-changes`→`REQUEST_CHANGES`)
authored by `dobi-bot`; on GitLab `forge-cli pr review` records the decision as
outcome-note metadata only and does not mutate native approval state.

For bot identity and issue mirroring: post a compact specialist review comment
after each reviewer lens returns and after each focused follow-up rerun. Set the
matching profile for that one command only when the lens is mapped:
`red-team` -> `review-red-team`, `testing` -> `review-testing-bot`,
`maintainability` -> `review-maintainability`, `performance` ->
`review-performance`, `security` -> `review-security`, `api-contract` ->
`review-api-contract`, and `data-migration` -> `review-data-migration`. Any
other or unknown lens uses `FORGE_BOT_PROFILE=dobi` with
`--decision comments-only`. For the final combined delivery-owner outcome,
set `FORGE_BOT_PROFILE=dobi` so `dobi-bot` authors it. When the PR/MR is linked
to a tracking or dispatch issue and the issue number is available, add
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
machine verdict: repair actionable feedback, accept it with rationale, or move
it to a follow-up before posting the final combined owner outcome. Stale-head
reviews are informational. GitLab has no native snapshot in v1 and keeps the
existing specialist/outcome-note flow. If `summary_truncated` is true, retrieve
the full review body through provider read tooling before disposition; stop if
the full body cannot be read. Do not poll or sleep in agent instructions; the
released `forge-cli pr merge` owns the configured observed-bot quiet period,
timeout, complete snapshot, final recheck, native `CHANGES_REQUESTED`,
unresolved-thread, unchecked-task, and provider-head gates.

Observed convergence is GitHub-only in v1. On GitLab, pass
`--review-convergence=false` explicitly so a user-global GitHub policy does not
turn a supported MR delivery into `provider_unsupported`.

If merge returns `review_convergence_activity_changed`, read `pr reviews`
again, disposition the new current-head evidence, refresh the final owner
outcome, and retry. For `review_changes_requested` or
`review_snapshot_incomplete`, inspect `pr reviews` and stop until the native
state is cleared or complete. For `unresolved_review_threads`, use
`forge-cli pr review-threads list`, then repair, reply and resolve as accepted,
or create a follow-up and resolve with its link per
`core/policies/review-thread-convergence.md`. For `unchecked_task_items`, use
`forge-cli pr tasks`, then finish/check the item or rewrite it as deferred with
a follow-up ref. `review_convergence_head_changed` requires rebinding delivery
evidence to the new head, then re-run validation and affected review lenses,
read current-head summaries again, and post a new owner outcome before retrying.
Timeout failures require a stable provider state before retry. Bypass flags
remain exceptional and their rationale belongs in the delivery review outcome.

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
9. Run the generic code-review outcome in pre-merge mode.
10. Keep review workers read-only. As each reviewer lens returns,
   post one compact specialist review comment through `forge-cli pr review`
   (a native `COMMENT` review event via `--submit-review` on GitHub)
   with the mapped reviewer bot profile, or `FORGE_BOT_PROFILE=dobi` for
   unmapped specialist lenses. The parent delivery workflow posts; reviewer
   subagents never call the provider. Post the moment each lens returns — before
   the repair in step 11, never batched after it; the comment is the finding the
   step-11 fix responds to, so it must exist first (see
   `REVIEW_OUTCOME_POSTING_CONTRACT.md`, posting order). On GitHub, attach
   `--thread-file` for actionable findings so the fix can close a native review
   thread; summary-only reviews omit it.
11. Repair concrete findings in this delivery workflow, then rerun validation,
   checks, and affected review lenses. Post each focused follow-up specialist
   review comment with the same bot-profile selection before continuing.
12. On GitHub, read `forge-cli pr reviews` once after specialist repairs and
    semantically disposition every actionable current-head summary; stale-head
    reviews are informational. When `summary_truncated` is true, obtain the full
    review body and stop if it is unavailable. On GitLab, retain the outcome-note
    path and do not invoke the unsupported snapshot. Do not implement a polling
    or sleep loop in the workflow.
13. Post the final combined delivery review outcome body produced by the
   generic review's pre-merge mode with `forge-cli pr review` (a native
   `APPROVE` / `REQUEST_CHANGES` review event via `--submit-review` on GitHub)
   before merge. Set `FORGE_BOT_PROFILE=dobi` for combined delivery-owner
   outcomes so they stay on `dobi-bot`; set a reviewer bot profile only for
   mapped specialist review comments.
14. Before merge, if the PR/MR references a linked tracking or dispatch issue,
    audit it and confirm lifecycle readiness: source/plan snapshots, complete
    state, latest `role=session`, validation, review, and dashboard links are
    present. If not, stop and route to the matching plan delivery workflow.
15. Merge with `forge-cli --provider "$PROVIDER" pr merge "$PR_NUMBER"` unless
    `--no-merge` is the requested final stop. The CLI owns observed quiet
    timing, complete/final native-review reads, native change requests,
    thread/task gates, and head CAS. On
    `review_convergence_activity_changed`, re-read `pr reviews`, disposition
    the new evidence, refresh the final owner outcome, and retry. Route other
    typed review/thread/task failures through the matching read surface and the
    same repair/accept/follow-up discipline before retrying.
    `review_convergence_head_changed` additionally requires delivery-evidence
    rebinding, validation and affected-review reruns, and a new owner outcome on
    the new head before retry.
16. After merge, if the body referenced a linked tracking or dispatch issue
    and `--no-closeout` was not supplied, run `plan-issue record close` with
    the correct profile. On gate fail, leave the issue open with the blocked
    code surfaced by `plan-issue` and route to the matching closeout skill.
17. Record the PR/MR URL, labels, check/pipeline evidence, review outcome, merge
    commit, chained closeout result, and any fallback used in delivery notes.
18. If this workflow is the outermost terminal owner, finish any requested
    post-merge deployment, activation, archive, evidence, and local closeout
    duties, then apply `core/policies/git-delivery.md` terminal cleanup. Recheck
    status and provider merge/head truth. Restore a clean primary checkout to
    base, or invoke `git-cli worktree remove <path-or-slug> --format json` from
    the primary checkout through the supported hooked shell; the target-aware
    lease guard must confirm no live foreign owner before removal. If that proof
    or hook is unavailable, retain the worktree. Delete the local
    branch only when its tip equals the provider-confirmed delivered head;
    otherwise retain and report it. If an outer L2/L3 workflow remains, hand it
    the captured identity and defer this step.

## Boundary

`forge-cli` owns provider create, checks/pipeline wait, ready, native-review
convergence, thread/task enforcement, provider-head binding, and merge calls.
`plan-issue record` owns linked issue lifecycle closeout. The workflow owner
owns scope judgment, code changes, local validation, pre-merge gate decisions,
repair loops, delivery outcome comments, and any temporary provider fallback
decision. The outermost workflow also owns terminal local cleanup after all
downstream duties; child delivery workflows hand off rather than clean early.
Provider auto-close keywords against issue-backed plan records remain banned.
