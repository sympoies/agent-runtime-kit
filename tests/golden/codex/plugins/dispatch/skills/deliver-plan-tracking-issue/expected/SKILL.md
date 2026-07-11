---
name: deliver-plan-tracking-issue
description: >
  Open or resume one lightweight issue-backed plan tracker and carry it through
  implementation, review, PR delivery, strict closeout, and archive handoff.
---

# Deliver Plan Tracking Issue

## Contract

Prereqs:

- Profile: `tracking`.
- CLI floors: `plan-issue >=1.0.13`, `plan-tooling >=1.0.1`,
  `forge-cli >=1.17.0`, `review-specialists`.
- The tracking issue is absent and ready to open, or open, visible, and
  reconcilable with `run-state.json`; FSM is not blocked or stale.
- PR delivery runs the generic code-review outcome in pre-merge mode and posts
  native review events per
  `core/skills/code-review/code-review-specialists/references/REVIEW_OUTCOME_POSTING_CONTRACT.md`.
  Every tracking PR runs the full gate; there is no single-author self-review
  shortcut.
- Shared family rules apply from
  `core/skills/dispatch/plan-issue-spec/skill-family.md`.
- Internal role ordering and single-writer boundaries apply from
  `references/outcome-routing.md`.

Inputs:

- `OWNER_REPO`, optional `ISSUE`, optional `RUN_STATE`, `PLAN_BUNDLE`, `SLUG`,
  `BRANCH`, `PR_NUMBER`, `PROVIDER`, `BASE_REF`, and post-close read-back paths
  `CLOSED_ISSUE_VIEW_JSON`, `CLOSED_ISSUE_JSON`, and `CLOSED_ISSUE_BODY`.
- Optional `LINKED_PR` when a PR already exists and should be verified
  instead of created.
- Approval evidence for the later close-ready probe.
- Review-gate artifacts: per-lens `REVIEW_LENS`,
  `SPECIALIST_REVIEW_COMMENT_FILE`, optional GitHub `REVIEW_THREAD_FILE` for
  actionable findings, `REVIEW_DECISION`, and `DELIVERY_REVIEW_OUTCOME`
  (combined outcome body).
- `REVIEW_OUTCOME_COMMENT`: the native review event URL produced by
  `forge-cli pr review --submit-review` (or a retained evidence path).
  `REVIEW_FINDINGS_JSON` is optional and contains finding rows when findings
  exist.

Outputs:

- `record open|attach --profile tracking` and `tracking run init` when the
  tracker does not yet exist or has no run state.
- Progress checkpoints: `tracking checkpoint --live --post
  state[,session[,validation]]`.
- PR delivery through `forge-cli pr deliver --no-merge`, or adoption of an
  already linked PR, so the review gate runs before merge.
- Native review events through `forge-cli pr review --submit-review`: one
  `COMMENT` per specialist lens (mapped reviewer bot profile) and one combined
  `APPROVE`/`REQUEST_CHANGES` outcome (`FORGE_BOT_PROFILE=dobi`), with a
  `--mirror-issue` breadcrumb to the tracking issue.
- Pre-merge disposition of every review thread (`pr review-threads`) and
  unchecked task item (`pr tasks`).
- Delivery checkpoint: `tracking checkpoint --live --post state,review`, whose
  `review` role records the native review outcome URL and is posted before merge.
- Per-task ledger sync through `plan-tooling ledger-update`.
- `forge-cli pr merge` after the gate, sweeps, and review checkpoint pass.
- Strict `tracking close-ready --expect-visible`, followed by
  `record close --profile tracking` only when readiness and approval are complete.
- Post-close provider read-back plus `record audit --expect-visible`, followed
  by `plan-archive discover` and dry-run-first `plan-archive migrate` routing;
  apply remains confirmation-gated.

Failure modes:

- Stop on `run-state-stale`, `issue-evidence-missing`, `RECORD_BLOCKED`,
  `visible-completeness-failed`, PR delivery failure, or any
  `close-ready` blocker.
- Stop on provider payload privacy failures such as `local_path_present`; rewrite
  useful evidence paths to `$HOME/...` and omit remote-useless local artifact
  paths before retrying.
- Stop on `ledger-rows-pending`; repair the named task rows with
  `plan-tooling ledger-update` before retrying the gate.
- Stop when `pr merge` fails closed on `unresolved_review_threads` or
  `unchecked_task_items`; disposition every thread and task item, then retry.
