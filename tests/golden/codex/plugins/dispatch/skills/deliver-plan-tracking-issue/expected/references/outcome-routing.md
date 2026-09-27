# Plan Outcome Routing

The public plan surface has two outcomes. Both are specializations of the
`program` tracking mode in `core/policies/work-modes.md`:

- `program/plan` is one issue-backed plan whose frozen plan lives in the
  repository.
- `program/dispatch` is a plan split into independent lanes that integrate on
  a shared plan branch.

Plain `program` is the default for large work: a tracker issue plus child
issues through the `issue-follow-up` program mode. Choose a specialization only
when its requirement below applies.

Creation, execution, lane PR creation, review, checkpoint, merge, closeout, and
archive operations are internal phases. Their write authorities remain distinct
even when they are no longer separate user-selected skills.

## When A Specialization Is Required

| Specialization | Required when | Otherwise use |
| --- | --- | --- |
| `program/plan` (`deliver-plan-tracking-issue`) | The frozen plan must live in the repository as a drift-checked plan bundle with a task ledger and archive handoff. | Plain `program` |
| `program/dispatch` (`deliver-dispatch-plan`) | Lanes must integrate on a shared plan branch before main, because intermediate lane states cannot land on main one by one. | Plain `program`, with one child issue per independently landable unit |

## Plan Tracking Outcome (`program/plan`)

The plan parent:

1. validates and opens or resumes one tracker;
2. initializes and reconciles run state;
3. delivers its PR;
4. invokes independent read-only review;
5. records final evidence;
6. merges only after gates pass;
7. closes through the strict close-ready path;
8. then offers archive maintenance.

It never uses dispatch lane semantics.

Outside Main Agent Mode, the plan parent remains the implementation writer.

When the user explicitly activates Main Agent Mode, one assigned managed worker
becomes the plan implementation writer in an isolated managed worktree with
coordination enforcement. In that case:

- The plan parent remains the owner of plan/run-state, review, acceptance,
  merge, closeout, and the user conversation.
- It does not implement or repair production or test code.
- Findings return to the same worker unless the parent records an explicit
  reassignment.

## Dispatch Outcome (`program/dispatch`)

The dispatch parent:

1. opens or resumes one shared dispatch issue;
2. assigns exact lane scope;
3. waits for lane PR delivery;
4. routes each PR to an independent reviewer;
5. integrates only approved lanes;
6. closes only after every lane and integration gate passes.

A lane executor stops after PR creation and lane-scoped
state/session/validation checkpoints. It never reviews or merges its own PR.

Main Agent Mode does not change the tracking mode. Existing exact lane workers
remain the implementation writers, and the orchestrator retains the acceptance
boundary.

## Lifecycle Writers

| Lifecycle role | `program/plan` writer | `program/dispatch` writer |
| --- | --- | --- |
| Source, plan, initial state | Plan parent open phase | Dispatch orchestrator open phase |
| Task implementation checkpoint | Plan parent execution phase; assigned managed worker only in explicit Main Agent Mode | Assigned lane executor, lane scope only |
| Provider PR creation | Plan parent delivery phase; assigned managed worker may create/update its delivery artifact in explicit Main Agent Mode | Assigned lane executor, plan branch only |
| Review provider post and issue review role | Plan independent review phase | Independent lane reviewer |
| PR merge | Plan parent after review and sweeps | Dispatch orchestrator after independent approval |
| Plan-level state/session/validation | Plan parent | Dispatch orchestrator |
| Closeout | Plan parent closeout phase after close-ready | Dispatch orchestrator closeout phase after close-ready |

No phase hand-composes lifecycle comments or writes through a generic provider
issue-comment command. The write owners are:

- `plan-issue tracking`: run-state reconciliation and checkpoints.
- `plan-issue record`: open/close primitives.
- `plan-tooling`: bundle and ledger updates.
- `forge-cli`: provider PR operations.

## Stop Conditions

Stop on any of the following:

- stale run state
- blocked records
- visible-completeness failures
- privacy payload rejection
- unresolved review findings or threads
- unchecked task items
- pending ledger rows
- missing approval
- any close-ready blocker

A parent may repair only the role set that the controller explicitly reports as
repairable. It never infers readiness from prose.
