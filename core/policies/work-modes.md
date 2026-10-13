# Work Modes

## Purpose

Required delivery decision boundary: choose the lightest durable tracking that
holds the work's actual state. Keep routine `direct` classification internal.
Surface a mode only for provider artifacts, delivery, or material ambiguity.
Tracking, execution (`inline` / subagents), and risk-selected review are separate
axes; a tracking choice never grants authority or reduces review depth.

## Tracking Decision

| Mode | Durable record | Trigger and owner |
| --- | --- | --- |
| `direct` | None beyond the answer or authorized PR | Work finishes now without another timeline; start here |
| `issue` | One provider issue and comment timeline | Deferral, unknown fix/investigation, recorded blocker, handoff, cross-session continuity/visibility, or recurring loop; `issue-follow-up` |
| `program` | Tracker plus at least two independently deliverable/reviewable child issues | Two or more units AND dependencies, cross-repo scope, phase authority gates, or work expected to outlive a session; `issue-follow-up` program mode |
| `program/dispatch` | Program records and shared integration branch | Intermediate lanes cannot land independently; `deliver-dispatch-plan` |

Size alone does not escalate tracking. Split an unconvergeable review surface
into reviewable PRs in the same mode. When torn between issue and program,
choose issue. Re-triage as evidence changes, preserve completed work, and
reduce tracking when its need shrinks. A program with one remaining child
closes its tracker under the closeout rules and continues in issue mode.

Classifying is autonomous. Creating provider artifacts or materially ambiguous
escalation needs the user's decision unless already authorized by the current
request/workflow. Name the required durable state and recommend the lightest
safe option. Do not manufacture a tracker for ordinary work or a capture exit.
Subagents are execution, not tracking: existing issues retain their mode.

## Delivery And Review Boundaries

- `direct` uses a PR only when provider delivery is explicitly requested or
  already owned by an approved workflow. PR/MR is the default provider route;
  implementation alone does not authorize it.
- Direct-main and one local-only default-branch commit are `direct`-only,
  exact current-task exceptions. Signing, managed-worktree authoring, receipts
  and provider proof follow [Git delivery](git-delivery.md).
- `deliver-pr` selects the smallest safe pre-merge review. Eligible direct or
  issue diffs (including program children) may use a clean quick pass for that
  head. Risk triggers, unresolved review state, insufficient reviewer confidence
  or program/dispatch require full review. Escalating depth never changes mode.
- Program trackers stay open until children are closed or explicitly moved,
  decisions are canonised, and a final checkpoint is posted. Child delivery
  follows issue mode; tracker dependencies come from phase rows, never a
  separately edited graph. Public children contain generic program keys rather
  than private identities or topology. Read
  [program record operations](references/work-modes.md#program-records) when
  authoring or closing those records.

## Capture Lifecycle

An implementation-readiness capture is an optional spec, never a tracking mode.
`docs/discussions/` is staging. Choose its `Exit:` when writing it and execute
that exit in the shipping PR: `open-issue` then delete, `canonise` by moving to
its durable owner, or `retire` by deletion. There is no keep state. For mixed
canon/backlog, promote the durable half and record the remainder before deletion.

Nothing outside the directory may link to an individual capture; bare directory
mentions and its own index are exempt. Provider history alone cannot justify
retirement: reasoning must first live in repository canon or its development
log (add a log before retiring captures if absent). If the provider cannot
accept the outstanding-work record, retain the staged capture until a valid
exit. Read [capture operations](references/work-modes.md#capture-lifecycle)
when capturing, promoting, or retiring a spec.

## On-Demand Owners

- [Record operations and examples](references/work-modes.md): tracker/child
  fields, dependency grammar, checkpoints, closeout and capture exits.
- `issue-follow-up`: ordinary issues and program records; `deliver-dispatch-plan`:
  integrated lanes; `discussion-to-implementation-doc`: captures.
- [Review convergence](review-thread-convergence.md): accumulated review threads.
- [Git delivery](git-delivery.md) and `deliver-pr`: commit/provider lifecycle;
  [label taxonomy](forge-label-taxonomy.md): record labels.
