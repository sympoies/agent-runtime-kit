# Async Bot Review Threads Need A Converging, Deliver-Time Sweep Operation Record

## Status

- Date: 2026-06-16
- Status: active
- Cluster: async-bot-review-fix-loop
- Kind: cross-case compression rule over resolved cases
- Enforced-by: partial, and now mechanically wider — `forge-cli pr merge` fails
  closed on `unresolved_review_threads`, and two further levers narrow the
  by-hand surface: cross-run idempotent native review posting (a re-run on an
  unchanged head re-creates no duplicate threads and never sweeps prior reviews,
  reported as `data.threads_skipped_idempotent`) removes the fix-PR
  duplicate-thread growth; and outdated-thread auto-disposition (the merge gate
  records outdated unresolved threads as `stale` in
  `data.stale_thread_dispositions` and stops counting them, so only live
  non-outdated threads block). What still needs a future agent's hand is the
  per-finding fix / accepted / follow_up triage of the remaining non-outdated
  threads via `core/policies/review-thread-convergence.md`, so this stays active.
- System area: PR/MR delivery + review-thread cleanup across repos with async
  bot reviewers
- Durable fix paths:
  - `agent-runtime-kit` `core/policies/review-thread-convergence.md` (PR #407) —
    the provider-agnostic triage table + convergence/stopping rule.
  - `agent-runtime-kit` `core/skills/pr/review-thread-cleanup/SKILL.md.tera`
    (PR #412) — the shared orchestration skill over the read/write surfaces.
  - `sympoies/nils-cli` `forge-cli pr review-threads list/resolve/reply`
    (PR #883, #885; released `v1.9.1`) — the mechanics; `pr merge` keeps the
    `unresolved_review_threads` fail-closed gate.
  - `sympoies/nils-cli` `forge-cli pr review` / `pr merge` convergence levers
    (PR #1292) — cross-run idempotent native review posting, outdated→stale
    disposition at the `unresolved_review_threads` merge gate, and the
    required-reason `--allow-unresolved-threads` bypass; runtime-kit wiring under
    tracker `graysurf/agent-runtime-kit#673` (release + pin bump gated).
  - `sympoies/symphony-board` `review-candidates` CLI (PR #230) +
    `project-review-cleanup` reduced to a board-discovery adapter (PR #231).

## Signal

Two independently diagnosed, resolved cases share one root cause: an
allowlisted bot reviewer posts review activity *asynchronously* — often minutes
after PR creation and frequently after checks pass and the PR merges — so a
naive cleanup either misses the late threads or, when it does fix them, recurses
because the fix PR draws its own async bot review.

- `deliver-pr-merge-misses-bot-review-threads` (promoted): the deliver/close
  flow swept review threads only at creation time, so a bot review landing at
  the last action before merge left `unresolved_review_threads` undispositioned
  at merge.
- `review-cleanup-post-merge-review-recursion` (promoted): a mechanical
  "fix every new thread" sweep recurses across review generations on
  principled-but-imperfect code, or stops early and leaves a real bug — there
  was no convergence/stopping rule.

## Evidence

- Both sibling cases carry `Cluster: async-bot-review-fix-loop` and are promoted
  and archived under the 2026 inbox archive tree
  (`error-inbox/archive/2026/deliver-pr-merge-misses-bot-review-threads/`,
  `error-inbox/archive/2026/review-cleanup-post-merge-review-recursion/`).
- The resolution shipped across three repos this session under tracker
  `graysurf/agent-runtime-kit#408` (Sprints 0-4): policy #407, shared skill
  #412, forge-cli write surface #883/#885 (`v1.9.1`), board adapter #230/#231.

## Diagnosis

Async bot review is a two-headed hazard. First, *timing*: the review can arrive
at any point after creation, so a one-shot creation-time sweep is structurally
blind to it — the disposition gate has to run at the last action before merge,
which is exactly where `forge-cli pr merge`'s `unresolved_review_threads`
fail-closed check sits. Second, *recursion*: fixing a thread opens a fix PR that
the same bot reviews, so "fix every new thread" can loop across generations on
code that is principled but not bot-perfect, or terminate early and abandon a
real defect. Both heads need the same missing ingredient: a convergence
discipline that decides per-finding disposition (fix / stale / follow-up /
accepted) and a principled stopping rule, rather than per-case mechanical
chasing.

## Durable Fix

The individual fixes are landed and linked under Status. The reusable rule for
any repo with an async bot reviewer:

1. Sweep review threads at the **last action before merge**, not only at
   creation — `forge-cli pr merge` enforces this mechanically by failing closed
   on `unresolved_review_threads` (and `unchecked_task_items`).
2. Disposition every unresolved thread against
   `core/policies/review-thread-convergence.md`: `fix` genuine defects;
   `stale`/`follow_up` with a ref; `accepted` only with a recorded rationale,
   never to silence an unread/unverified finding. Always escalate major /
   high-risk findings to the user.
3. When threads cluster on one mechanism, prefer a single terminal/uniform rule
   over per-case special-casing; for an inherently-ambiguous key, pick the
   conservative branch once and document the tradeoff — converge the code
   instead of chasing each generation.
4. Stop once only preference or genuine-ambiguity threads on principled code
   remain (resolved `accepted` with rationale) — do not open another fix PR that
   would only draw another review.
5. Keep the layers separate: mechanics in `forge-cli pr review-threads`,
   judgment in the convergence policy, orchestration in the shared
   `review-thread-cleanup` skill, and board/candidate discovery in the consuming
   repo's own surface (e.g. `symphony-board review-candidates`) — `forge-cli`
   never learns about any board.

## Promotion Decision

Compressed per the Compression Rule: both source cases are resolved
(`promoted`, archived), share the `async-bot-review-fix-loop` root cause, and
span the two distinct sub-problems (deliver-time timing vs. fix-loop recursion)
that the same shared infrastructure now addresses. No `active` operation record
covered this cluster before (the two active records cover
`push-then-watch-stale-run` and `plan-issue-host-surface-drift`). The reusable
artifact is this convergence-and-deliver-time-sweep rule; the individual fixes
are landed and linked above.

## Validation

- Shared skill acceptance: the runtime-smoke `pr.review-thread-cleanup` probe
  (PR #412) dry-runs `list`/`resolve`/`reply` across providers and asserts the
  GitLab fail-closed (`provider_unsupported`) path and the documented surface.
- nils-cli `forge-cli pr review-threads` carries crate tests for the
  reply-then-resolve and provider-matrix behavior (#883/#885).
- Cross-repo read-only sweep smoke (tracker #408, Sprint 4.1): `review-candidates`
  surfaced candidates across two repos and `forge-cli pr review-threads list`
  verified live state, with the live read converging stale contract candidates.

## Retention

This record retains the cross-repo rule — sweep review threads at deliver time
under a convergence discipline, with mechanics/judgment/orchestration/discovery
kept in separate layers — so future repos with async bot reviewers can adopt
(and review) it without re-deriving the failure class from the two source cases.
