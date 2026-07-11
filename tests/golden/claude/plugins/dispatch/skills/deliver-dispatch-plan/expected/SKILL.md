---
name: deliver-dispatch-plan
description: >
  Open or resume one shared dispatch plan issue, coordinate independently
  reviewed lane PRs, integrate approved work, and close through strict gates.
---

# Deliver Dispatch Plan

## Contract

Prereqs:

- Profile: `dispatch`.
- CLI floors: `plan-issue >=1.0.13`, `plan-tooling >=1.0.1`,
  `forge-cli >=1.17.0`.
- The dispatch issue is either not opened yet, or the existing issue is
  the same shared plan being resumed by the orchestrator.
- Dispatch `run-state.json` is either uninitialized or reconciled.
- Shared family rules apply from
  `core/skills/dispatch/plan-issue-spec/skill-family.md`.
- Internal role ordering and single-writer boundaries apply from
  `references/outcome-routing.md`.

Inputs:

- `OWNER_REPO`, `PLAN_BUNDLE`, `PLAN`, `SLUG`, optional `ISSUE`, `PROVIDER`,
  and post-close read-back paths `CLOSED_ISSUE_VIEW_JSON`,
  `CLOSED_ISSUE_JSON`, and `CLOSED_ISSUE_BODY`.
- `RUN_STATE` for the dispatch run.
- Lane assignments with `TASK_ID` / sprint / PR group, `PLAN_BRANCH`,
  exact task context, and the dispatch bundle
  (`TASK_PROMPT_PATH`, `PLAN_SNAPSHOT_PATH`, `DISPATCH_RECORD_PATH`).
- Dispatch labels. GitHub uses `workflow::plan` plus
  `workflow::dispatch`; GitLab uses only `workflow::dispatch` plus bare
  `plan` because scoped labels collapse per `key::` scope.
- Lane approval URLs, review evidence paths, linked PRs, and final
  integration evidence for close-ready.

Outputs:

- `record open|attach --profile dispatch` for source, plan, and initial
  state snapshots.
- `tracking run init --profile dispatch --execution-state-file ...`.
  Always pass `--execution-state-file`; otherwise later dispatch state
  checkpoints render a synthesized single-row ledger instead of the
  accumulative task table.
- Dispatch-level checkpoints through `tracking checkpoint --profile
  dispatch --live --post state[,session[,validation[,review]]]`.
- Final per-lane ledger repair through `plan-tooling ledger-update`.
- Independent lane review and orchestrator-owned merge after approval.
- Strict `tracking close-ready --profile dispatch --expect-visible`, followed
  by `record close --profile dispatch` only when every lane and integration
  gate passes.
- Post-close provider read-back plus
  `record audit --profile dispatch --expect-visible` before completion.

Failure modes:

- Stop on `run-state-stale`, `RECORD_BLOCKED`,
  `visible-completeness-failed`, or any close-ready blocker.
- Stop on provider payload privacy failures such as `local_path_present`; rewrite
  useful evidence paths to `$HOME/...` and omit remote-useless local artifact
  paths before retrying.
- Stop on `ledger-rows-pending`; repair only the named task rows before
  retrying close-ready.
- Forbidden writes: lane-scoped implementation posts by the orchestrator, lane
  review posts by lane executors, lightweight-tracking closeout rules, multiple
  shared issues for one dispatch plan, or raw lifecycle comments.

## Outcome Routing

The user selects the L3 outcome, never a lane lifecycle substep. This parent
applies `references/outcome-routing.md` to route lane
execution, plan-branch PR creation, independent review, orchestrator merge,
plan-level checkpoints, and strict closeout while keeping one writer for every
role.

Lane executors stop after implementation, validation, PR creation, and their
lane-scoped state/session/validation checkpoint. An independent reviewer owns
provider review activity and the lane review checkpoint. Only the orchestrator
may merge an approved lane PR with `--allow-non-default-base`, update
plan-level integration truth, and enter dispatch closeout.

## Entrypoint

