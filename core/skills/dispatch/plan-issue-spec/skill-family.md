# Plan Issue Outcome Family Spec

## Status

- Status: implemented; canonical plan-issue outcome-family spec
- Date: 2026-07-11
- Depends on:
  - `core/skills/dispatch/plan-issue-spec/comment-taxonomy.md`
  - `core/skills/dispatch/plan-issue-spec/workflow.md`
  - `core/skills/dispatch/plan-issue-spec/run-state-controller.md`
  - `core/skills/dispatch/plan-issue-spec/cli.md`
- Owning implementation repos:
  - `sympoies/nils-cli`
  - `graysurf/agent-runtime-kit`

## Purpose

This document defines the two user-visible plan outcomes and their internal
phase boundaries. Users choose a complete lightweight tracking delivery or a
complete dispatch delivery. Opening, execution, review, PR handling, closeout,
and archive operations are internal phases selected by the parent outcome, not
separate skill choices.

`nils-cli` owns lifecycle mechanics, templates, run-state reconciliation,
checkpoint rendering, dashboard repair, close-ready gates, provider payload
privacy checks, and archive primitives. Runtime-kit outcome skills own scope,
judgement, ordering, delegation, and interpretation.

## Active Outcome Inventory

| Outcome | Source path | Profile |
| --- | --- | --- |
| `deliver-plan-tracking-issue` | `core/skills/dispatch/deliver-plan-tracking-issue/SKILL.md.tera` | `tracking` |
| `deliver-dispatch-plan` | `core/skills/dispatch/deliver-dispatch-plan/SKILL.md.tera` | `dispatch` |

Rendered product files and goldens are generated outputs. Refresh them after
source changes; do not hand-edit them as the source of truth.

## Shared Rules

Both outcomes follow these rules:

- Do not hand-compose or raw-post lifecycle comments.
- Use `plan-tooling` for plan bundle and task-ledger validation.
- Use `plan-issue record` for lifecycle record primitives.
- Use `plan-issue tracking` for run-state, status, checkpoint, and
  close-readiness behavior.
- Use `forge-cli` for provider issue and PR/MR lifecycle outside plan records.
- Reconcile provider evidence before mutation; local run state is not durable
  truth when the provider is newer.
- Keep source, plan, state, session, validation, review, and closeout roles
  within their declared single-writer phases.
- Provider-visible payloads must not contain raw machine-local home paths.
  Rewrite useful paths to `$HOME/...` and omit remote-useless local artifacts.
- Stop on stale state, visible-completeness failures, privacy failures,
  unresolved review gates, unchecked task items, or any close-ready blocker.
- Preserve independent review. Implementers do not approve or merge their own
  lane work.

## Lightweight Tracking Outcome

`deliver-plan-tracking-issue` owns one issue-backed L2 delivery from open or
resume through implementation, validation, PR delivery, review, merge, strict
closeout, and archive handoff.

Internal phases:

1. Validate the plan bundle.
2. Open or attach the tracking issue and initialize run state when absent.
3. Reconcile live issue evidence when resuming.
4. Implement and validate tasks; keep the task ledger current.
5. Deliver or adopt the linked PR without merging.
6. Run the generic specialist review outcome and post provider review activity
   through `forge-cli`; native combined approval requires an independent
   reviewer identity.
7. Resolve review threads and unchecked task items.
8. Post the issue-side review checkpoint, then merge through the active PR
   workflow.
9. Require `tracking close-ready --expect-visible` to return ready with no
   blockers before `record close --profile tracking`.
10. Read the closed issue back, audit visible evidence, and route archive
    discovery/migration dry-run first.

The parent may open a missing tracker, but it must not create a second tracker
for the same plan, use dispatch semantics, bypass independent review, or close
when any gate is incomplete.

Primary CLI surfaces:

```bash
plan-tooling validate ...
plan-issue record open|attach --profile tracking ...
plan-issue tracking run init|update ...
plan-issue tracking status|checkpoint|close-ready ...
forge-cli pr deliver|review|review-threads|tasks|merge ...
plan-issue record close|audit --profile tracking ...
plan-archive discover|migrate ...
```

## Dispatch Outcome

`deliver-dispatch-plan` owns one shared L3 dispatch issue from open or resume
through lane coordination, independent lane review, approved integration,
strict closeout, and provider read-back.

Internal phases:

1. Validate the plan bundle and open, attach, or reconcile the shared dispatch
   issue.
2. Initialize dispatch run state with the canonical execution-state file.
3. Assign each lane exact task scope, worktree, branch, plan branch, and task
   packet.
4. Lane executors implement, validate, create plan-branch PRs through
   `forge-cli`, and post only lane-scoped state/session/validation evidence.
5. Independent reviewers run the generic review outcome, post provider review
   activity, and write the lane review checkpoint.
6. The orchestrator alone merges approved lane PRs into the plan branch and
   updates plan-level integration truth.
7. Finalize every task-ledger row and post plan-level checkpoints only when
   orchestration truth changes.
8. Require `tracking close-ready --profile dispatch --expect-visible` to return
   ready with no blockers before `record close --profile dispatch`.
9. Read the closed issue back and audit visible evidence.

The parent must not implement lane work, let a lane executor self-review or
merge, use lightweight-tracking closeout rules, or create multiple shared
issues for one dispatch plan unless the user explicitly splits scope.

Primary CLI surfaces:

```bash
plan-tooling validate ...
plan-issue record open|attach --profile dispatch ...
plan-issue tracking run init|update ...
plan-issue tracking status|checkpoint|close-ready --profile dispatch ...
forge-cli pr deliver|review|merge ...
plan-issue record close|audit --profile dispatch ...
```

## Evidence And PR Boundaries

Evidence record types such as `review-evidence`, `test-first-evidence`, and
`web-evidence` are direct CLI/control-plane primitives. They do not appear as
skills and never post plan lifecycle comments by themselves.

`deliver-pr` is the single user-visible PR/MR delivery outcome. Plan outcomes
may call its underlying `forge-cli pr` lifecycle phases, but PR delivery does
not own plan dashboards, run state, checkpoints, or closeout.

## Validation

When either outcome changes:

1. Refresh Codex, Claude, and Hermes renders and goldens.
2. Run skill governance and exposure-contract validation.
3. Run deterministic dispatch and PR runtime smoke.
4. Run the full repository CI and hook suites.
5. Validate against the released nils-cli pin; do not replace the user-global
   CLI with an unreleased checkout during development.
