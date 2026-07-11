---
name: deliver-pr
description: >
  Deliver GitHub pull requests or GitLab merge requests end to end through the released nils-cli `forge-cli pr deliver` macro.
---

# Deliver PR / MR

## Contract

Prereqs:

- `agent-runtime`, `forge-cli >=1.17.0`, `plan-issue >=1.1.0`, and
  `review-specialists` are installed from the released nils-cli package and
  available on `PATH`. The generic code-review outcome uses
  `review-specialists` in pre-merge mode; the review-thread sweep and merge gate need
  `forge-cli` 1.0.16, the task-list sweep and merge gate 1.0.17, and
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
- A provider review-thread sweep completed immediately before merge, with
  every unresolved thread (bot or human) dispositioned: repaired, resolved as
  accepted, or converted to a follow-up issue.
- A task-list sweep completed immediately before merge, with every unchecked
  `- [ ]` item in the PR/MR description dispositioned: completed and checked
  off, or rewritten as deferred with a follow-up issue ref.
- A merged PR/MR through `forge-cli pr merge`, unless `--no-merge` is supplied.
- When a linked issue closeout runs, `plan-issue record close` posts closeout
  evidence, repairs the dashboard, verifies linked records, and closes the
  issue.

Failure modes:

- Provider auth fails, the branch has no pushed upstream, or the base branch is
  not the intended target.
- Required checks / pipeline checks fail, time out, remain pending, or are
  missing without an explicit no-checks decision.
- Selected labels fail catalog validation or the provider rejects label
  application.
- Mandatory pre-merge review gate findings are unresolved or undispositioned.
- Provider review threads — typically from bot reviewers posting minutes after
  PR creation — remain unresolved and undispositioned at merge time. CI checks
  and the local review gate do not surface them; `forge-cli pr merge` fails
  closed with `unresolved_review_threads`, and the sweep is how the workflow
  dispositions them before that gate trips.
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

## Lifecycle Mode Selection

The user requests the PR/MR outcome, not a lifecycle helper.

- **Create only** — render and validate the body, create the draft provider
  record with `forge-cli pr create`, return its URL, and stop before checks,
  review, merge, or linked-issue closeout.
- **Deliver** — create or adopt the record, wait for checks, run the mandatory
  review gate, repair findings, sweep threads/tasks, and merge unless the user
  requested a readiness stop.
- **Review repair** — adopt the existing record, classify unresolved review
  threads, make authorized fixes, rerun validation and affected review modes,
  and return to the delivery gates.
- **Merge** — adopt an existing ready record and run every remaining review,
  task, thread, linked-lifecycle, and checks gate before `forge-cli pr merge`.
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
# Native review events are GitHub-only; GitLab posts an outcome note instead.
SUBMIT_REVIEW=()
[ "$PROVIDER" = github ] && SUBMIT_REVIEW=(--submit-review)
FORGE_BOT_PROFILE=dobi forge-cli --provider "$PROVIDER" pr review "$PR_NUMBER" \
  --decision "$REVIEW_DECISION" \
  "${SUBMIT_REVIEW[@]}" \
  --comment-file "$DELIVERY_REVIEW_OUTCOME" \
  --lens testing \
  --lens maintainability
forge-cli --provider "$PROVIDER" pr merge "$PR_NUMBER" --method squash
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

Immediately before the merge call, sweep provider review threads. Bot
reviewers post asynchronously — often minutes after PR creation — so the sweep
runs at the last action before merge, not only at creation time:

```bash
forge-cli --provider "$PROVIDER" --format json pr review-threads list "$PR_NUMBER"
```

`data.unresolved == 0` is the gate. Disposition every unresolved thread before
merge per `core/policies/review-thread-convergence.md` (the per-finding triage
table and the convergence/stopping rule): repair it in this workflow, reply and
resolve it as an accepted tradeoff, or convert it to a follow-up issue and
resolve the thread with the link. `forge-cli pr merge` (and the `pr deliver`
merge step) also enforces
this mechanically — merging with unresolved threads fails closed with
`unresolved_review_threads` (sympoies/nils-cli#808, shipped in v1.0.16). Never
pass `--allow-unresolved-threads` to silence the gate without dispositioning
the threads and recording the reason in the delivery review outcome.

In the same pre-merge pass, sweep the PR/MR description's task list:

```bash
forge-cli --provider "$PROVIDER" --format json pr tasks "$PR_NUMBER"
```

`data.unchecked == 0` is the gate. Disposition every unchecked `- [ ]` item
before merge: finish the work and check it off (`- [x]`), or rewrite the item
as deferred with a follow-up issue ref. `forge-cli pr merge` (and the
`pr deliver` merge step) also enforces this mechanically — merging with
unchecked items fails closed with `unchecked_task_items`
(sympoies/nils-cli#814, shipped in v1.0.17). The bypass pair
`--allow-unchecked-tasks` + `--allow-unchecked-tasks-reason` records its
reason in the merge payload; use it only after dispositioning the items is
genuinely not possible, and repeat the reason in the delivery review outcome.
Author `## Test plan` checklists in their final state — a checklist you do
not intend to finish before merge belongs in a follow-up issue, not the
description.

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
12. Post the final combined delivery review outcome body produced by the
   generic review's pre-merge mode with `forge-cli pr review` (a native
   `APPROVE` / `REQUEST_CHANGES` review event via `--submit-review` on GitHub)
   before merge. Set `FORGE_BOT_PROFILE=dobi` for combined delivery-owner
   outcomes so they stay on `dobi-bot`; set a reviewer bot profile only for
   mapped specialist review comments.
13. Sweep provider review threads immediately before merge with
    `forge-cli pr review-threads` (see Entrypoint) — bot reviewers post
    asynchronously, so this runs as the last gate, not only at creation.
    Disposition every unresolved thread: repair, reply-and-resolve as
    accepted, or convert to a follow-up issue. `pr merge` refuses
    undispositioned threads (`unresolved_review_threads`); do not bypass with
    `--allow-unresolved-threads` without recording the reason.
14. In the same pass, sweep the description's task list with
    `forge-cli pr tasks` (see Entrypoint). Disposition every unchecked
    `- [ ]` item: check it off or rewrite it as deferred with a follow-up
    ref. `pr merge` refuses unchecked items (`unchecked_task_items`); do not
    bypass with `--allow-unchecked-tasks` without its required reason flag
    and a matching note in the delivery review outcome.
15. Before merge, if the PR/MR references a linked tracking or dispatch issue,
    audit it and confirm lifecycle readiness: source/plan snapshots, complete
    state, latest `role=session`, validation, review, and dashboard links are
    present. If not, stop and route to the matching plan delivery workflow.
16. Merge with `forge-cli --provider "$PROVIDER" pr merge "$PR_NUMBER"` unless
    `--no-merge` is the requested final stop.
17. After merge, if the body referenced a linked tracking or dispatch issue
    and `--no-closeout` was not supplied, run `plan-issue record close` with
    the correct profile. On gate fail, leave the issue open with the blocked
    code surfaced by `plan-issue` and route to the matching closeout skill.
18. Record the PR/MR URL, labels, check/pipeline evidence, review outcome, merge
    commit, chained closeout result, and any fallback used in delivery notes.

## Boundary

`forge-cli` owns provider create, checks/pipeline wait, ready, and merge calls.
`plan-issue record` owns linked issue lifecycle closeout. The workflow owner
owns scope judgment, code changes, local validation, pre-merge gate decisions,
repair loops, delivery outcome comments, and any temporary provider fallback
decision. Provider auto-close keywords against issue-backed plan records remain
banned.
