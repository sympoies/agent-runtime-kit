# Discussion Source: Converge the deliver-pr review loop

## Trigger

On large PRs the delivery review gate can appear to "review forever / never
merge". The reference symptom is `sympoies/nils-cli#1272`: a still-draft,
+17k-line PR carrying 32 native reviews (all `COMMENTED`) from seven review
bot identities and 89 unresolved review threads (38 of them `outdated`). The
maintainer asked whether `deliver-pr` requires all reviews to pass before
merge, whether that can block merge indefinitely, and for an integrated fix.

## Findings

- The merge gate is owned by `forge-cli pr merge`, not an agent loop, and it
  does **not** require reviewer approval. It fails closed on: required checks
  not green (rule 8), a current-head native `CHANGES_REQUESTED` (rule 12, only
  when review-convergence is enabled — off by default), any unresolved review
  thread (rule 13, bot or human, `outdated` included), and unchecked task-list
  items (rule 14). Approval enforcement is delegated to provider branch
  protection.
- The "endless review" is self-inflicted, not an external bot watcher. There is
  no PR-review GitHub Action. The `review-*` / `dobi` identities are produced by
  an agent running the mandatory pre-merge `code-review-specialists` gate inside
  the delivery flow: each lens posts a native `COMMENT` review via
  `forge-cli pr review`, rewritten to a bot identity by a private router. The
  gate re-posts a fresh review and fresh inline threads on **every delivery
  run**, with within-run dedup only and **no cross-run idempotency**. Those
  threads then trip rule 13 on the next run. Fix a thread, push, re-run
  delivery, and the gate posts another round — threads accumulate faster than
  they converge, so a large PR never reaches zero unresolved threads.
- Posting native review events during delivery is a deliberate, maintainer-
  locked decision (the 2026-07-01 native-review-gate plan removed the single-
  author shortcut so every tracking PR posts native events). That decision is
  scoped to the **pre-merge point of one delivery pass**; "the same PR reviewed
  repeatedly across runs" is not modeled anywhere. Cross-run idempotency was
  never considered — an unhandled gap, not a rejected design. The posting
  contract forbids sweeping or deleting prior reviews, so the fix must be "do
  not create a duplicate", never "delete what a previous run posted".
- The normalized review-thread envelope already carries `resolved` and
  `outdated` booleans, but the convergence discipline
  (`core/policies/review-thread-convergence.md`) requires every thread to carry
  an explicit disposition and states that mechanical safety is not a
  disposition. So outdated threads cannot be silently ignored at the gate; they
  can be mechanically dispositioned as `stale` with a recorded rationale, which
  is a valid disposition.
- `--allow-unresolved-threads` is a bare boolean flag with no required reason,
  unlike `--allow-unchecked-tasks` which requires
  `--allow-unchecked-tasks-reason`. The "record the rationale" rule for the
  sanctioned bypass exists only as prose, not as a mechanical audit.
- This is the same family as the active operation record
  `async-bot-review-fix-loop`, whose `Enforced-by` is `partial`: the merge-time
  thread sweep is mechanical, but the convergence/triage judgment is still a
  hand-applied discipline. The standalone `pr.review-thread-cleanup` skill named
  in that record has since been retired into `deliver-pr` as an internal phase.
- `forge-cli-deliver-zero-required-skips-pending-checks` (nils-cli #1132) is a
  separate, already-open error-inbox entry: a check-gate premature-success on
  repos with zero required checks. It is orthogonal to the review loop and is
  linked, not re-created.

## Decisions

1. Keep the mandatory pre-merge specialist gate and native review posting; the
   fix does not weaken "the outcome must exist before merge" or "post the moment
   a lens returns within a run". The primary lever is **cross-run idempotency**,
   not skipping the gate.
2. **L1 (primary):** make native review posting idempotent across runs. On an
   unchanged head, an existing open thread for a finding fingerprint is not
   re-created and an equivalent submitted review is not re-posted. Prior reviews
   are never swept or deleted. This is a forge-cli capability plus the
   agent-runtime-kit posting-contract wording that consumes it.
3. **L2 (folded into L1):** the draft-run waste on #1272 is mostly repeated
   end-to-end runs; cross-run idempotency subsumes it. Keep only a light
   contract note that advisory review on a draft does not post native events
   before the pre-merge point. No draft-aware skip that contradicts the
   "mandatory gate for every delivery PR" language.
4. **L3:** at rule 13, `outdated` threads are mechanically dispositioned as
   `stale` with a recorded rationale rather than silently ignored, so the
   convergence discipline (every thread dispositioned) still holds.
5. **L4:** mechanize the bulk stale/preference disposition inside the delivery
   cleanup phase / forge-cli, not as a revived standalone skill (that skill is
   retired). This moves the `async-bot-review-fix-loop` hand-applied judgment
   toward mechanical enforcement.
6. **L5:** add `--allow-unresolved-threads-reason`, required whenever
   `--allow-unresolved-threads` is set, recorded in the merge payload — the
   sanctioned exit gains a mechanical audit trail, mirroring the task bypass.
7. **L6:** state a work-tier / large-PR splitting expectation so a change the
   size of #1272 is split into reviewable, convergeable units instead of one
   giant PR that guarantees thread explosion.
8. Record the workflow gap as an open error-inbox case with
   `Cluster: async-bot-review-fix-loop`, cross-linking the active operation
   record and its two archived siblings, and reflect the advanced mechanical
   enforcement in the operation record.

## Scope

- In scope: forge-cli convergence capabilities (idempotent review posting,
  outdated→`stale` disposition, `--allow-unresolved-threads-reason`, bulk
  disposition) and their tests; agent-runtime-kit posting-contract and delivery
  wiring, work-tier policy, render/golden/smoke refresh, the coupled nils-cli
  surface/pin integration required to consume the released behavior, and the
  heuristic-system case + operation-record update.
- Out of scope: removing the mandatory gate, skipping review on drafts in a way
  that contradicts the pre-merge mandate, deleting or sweeping prior submitted
  reviews, changing provider branch protection, the orthogonal #1132 check-gate
  fix (tracked separately), and applying the finished runtime surfaces to live
  Codex/Claude homes.

## Deployment boundary

Implementation, review, provider delivery, the required nils-cli release/pin
convergence, and deploy-readiness validation belong to this L2. Applying the new
managed runtime surfaces to live runtime homes is a separate final step and
needs fresh explicit maintainer approval after deploy readiness is proven. The
nils-cli release is the heaviest commitment and is gated in Sprint 2.

## Execution

- Recommended plan: docs/plans/2026-07-19-review-loop-convergence/review-loop-convergence-plan.md
- Recommended execution state: docs/plans/2026-07-19-review-loop-convergence/review-loop-convergence-execution-state.md
