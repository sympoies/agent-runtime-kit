# plan-issue record close leaves Current task stale in terminal execution state

## Status

- Status: open
- First observed: 2026-07-10
- Area: plan-issue record close; execution-state terminal sync
- Severity: medium

## Signal

Successful `record close --bundle` reported `execution_state_sync.changed=true`
and `followup_commit_required=true`, but its terminal rewrite patched only
`Status` and `Branch/commit/PR`. The durable execution-state file still said
`Current task: run the close-ready audit and tracker closeout` after the issue
was closed.

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

## Impact

The tool explicitly requires committing its terminal sync, so future agents can
land a durable file that still presents completed closeout as pending. The
existing plan lint and visible lifecycle audit do not detect this cross-field
contradiction.

## Current Workaround

Inspect the generated execution-state diff before committing it. For a closed
tracker, require `Status: complete`, `Current task: complete`, and `Next task:
none`; repair the current-task field in the same follow-up PR when needed.

## Promotion Criteria

Promote when `record close` synchronizes the terminal status, current task, next
task, and merged PR fields atomically, with a regression test that starts from
an actionable pre-closeout `Current task` value.

## Next Action

File an upstream nils-cli regression that requires record close to synchronize Status, Current task, Next task, and merged PR fields atomically.
