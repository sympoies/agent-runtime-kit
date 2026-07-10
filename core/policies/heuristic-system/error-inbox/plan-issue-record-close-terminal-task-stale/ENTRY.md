# plan-issue record close leaves terminal task and handoff fields stale

## Status

- Status: open
- First observed: 2026-07-10
- Area: plan-issue record close; execution-state terminal sync
- Severity: medium

## Signal

Successful `record close --bundle` reported `execution_state_sync.changed=true`
and `followup_commit_required=true`, but its terminal rewrite patched only
`Status` and `Branch/commit/PR`. Across two closeouts, the durable
execution-state files retained pre-close actions in `Current task`, `Next task`,
or `Handoff` after their issues were closed.

## Evidence

- Raw record: not captured (manual diagnosis: terminal execution-state sync,
  2026-07-10).
- Installed surface: nils-cli / plan-issue `1.21.7`.
- Repro tracker: `sympoies/agent-console#217`; closeout PR
  `sympoies/agent-console#224`.
- `record close` produced a terminal sync with `Status: complete; tracking issue
  closed` and merged PR #224 while leaving the old actionable current task.
- The closed issue Final Dashboard already rendered `Current task: complete`,
  so the provider record and repository file contradicted one another.
- Testing and maintainability reviewers independently found the stale field.
  The manual repair landed in `sympoies/agent-console#225`.
- A second closeout, `sympoies/agent-console#216`, started with `Current task:
  none` but retained `Next task: run the strict tracking close-ready audit ...
  without closing it` and the matching pre-close `Handoff` after `record close`
  succeeded. The terminal record was repaired in commit `890ce27` before the
  closed bundle's archive dry-run.

## Impact

The tool explicitly requires committing its terminal sync, so future agents can
land a durable file that still presents completed closeout as pending. The
existing plan lint and visible lifecycle audit do not detect this cross-field
contradiction.

## Current Workaround

Inspect the generated execution-state diff before committing it. For a closed
tracker, require `Status: complete`, no pending action in `Current task` or
`Next task`, and a `Handoff` that describes the closed state rather than asking
for closeout; repair all stale terminal fields in the follow-up commit when
needed.

## Promotion Criteria

Promote when `record close` synchronizes terminal status, current task, next
task, handoff, and merged PR fields atomically, with regression tests that start
from actionable pre-closeout values in each field.

## Next Action

File an upstream nils-cli regression that requires record close to synchronize
Status, Current task, Next task, Handoff, and merged PR fields atomically.
