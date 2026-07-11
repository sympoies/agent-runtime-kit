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
- Installed surfaces: nils-cli / plan-issue `1.21.7` and `1.21.12`.
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
  succeeded. Despite an earlier local repair reference, `origin/main` still
  contained both stale fields when the closed issue was audited on 2026-07-11.
- The defect reproduced on `sympoies/agent-console#233` with plan-issue
  `1.21.12`: `record close --bundle` patched `Status`, `Last updated`, and
  `Branch/commit/PR`, but left `Current task` and `Next task` describing merge
  and closeout as future work after the issue was already closed.
- Agent Console PR #243 repaired the durable terminal fields for both #216 and
  #233 and merged as `94b3f42b`. Testing and maintainability follow-up passed;
  both plan bundles explicitly retain the user's no-archive override.
- Reproduced again on `graysurf/agent-runtime-kit#563` with plan-issue
  `1.21.15`: `record close --bundle` patched terminal status and merged-PR
  evidence but retained `Next task: run strict close-ready and canonical
  tracker closeout`. PR #566 repaired it to `Next task: none`. See
  `evidence/issue563-terminal-sync.md`.
- Reproduced again on `sympoies/agent-console#248` with plan-issue `1.21.16`:
  `record close --bundle` patched `Status` and `Branch/commit/PR`, but retained
  `Next task: canonical tracking-issue closeout` after it had already closed
  the tracker. Follow-up PR #252 committed the terminal-state repair after the
  post-close visible audit passed all seven lifecycle roles.

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