- Forbidden writes: dispatch-profile posts, raw lifecycle comments, raw
  `gh pr review` / `glab mr approve` for recorded review evidence, or merging before the review
  gate, sweeps, and `review` checkpoint complete.

## Outcome Routing

The user selects the L2 plan outcome, never tracker creation, execution,
review, closeout, or archive substeps. This parent selects those phases using
`references/outcome-routing.md` and preserves their
separate CLI write authorities.

When no tracker exists, validate the bundle, open or attach it through
`plan-issue record`, and initialize run state before implementation. When a
tracker exists, reconcile live evidence before any mutation. After delivery and
independent review, merge only after the issue-side review checkpoint and all
provider sweeps pass. Close only after `tracking close-ready` returns
`ready: true`; then run archive discovery and migration directly through
`plan-archive`, dry-run first and apply only with explicit confirmation.

## Entrypoint

```bash
plan-tooling validate --file "$PLAN_BUNDLE/$SLUG-plan.md" --format text --explain

# Open/attach and tracking run init are used only when the tracker/run is absent.
PROVIDER="$(forge-cli repo view --repo "$OWNER_REPO" --format json \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["provider"])')"
case "$PROVIDER" in
  github) PLAN_LABEL_ARGS=(--label workflow::plan --label workflow::tracking) ;;
  gitlab) PLAN_LABEL_ARGS=(--label workflow::tracking --label plan) ;;
  *) echo "unsupported tracker provider: $PROVIDER" >&2; exit 64 ;;
esac

plan-issue --repo "$OWNER_REPO" --format json record open \
  --profile tracking --bundle "$PLAN_BUNDLE" --title "$TITLE" \
  --label type::chore --label area::docs \
  --label state::needs-triage \
  "${PLAN_LABEL_ARGS[@]}"

plan-issue --format json tracking run init \
  --provider-repo "$OWNER_REPO" --issue "$ISSUE" \
  --bundle "$PLAN_BUNDLE" \
  --execution-state-file "$PLAN_BUNDLE/$SLUG-execution-state.md" \
  --branch "$BRANCH" \
  --now "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

plan-issue --format json tracking status \
  --provider-repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --profile tracking \
  --run-state "$RUN_STATE" \
  --expect-visible

plan-tooling ledger-update \
  --execution-state "$PLAN_BUNDLE/$SLUG-execution-state.md" \
  --task "$TASK_ID" \
  --status done \
  --evidence "$EVIDENCE"

plan-issue --format json tracking run update \
  --run-state "$RUN_STATE" \
  --phase validating \
  --validation-overall pass \
  --validation-command "$VALIDATION_COMMAND" \
  --validation-status pass \
  --validation-evidence "$VALIDATION_LOG" \
  --now "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

plan-issue --format json tracking checkpoint \
  --provider-repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --profile tracking \
  --run-state "$RUN_STATE" \
  --live \
  --post state,session,validation \
  --repair-dashboard

# Deliver the PR without merging so the review gate has a window (adopt and
# verify LINKED_PR through pr deliver existing-PR adoption when it already exists).
forge-cli pr deliver --repo "$OWNER_REPO" \
  --kind feature --title "$PR_TITLE" \
  --head "$BRANCH" --base main \
  --body-file "$PR_BODY_FILE" \
  --test-first-evidence "$EVIDENCE_DIR" \
  --no-merge --format json

# Shared read-only specialist gate (min testing + maintainability).
review-specialists scope --base "$BASE_REF" --testing --maintainability --format json

# Native review events (GitHub) per REVIEW_OUTCOME_POSTING_CONTRACT.md: one
# COMMENT per lens with its reviewer bot profile as each lens returns, then the
# combined APPROVE/REQUEST_CHANGES outcome as dobi.
SUBMIT_REVIEW=(); [ "$PROVIDER" = github ] && SUBMIT_REVIEW=(--submit-review)

# Repeat this specialist block once for each returned lens: testing,
# maintainability, plus any risk lens selected by generic pre-merge review.
THREAD_FILE_ARGS=()
if [ "$PROVIDER" = github ] && [ -n "${REVIEW_THREAD_FILE:-}" ]; then
  THREAD_FILE_ARGS=(--thread-file "$REVIEW_THREAD_FILE")
fi
case "$REVIEW_LENS" in
  red-team) REVIEW_BOT_PROFILE=review-red-team ;;
  testing) REVIEW_BOT_PROFILE=review-testing-bot ;;
  maintainability) REVIEW_BOT_PROFILE=review-maintainability ;;
  performance) REVIEW_BOT_PROFILE=review-performance ;;
  security) REVIEW_BOT_PROFILE=review-security ;;
  api-contract) REVIEW_BOT_PROFILE=review-api-contract ;;
  data-migration) REVIEW_BOT_PROFILE=review-data-migration ;;
  *) REVIEW_BOT_PROFILE=dobi ;;
esac
FORGE_BOT_PROFILE="$REVIEW_BOT_PROFILE" forge-cli --provider "$PROVIDER" pr review "$PR_NUMBER" \
  --repo "$OWNER_REPO" \
  --decision comments-only \
  "${SUBMIT_REVIEW[@]}" \
  "${THREAD_FILE_ARGS[@]}" \
  --comment-file "$SPECIALIST_REVIEW_COMMENT_FILE" \
  --lens "$REVIEW_LENS" \
  --issue "$ISSUE" --mirror-issue --format json

FORGE_BOT_PROFILE=dobi forge-cli --provider "$PROVIDER" pr review "$PR_NUMBER" \
  --repo "$OWNER_REPO" \
  --decision "$REVIEW_DECISION" \
  "${SUBMIT_REVIEW[@]}" \
  --comment-file "$DELIVERY_REVIEW_OUTCOME" \
  --lens testing --lens maintainability \
  --issue "$ISSUE" --mirror-issue --format json

# Disposition every review thread and task-list item before merge.
forge-cli --provider "$PROVIDER" --format json pr review-threads list "$PR_NUMBER"
forge-cli --provider "$PROVIDER" --format json pr tasks "$PR_NUMBER"

# Record issue-side review evidence from the native outcome, then post the final
# state + review checkpoint before merging.
plan-issue --format json tracking run update \
  --run-state "$RUN_STATE" \
  --phase ready-for-close \
  --linked-pr "$OWNER_REPO#$PR_NUMBER" \
  --review-decision approve \
  --review-lens testing \
  --review-lens maintainability \
  --review-outcome-comment "$REVIEW_OUTCOME_COMMENT" \
  --now "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

plan-issue --format json tracking checkpoint \
  --provider-repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --profile tracking \
  --run-state "$RUN_STATE" \
  --live \
  --post state,review \
  --repair-dashboard

# Merge only after the gate, sweeps, and review checkpoint pass.
forge-cli --provider "$PROVIDER" pr merge "$PR_NUMBER" --method squash

plan-issue --format json tracking close-ready \
  --provider-repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --profile tracking \
  --run-state "$RUN_STATE" \
  --linked-pr "$OWNER_REPO#$PR_NUMBER" \
  --approval "$APPROVAL" \
  --expect-visible

# Only after close-ready reports ready=true and blockers=[].
plan-issue --repo "$OWNER_REPO" --format json record close \
  --profile tracking --issue "$ISSUE" --bundle "$PLAN_BUNDLE" \
  --linked-pr "$OWNER_REPO#$PR_NUMBER" --approval "$APPROVAL" \
  --add-label state::closed --remove-label state::needs-triage

# Read back the closed provider issue body and comments, then require visible
# closeout evidence before archive maintenance.
forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json issue view "$ISSUE" --with-comments \
  >"$CLOSED_ISSUE_VIEW_JSON"
jq '{body:.data.body, comments:(.data.comments // [])}' \
  "$CLOSED_ISSUE_VIEW_JSON" >"$CLOSED_ISSUE_JSON"
jq -r .body "$CLOSED_ISSUE_JSON" >"$CLOSED_ISSUE_BODY"

plan-issue --repo "$OWNER_REPO" --format json record audit \
  --profile tracking \
  --body-file "$CLOSED_ISSUE_BODY" \
  --comments-json "$CLOSED_ISSUE_JSON" \
  --expect-visible

plan-archive discover --source-repo "$PWD" --format json
plan-archive migrate --plan "$PLAN_BUNDLE" --issue "$ISSUE_URL" --format json
```

