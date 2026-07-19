# Review Thread Convergence Policy

Portable, provider-agnostic policy for handling provider review threads — most
acutely the asynchronous bot reviewers (code-quality bots, the Codex connector,
and similar) that post review threads minutes after a PR/MR opens, and that
review *every* fix PR you open, including the fix PRs opened to clear earlier
threads.

## Read This When

Read this before or while dispositioning provider review threads: during a
`deliver-pr` pre-merge thread sweep, a review-cleanup sweep over already-merged
PRs, or any follow-up that opens fix PRs in response to review feedback. This is
the source of truth that review-cleanup-type skills reference — keep the rule
here and link to it rather than re-deriving it per skill.

## The Hazard

Fixing a review thread opens a fix PR. The async bot reviews that fix PR too. On
principled-but-imperfect code — especially an inherently-ambiguous heuristic
where no single special-case is fully sound — a mechanical "fix every new
thread" loop recurses across generations and may never converge; or it stops
early and leaves a genuine bug. The discipline below decides what to fix, how to
fix it so it converges, and when the sweep is done.

## Per-Finding Triage

Disposition every thread; classify each on two axes.

- Correctness: a genuine defect (wrong behavior, data loss, security, contract
  or schema break, a real edge-case bug that can actually occur), or a
  preference/structure/style remark on already-correct code?
- Relevance: does it touch business logic / observable behavior, or only
  internal mechanics or an inherently-ambiguous heuristic?

Route by classification:

| Classification | Disposition |
| --- | --- |
| Genuine defect | `fix` — make the repair and link the fix PR. Major/high-risk (security, data loss, contract break, destructive migration, cross-repo architecture) → stop and ask the user first. |
| No longer applies to the merged code | resolve as `stale`. `forge-cli pr merge` also auto-dispositions **outdated** unresolved threads as `stale` (recorded in `data.stale_thread_dispositions`), so those no longer block the merge gate. |
| Real but out of scope for this pass | `follow_up` — open/link a tracking issue. |
| Preference/style on principled, correct, business-logic-irrelevant code | `accepted` with recorded rationale. Do **not** open a fix PR. |
| Inherently-ambiguous edge case (e.g. a placeholder indistinguishable from real data) | pick the conservative/safe branch **once, uniformly**, document the tradeoff; do not chase per-case heuristics. |
| Several threads clustered on one mechanism | replace per-case special-casing with a single terminal/uniform rule, rather than patching each edge. |

## Convergence / Stopping Rule

The sweep is a loop over per-finding triage. It converges when the
genuine-defect set is empty:

1. Fix genuine defects (and escalate major/high-risk to the user).
2. When threads cluster on one mechanism, prefer a terminal/uniform design over
   per-case special-casing — converge the code instead of patching each edge.
3. Once only preference or inherently-ambiguous threads on principled code
   remain, resolve them as `accepted` with rationale and **stop** — do not open
   another fix PR that would only draw another review.

Expect each fix PR to draw a fresh post-merge review. That is normal; it is not
a signal to keep fixing. Converge, then stop.

## Concentrate vs Converge

- Concentrate (disposition every thread, fix every genuine defect): the
  pre-merge sweep of any PR with business-behavior, security, contract, or
  migration surface; and the *first* review generation of any fix PR, which can
  surface a real regression the fix introduced.
- Converge / stop (accept-with-rationale, do not recurse): Nth-generation
  post-merge reviews where the genuine-defect set is empty and only preference
  or inherently-ambiguous threads on principled code remain.

## Guard Rails

- `accepted` requires a recorded rationale and is reserved for *verified*
  preference or genuine ambiguity. It must never be used to silence an unverified
  or unread finding just to end the loop.
- Major/high-risk findings always escalate to the user; the stopping rule never
  overrides that.
- `safe_to_resolve` (mechanical safety of the provider mutation) is not a
  disposition. A safe thread still needs an explicit triage decision.

## Mechanics

Use released forge-cli surfaces, not raw `gh`/`glab`, where available:

- Discover threads: `forge-cli pr review-threads list <pr>` (provider-aware,
  read). Each `data.threads[]` entry carries the normalized `resolved` /
  `outdated` booleans (not GitHub's raw `isResolved` / `isOutdated`); filter on
  `resolved == false` for the unresolved set (or use the `data.unresolved`
  count). The merge gate blocks only on threads that are both `resolved == false`
  **and** `outdated == false`; outdated unresolved threads are auto-dispositioned
  `stale` (see the merge-gate bullet below).
- Resolve / reply (GitHub, released in forge-cli ≥ 1.9.1): reply-and-resolve in
  one call with `forge-cli pr review-threads resolve <pr> --thread <PRRT_…>
  [--note <reply>]`, resolve without a reply by omitting `--note`, or reply
  without resolving via `forge-cli pr review-threads reply <pr> --thread
  <PRRT_…> --body <text>`. All three return `provider_unsupported` on
  GitLab / Local; converge those threads through the provider surface.
- Merge gate: `forge-cli pr merge` fails closed on `unresolved_review_threads`,
  counting only threads that are both unresolved **and** not outdated. Outdated
  unresolved threads are auto-dispositioned `stale` and recorded in
  `data.stale_thread_dispositions` rather than blocking the merge — the anchored
  diff hunk no longer exists, so there is nothing left to converge. Bypass the
  remaining (non-outdated) block only with `--allow-unresolved-threads`, which
  now **requires** a paired `--allow-unresolved-threads-reason "<why>"`; the
  recorded rationale is surfaced as `data.unresolved_threads_override_reason`.
  Bypass only after each such thread is dispositioned.

## Consumers

Outcomes that drive a thread sweep should reference this policy rather than
restating it: the runtime-kit `deliver-pr` pre-merge sweep,
`code-review-specialists` follow-up mode, and project-local review-cleanup
outcomes such as symphony-board `project-review-cleanup`.
