# Large PRs get reviewed forever and never converge to merge

## Status

- Status: open
- First observed: 2026-07-18
- Area: pr-delivery
- Severity: medium
- Cluster: async-bot-review-fix-loop
- Durable link: `https://github.com/sympoies/nils-cli/pull/1292`
- Lifecycle link: `https://github.com/graysurf/agent-runtime-kit/issues/673`

## Signal

On a large PR with an asynchronous bot reviewer, the deliver/merge loop fails to
*converge*. Each fix pass re-runs the review, the bot re-posts the same threads
(now duplicated), and outdated threads — whose anchored diff hunk no longer
exists — still count against the `unresolved_review_threads` merge gate. The PR
accumulates unresolved threads faster than they can be dispositioned and is
"reviewed forever, never merged". The `--allow-unresolved-threads` escape hatch
existed but took no recorded reason, so a bypass left no audit trail.

Reference symptom: sympoies/nils-cli#1272 — 89 unresolved threads, 38 of them
outdated, across 32 all-`COMMENTED` review generations, none converging.

## Evidence

- Raw record: not captured (diagnosed from the live PR state on
  sympoies/nils-cli#1272; thread and outdated counts read from the provider).
- The two sibling cases in this cluster
  (`error-inbox/archive/2026/deliver-pr-merge-misses-bot-review-threads/`,
  `error-inbox/archive/2026/review-cleanup-post-merge-review-recursion/`) fixed
  the deliver-time *timing* blind spot and the fix-loop *recursion*, but neither
  removed the two mechanical amplifiers above (duplicate re-posting and
  outdated-thread counting) nor made the bypass auditable.

## Impact

Large PRs stall at the review gate: reviewers churn, the merge gate never clears,
and a maintainer either force-bypasses without a recorded reason or abandons the
PR. It recurs on every large PR in a repo with an async bot reviewer, and the
silence of an unread bypass reads as "converged" when it was not.

## Current Workaround

Disposition every non-outdated thread by hand per
`core/policies/review-thread-convergence.md`, manually skip the outdated ones,
and — when the PR is not split — bypass with `--allow-unresolved-threads`,
previously with no recorded rationale. The durable fix is the mechanical
convergence levers in `forge-cli` (below) plus the work-tier "split what review
cannot converge" expectation now recorded in
`core/policies/work-tier-levels.md`.

## Promotion Criteria

Met when the mechanical levers ship in a released, pinned `forge-cli` and the
runtime-kit surfaces consume them. The levers landed on nils-cli main in
`sympoies/nils-cli` PR #1292: (1) cross-run idempotent native review posting
(`data.threads_skipped_idempotent`, never sweeps prior reviews); (2) outdated
unresolved threads auto-dispositioned `stale` at the merge gate
(`data.stale_thread_dispositions`) so only non-outdated threads block; and
(3) the `--allow-unresolved-threads` bypass now requires
`--allow-unresolved-threads-reason` (`data.unresolved_threads_override_reason`).
Runtime-kit wiring — the posting contract, the review-thread-convergence policy,
the work-tier split expectation, and this cluster's operation record — is
authored under tracker `graysurf/agent-runtime-kit#673`. Promotes to archived
once the coupled nils-cli release + pin bump (the tracker's gated Task 2.5)
lands and the runtime-kit wiring PR merges.

## Next Action

Release the coupled `forge-cli` and bump the runtime-kit nils-cli pin (tracker
#673, Task 2.5 — gated on explicit maintainer go-ahead), then merge the
runtime-kit wiring PR and compress this entry into the cluster's operation
record
`core/policies/heuristic-system/operation-records/async-bot-review-fix-loop/RECORD.md`.

## Related

- Cluster operation record:
  `core/policies/heuristic-system/operation-records/async-bot-review-fix-loop/RECORD.md`
- Sibling cases (archived under `error-inbox/archive/2026/`):
  `deliver-pr-merge-misses-bot-review-threads`,
  `review-cleanup-post-merge-review-recursion`
