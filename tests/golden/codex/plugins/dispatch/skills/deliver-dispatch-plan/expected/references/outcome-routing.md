# Plan Outcome Routing

The public plan surface has two outcomes: one L2 tracking outcome for a single
issue-backed plan, and one L3 dispatch outcome for a plan split into independent
lanes. Creation, execution, lane PR creation, review, checkpoint, merge,
closeout, and archive operations are internal phases. Their write authorities
remain distinct even when they are no longer separate user-selected skills.

## L2 Tracking Outcome

The L2 parent validates and opens or resumes one tracker, initializes and
reconciles run state, executes the selected task scope, delivers its PR, invokes
independent read-only review, records final evidence, merges only after gates
pass, closes through the strict close-ready path, and then offers archive
maintenance. It never uses dispatch lane semantics.

## L3 Dispatch Outcome

The L3 parent opens or resumes one shared dispatch issue, assigns exact lane
scope, waits for lane PR delivery, routes each PR to an independent reviewer,
integrates only approved lanes, and closes only after every lane and integration
gate passes. A lane executor stops after PR creation and lane-scoped
state/session/validation checkpoints. It never reviews or merges its own PR.

## Lifecycle Writers

| Lifecycle role | L2 writer | L3 writer |
| --- | --- | --- |
| Source, plan, initial state | L2 parent open phase | L3 orchestrator open phase |
| Task implementation checkpoint | L2 parent execution phase | Assigned lane executor, lane scope only |
| Provider PR creation | L2 parent delivery phase | Assigned lane executor, plan branch only |
| Review provider post and issue review role | L2 independent review phase | Independent lane reviewer |
| PR merge | L2 parent after review and sweeps | L3 orchestrator after independent approval |
| Plan-level state/session/validation | L2 parent | L3 orchestrator |
| Closeout | L2 parent closeout phase after close-ready | L3 orchestrator closeout phase after close-ready |

No phase hand-composes lifecycle comments or writes through a generic provider
issue-comment command. `plan-issue tracking` owns run-state reconciliation and
checkpoints, `plan-issue record` owns open/close primitives, `plan-tooling` owns
bundle and ledger updates, and `forge-cli` owns provider PR operations.

## Stop Conditions

Stop on stale run state, blocked records, visible-completeness failures, privacy
payload rejection, unresolved review findings or threads, unchecked task items,
pending ledger rows, missing approval, or any close-ready blocker. A parent may
repair only the role set explicitly reported as repairable by the controller;
it never infers readiness from prose.