```bash
plan-tooling validate --file "$PLAN" --format text --explain

# GitHub label form. For GitLab, drop workflow::plan and keep
# workflow::dispatch plus the bare plan marker.
plan-issue --repo "$OWNER_REPO" --format json record open \
  --profile dispatch \
  --bundle "$PLAN_BUNDLE" \
  --title "$TITLE" \
  --label type::chore \
  --label area::docs \
  --label state::needs-triage \
  --label workflow::plan \
  --label workflow::dispatch \
  --label plan

plan-issue --format json tracking run init \
  --provider-repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --profile dispatch \
  --bundle "$PLAN_BUNDLE" \
  --execution-state-file "$PLAN_BUNDLE/$SLUG-execution-state.md" \
  --now "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

plan-issue --format json tracking checkpoint \
  --provider-repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --profile dispatch \
  --run-state "$RUN_STATE" \
  --live \
  --post state,session \
  --repair-dashboard

plan-tooling ledger-update \
  --execution-state "$PLAN_BUNDLE/$SLUG-execution-state.md" \
  --task "$TASK_ID" \
  --status done \
  --evidence "$LANE_PR_1"

plan-issue --format json tracking close-ready \
  --provider-repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --profile dispatch \
  --run-state "$RUN_STATE" \
  --linked-pr "$LANE_PR_1" \
  --linked-pr "$LANE_PR_2" \
  --approval "$APPROVAL" \
  --expect-visible

# Only after close-ready reports ready=true and blockers=[].
plan-issue --repo "$OWNER_REPO" --format json record close \
  --profile dispatch --issue "$ISSUE" \
  --linked-pr "$LANE_PR_1" --linked-pr "$LANE_PR_2" \
  --approval "$APPROVAL" \
  --add-label state::closed --remove-label state::needs-triage

forge-cli --provider "$PROVIDER" --repo "$OWNER_REPO" --format json issue view "$ISSUE" --with-comments \
  >"$CLOSED_ISSUE_VIEW_JSON"
jq '{body:.data.body, comments:(.data.comments // [])}' \
  "$CLOSED_ISSUE_VIEW_JSON" >"$CLOSED_ISSUE_JSON"
jq -r .body "$CLOSED_ISSUE_JSON" >"$CLOSED_ISSUE_BODY"

plan-issue --repo "$OWNER_REPO" --format json record audit \
  --profile dispatch \
  --body-file "$CLOSED_ISSUE_BODY" \
  --comments-json "$CLOSED_ISSUE_JSON" \
  --expect-visible
```

Replace `area::docs` with the dispatch plan's primary `area::` label.

## Workflow

1. **Preflight** — run `plan-tooling validate`; when resuming, also run
   `tracking status --profile dispatch --expect-visible`. Stop on stale
   or blocked state.
2. **Provider branch** — choose labels:
   - GitHub: `workflow::plan` + `workflow::dispatch`.
   - GitLab: `workflow::dispatch` + bare `plan`.
3. **Open / resume** — open or attach the shared dispatch issue, then run
   `tracking run init` with `--execution-state-file`.
4. **Lane execution** — assign each lane its exact scope, worktree, branch,
   run state, task packet, and `PLAN_BRANCH`. The lane executor implements,
   validates, creates the plan-branch PR, posts lane state/session/validation,
   and stops ready for independent review.
5. **Independent lane review** — a different reviewer runs the generic review
   outcome with retained evidence, posts provider review activity, and writes
   the lane review checkpoint. The lane executor never self-reviews.
6. **Orchestrator merge** — after approval and provider gates, the orchestrator
   merges the lane PR through `forge-cli pr merge
   --allow-non-default-base`. A reviewer does not merge.
7. **Dispatch checkpoints** — post plan-level state/session/validation/review
   only when orchestration truth changes across lanes.
8. **Ledger finalize branch** — before close-ready, patch any lane row not
   already updated by its lane executor.
9. **Read-back** — run `tracking status --profile dispatch
   --expect-visible` after dispatch checkpoints.
10. **Close-ready / closeout** — run the non-mutating close-ready gate. Stop on
    every blocker. On `ready: true`, write the closing summary, optionally
    repair only a stale dashboard, and call `record close --profile dispatch`.
11. **Closeout read-back** — fetch the closed provider issue with comments and
    run `record audit --profile dispatch --expect-visible`; stop unless the
    closeout role is visible and lint-clean.

## Boundary

Owns:

- Plan-level orchestration, lane assignment, integration judgement,
  dispatch dashboard freshness, approved lane integration, and strict closeout.

Must not:

- Implement lane tasks, let a lane executor review or merge its own PR, close
  with any blocker, merge PRs outside the active delivery workflow, or apply lightweight tracking
  closeout rules.

Internal phases:

- Open/resume, lane execution, lane PR creation, independent review,
  orchestrator merge, and closeout follow `references/outcome-routing.md`;
  they are not separate user choices.