`forge-cli pr deliver --no-merge` creates, checks, and marks the PR ready without
merging, leaving the window for the review gate; `forge-cli pr merge` performs the
merge only after the gate, the thread/task sweeps, and the issue-side `review`
checkpoint complete. When `LINKED_PR` already exists, adopt and verify it through
`pr deliver` existing-PR adoption instead of re-creating it, and record the ref
with `tracking run update --linked-pr`.

Post one compact specialist review comment per lens as it returns — before any
repair — using the mapped reviewer bot profile (`FORGE_BOT_PROFILE=dobi` for
unmapped lenses), with `--thread-file "$REVIEW_THREAD_FILE"` for actionable GitHub
findings; the combined delivery outcome posts last as `dobi`.
The generic review outcome owns the read-only lenses and mode selection; this
skill owns the provider writes, bot-profile resolution, sweeps, and merge, and
reviewer subagents never post. `pr merge` fails closed on
`unresolved_review_threads` / `unchecked_task_items`, so disposition every thread
and task item first.

Plan-tracking PRs are `--kind feature` records, so when the test-first gate is
enabled (`[test_first].require = true` in a repo `.forge-cli.toml` or the
user-global `${XDG_CONFIG_HOME:-~/.config}/forge-cli/config.toml`) the deliver
above requires `--test-first-evidence "$EVIDENCE_DIR"` — the `verify`-clean
directory the policy-owned `test-first-evidence` CLI flow produces — or it fails closed with
`test_first_evidence_required`.

