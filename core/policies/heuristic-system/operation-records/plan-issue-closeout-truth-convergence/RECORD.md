# Plan-Issue Closeout Must Converge On One Terminal Truth Operation Record

## Status

- Date: 2026-07-10
- Status: active
- Cluster: plan-issue-closeout-truth-convergence
- Kind: cross-case compression rule over resolved closeout cases
- Enforced-by: partial — `plan-issue tracking checkpoint --live`, `tracking
  close-ready --expect-visible`, and `record audit --expect-visible` enforce the
  terminal lifecycle shape, but provider/run-state reconciliation, irreversible
  mutation ordering, and repository execution-state synchronization still need
  operator judgment.
- System area: plan-issue tracking closeout; provider lifecycle truth;
  execution-state terminal synchronization
- Resolved source cases:
  - `tracking-closeout-review-state-complete-gap`
  - `plan-tracking-dashboard-stale-derivation`
  - `plan-issue-waived-closeout-status-mismatch`
- Open recurrence evidence:
  - `plan-issue-close-ready-validation-truth-mismatch`
  - `plan-issue-record-close-terminal-task-stale`
  - `plan-issue-record-close-label-partial-side-effects`
  - `plan-issue-dispatch-closeout-heading-contract-gap`

## Signal

Three independently resolved plan-tracking closeout cases shared one root
cause: terminal truth was split across the run state, provider lifecycle
comments/dashboard, repository execution-state Markdown, and the mutating close
command. Each surface could be internally valid while disagreeing with the
others at the exact close boundary.

- `tracking-closeout-review-state-complete-gap` showed that delivery omitted the
  `review` and `state=complete` records required by closeout. Live tracking
  checkpoints later made the upstream handoff mechanically postable.
- `plan-tracking-dashboard-stale-derivation` showed that a complete hidden
  payload could coexist with stale human-visible target/current/next fields.
  Renderer/controller fixes later derived those fields from terminal evidence.
- `plan-issue-waived-closeout-status-mismatch` showed `close-ready` and
  `record close` accepting different terminal task vocabularies. A shared
  terminal-status contract fixed the mismatch.

The class remains active. Current inbox cases show `close-ready` and
`record close` selecting different validation or review truth, successful close
leaving repository task/handoff fields actionable, and a late missing-label
failure occurring after the provider issue was already closed. These are
different symptoms of the same missing invariant: closeout must consume and
publish one normalized terminal state before any irreversible mutation.
The dispatch-heading recurrence adds another layer: a successful close can
emit a lifecycle comment that its own strict read-back contract rejects.

## Evidence

- Resolved cases are promoted and archived under
  `core/policies/heuristic-system/error-inbox/archive/2026/`.
- Current recurrence cases remain active under
  `core/policies/heuristic-system/error-inbox/` with provider repro links and
  promotion criteria.
- End-to-end exercise: `sympoies/agent-console#228`. Closeout docs PR #236
  deliberately retained Task 4.3 as in progress before merge; terminal-state
  PR #239 moved all eleven rows to done only after #236 merged. Installed macOS
  acceptance PR #241 then replaced the last human-interaction waiver and marked
  all review findings fixed.
- The final `tracking close-ready --expect-visible` returned `ready=true`,
  `RECORD_READY_FOR_CLOSE`, and no blockers. `record close` verified all six
  linked PRs, closed #228, and the post-close visible audit recognized all seven
  lifecycle roles. Its generated repository sync still left an actionable
  `Next task` and future-tense Task 4.3 note; PR #242 repaired both.
- The earlier #228 attempt also reproduced gate disagreement: close-ready
  passed while `record close` rejected two major residual review findings.
  `graysurf/plan-tracking-testbed#79` retains the upstream report.

## Diagnosis

Closeout is not one boolean transition. It joins four truth domains:

1. the authored plan ledger and execution-state file;
2. the local run controller's phase, validation, review, and linked PRs;
3. the provider's latest lifecycle-role comments and dashboard;
4. the mutating close command's issue, label, comment, and file-sync side
   effects.

If any gate reads only its nearest domain, it can return a convincing success
while another domain is stale. If the close command checks reversible
preconditions after irreversible provider mutation, its failure becomes
ambiguous: the operation reports an error even though the issue is already
closed. The durable prevention rule is therefore convergence and ordering, not
another per-field workaround.

## Durable Fix

For every plan-tracking closeout:

1. Do not mark the final task terminal before the PR that supplies its evidence
   has merged. Keep the repository file and provider state explicitly
   pre-terminal until that merge is provider-confirmed.
2. After all delivery PRs merge, author and merge one terminal execution-state
   transition. It must make every ledger row terminal, preserve waivers and
   open residuals, and remove actionable current/next/handoff prose.
3. Reconcile the run state to that merged reality, then post one live
   `state,session,validation,review` checkpoint with dashboard repair. Treat the
   provider's latest role per kind as the canonical close-ready input.
4. Run both non-mutating probes before close: `tracking close-ready
   --expect-visible` for lifecycle readiness and `record audit
   --expect-visible` for provider read-back. A pass from only one is not enough.
5. Preflight every requested label and other reversible provider prerequisite
   before the mutating close command. Never defer optional label discovery until
   after the issue/comment mutation.
6. Inspect any generated execution-state synchronization before committing it.
   Require terminal status, current task, next task, handoff, and merged PR
   fields to agree.
7. If close reports failure after any provider mutation, do not retry blindly.
   Read back issue state/comments/labels, rerun the visible audit, classify the
   exact missing side effect, and repair only that remainder.

## Promotion Decision

This record is warranted by the Compression Rule: three resolved, archived
cases cover distinct layers of the same terminal-truth divergence; no active
operation record covers plan-issue closeout convergence; and three active inbox
cases prove the class is recurring. The current session adds a validated
positive sequence rather than another error case, so the reusable artifact is
the cross-layer ordering rule, not a duplicate inbox entry.

`plan-issue-contract-drift-on-host-bumps` does not cover this class: it governs
binary/surface drift across host version changes, while this record governs
agreement between valid closeout surfaces at one installed version.

## Validation

- `sympoies/agent-console#228`: all eleven task rows terminal; PRs #235, #236,
  #238, #239, #241, and #242 merged; nils-cli PR #1093 merged/released; installed
  macOS WebView acceptance and user confirmation passed; issue closed with
  `state::closed`; post-close visible audit passed all seven roles.
- Resolved source cases each retain their shipped CLI/renderer/status-contract
  validation and lifecycle links in their archived `ENTRY.md` files.
- Current open siblings keep their own reproduction and promotion criteria;
  this operation record does not claim those defects are fixed.

## Retention

Keep this record active until one released close primitive normalizes the
run-state/provider/file inputs, preflights all reversible requirements before
mutation, and regression tests prove close-ready, close, read-back audit, and
terminal file sync agree. Until then, future agents must apply the convergence
sequence by hand.