## Workflow

1. **Open / preflight** — validate the bundle. Open or attach the tracker and
   initialize run state when absent; otherwise run `tracking status
   --expect-visible`. Stop on stale, blocked, or non-visible evidence.
2. **Implementation / validation** — do local work, update the task ledger
   after every task transition, and checkpoint only changed roles.
3. **PR branch** — deliver with `forge-cli pr deliver --no-merge` (or adopt and
   verify `LINKED_PR` through `pr deliver` existing-PR adoption). Do not merge
   yet; the review gate runs first.
4. **Review gate** — run the generic code-review outcome in pre-merge mode (min `testing` +
   `maintainability`; add risk lenses per scope). Post each lens's specialist
   review comment through `forge-cli pr review` as it returns (native `COMMENT`
   on GitHub via `--submit-review`, mapped reviewer bot profile; `--thread-file`
   for actionable findings), then the combined delivery outcome (native
   `APPROVE`/`REQUEST_CHANGES`, `FORGE_BOT_PROFILE=dobi`, `--mirror-issue`), per
   `REVIEW_OUTCOME_POSTING_CONTRACT.md`. Every tracking PR runs the full gate —
   there is no single-author self-review shortcut. Repair concrete findings in
   this delivery branch and rerun affected lenses before continuing.
5. **Pre-merge sweeps** — disposition every unresolved review thread
   (`pr review-threads`, `unresolved==0`) and unchecked task item (`pr tasks`,
   `unchecked==0`); `pr merge` fails closed otherwise.
6. **Review + final checkpoint** — set `phase=ready-for-close`, record the linked
   PR, review decision, lenses, and `--review-outcome-comment` (the native review
   event URL); add `--review-findings-file "$REVIEW_FINDINGS_JSON"` when findings
   exist; then post `state,review` in one live checkpoint. This issue-side
   `review` evidence is posted before merge.
7. **Merge** — `forge-cli pr merge` once the gate, sweeps, and review checkpoint
   pass.
8. **Close-ready / closeout** — run `tracking close-ready --expect-visible`.
   Stop on every blocker. On `ready: true`, write the closing summary, perform
   only controller-authorized final-role/dashboard repair, and call `record
   close --profile tracking` with linked PR and approval evidence.
9. **Closeout read-back** — fetch the closed provider issue with comments and
   run `record audit --profile tracking --expect-visible`; stop unless the
   closeout role is visible and lint-clean.
10. **Archive maintenance** — only after closeout read-back succeeds, run
    `plan-archive discover`, then the default dry-run `plan-archive migrate`;
    apply only
    after explicit confirmation and a clean plan.

## Boundary

Owns:

- Delivery-scope judgement, validation strength, review-gate orchestration and
  the provider review writes (per-lens specialist comments + the combined native
  outcome), pre-merge thread/task disposition, final state/review checkpoint
  timing, the merge, strict closeout, read-back, and archive routing.

Must not:

- Use dispatch-profile semantics, let reviewer subagents post provider comments,
  close with any blocker, archive before close read-back, or merge before the
  review gate, sweeps, and `review` checkpoint complete.

Internal phases:

- Open, execution, delivery, independent review, closeout, and archive phases
  follow `references/outcome-routing.md`; they are not separate user
  choices.
