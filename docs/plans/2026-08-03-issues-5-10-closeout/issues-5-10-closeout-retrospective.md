# Retrospective: Close issues #5–#10 (delivery-path guard, governed push surfaces, review-loop ledger)

## Overview

Issues #5–#10 were filed as one cluster from a single painful delivery
(`serenvia/agent-console#377`): a managed worktree whose branch tracked `main`,
a guard that blocked `git merge --ff-only` while admitting `git pull`, no
governed surface for a branch push or a default-branch sync, a `deliver-pr`
skill that predated the `forge-cli` review-loop ledger, an `observe` call with no
faithful preflight, and guard messages that named policy instead of the tripped
rule.

**The headline finding of this analysis: five of the six are already
substantially delivered.** PR #11 (`abfbb16e`) resolved #6 and #10 in the hook,
PR #12 (`db0d5109`) resolved #8 in the `deliver-pr` skill, and released nils-cli
**v1.25.13** — which this repo pins as *both* `minimum_supported_tag` and
`validated_tag` — ships the `git-cli push` / `git-cli sync-default` surfaces
(#7) and the faithful `review-loop observe --dry-run` plus documented
`--findings-file` schemas (#9). All six issues are nonetheless still open, with
no closure evidence recorded.

So this is **not a six-issue implementation plan**. It is a verification,
residual-gap, and closeout plan with exactly one substantive code/doc lane
(`Lane B`), one policy-record lane (`Lane C`), and two evidence-only lanes that
can run immediately and in parallel. The single genuine functional gap found is
that the merge-owning delivery skills still say *"repair, then push"* without
naming `git-cli push` — the same skill-versus-guard drift class that #8 was
about, now pointing at the surface PR #11's remedy text mandates.

## Read First

- Issues: `sympoies/agent-runtime-kit#5`, `#6`, `#7`, `#8`, `#9`, `#10`
- Landed work under verification: PR #11 (`abfbb16e`), PR #12 (`db0d5109`)
- Guard under test: `core/hooks/shared/block-unsafe-default-delivery.py`
  (module docstring lines 14–34 state the resolution actually chosen)
- Runtime policy: `core/policies/git-delivery.md` (mutation-ownership table,
  rows for `git-cli push` and `git-cli sync-default`)
- Skill under repair: `core/skills/pr/deliver-pr/SKILL.md.tera`
- Guard tests: `tests/hooks/test_shared_hooks.py`
- Open error-inbox entries describing the pre-#11 behavior:
  `core/policies/heuristic-system/error-inbox/push-guard-fails-closed-on-compound-command/`,
  `core/policies/heuristic-system/error-inbox/managed-worktree-lockout-pushguard-ssh/`
- Version floor: `docs/source/nils-cli-pin.yaml`
- Coupled CLI owner for #5/#7/#9 behavior: `sympoies/nils-cli`
- Placement rule for this bundle:
  `docs/source/docs-placement-retention-policy-v1.md`

## Current State Per Issue

Verified against the pinned host (`git-cli`/`forge-cli` 1.25.13) and `main` at
`db0d5109`.

| # | Area | Status | Evidence |
| --- | --- | --- | --- |
| 5 | `area::cli` | **Fixed upstream** — verify + close | `git-cli worktree add` now leaves the branch with *no* upstream (`branch.<slug>.remote` and `.merge` both empty), so the `merge = refs/heads/main` symptom is gone; `git-cli push` sets the upstream to the branch's own ref on first publish |
| 6 | `area::hooks` | **Delivered by #11** — verify + close, *resolution differs from the proposal* | `pull` is in `GIT_DEFAULT_BRANCH_REWRITE_COMMANDS`; tests `..._blocks_a_pull_that_can_author_a_commit`, `..._routes_raw_fast_forward_to_sync_owner`, `..._blocks_fast_forward_onto_unpublished_work` |
| 7 | `area::cli` | **Surfaces shipped; consumer layer partly aligned** — one real gap | `git-cli push` and `git-cli sync-default` exist in 1.25.13; `core/policies/git-delivery.md` carries both ownership rows; **but no skill names `git-cli push`** |
| 8 | `area::skills` | **Delivered by #12** — verify + close | `SKILL.md.tera` has the Review-Loop Ledger section, the append order, both `--findings-file` shapes, prereq raised to 1.25.13 |
| 9 | `area::cli` | **Asks 1 and 3 delivered; ask 2 open** — needs a decision | `observe --help` footer documents APPEND ORDER, both payload shapes, the `<category>:<component>:<invariant>` fingerprint form, the disposition enum, and a faithful `--dry-run` reporting `data.preflight[]`; no `observe validate` / `--validate-only` subcommand exists |
| 10 | `area::hooks` | **Delivered by #11 — all four asks** — verify + close | `MARK_BLOCKED` / `MARK_UNVERIFIED` (ask 3); `REMEDY_FEATURE_PUSH`, `REMEDY_SYNC_DEFAULT`, `REMEDY_SHELL_CONTEXT` (asks 1–2); a worked `Example:` inside each remedy (ask 4); tests `..._marks_blocked_apart_from_unverified`, `..._offers_a_remedy_for_the_actual_operation` |

### Two findings that must be stated on the issues, not silently closed

1. **#6 was resolved differently than proposed.** The issue asked that a provable
   fast-forward on the default branch be *allowed*. The hook instead **refuses
   raw `merge`/`pull` even with `--ff-only`** and routes the operation to
   `git-cli sync-default`, on the stated ground that remote-tracking refs and
   local pull sources cannot *prove* publication from local state
   (`block-unsafe-default-delivery.py` lines 14–17). The issue's actual bug — the
   subset blocked while the superset passed — is fixed. The closure comment must
   record the substitution rather than imply the proposal was adopted.

2. **#9 ask 2 is genuinely undelivered and is a judgment call.** The faithful
   `--dry-run` now performs the payload validation, head CAS, and state-tip CAS
   without appending, and its help footer explicitly recommends it to "check a
   findings file without writing durable provider-visible state." That covers the
   *need* behind ask 2 (learn the schema without a provider write). Whether a
   separate `validate` subcommand is still wanted is an upstream API-shape
   decision, and this repo does not own it.

## Scope

- **In scope**: verification evidence and closure for #5, #6, #8, #10; naming
  `git-cli push` as the branch-publish surface in the merge-owning delivery
  skills and closing #7 on that; converging the two open error-inbox entries that
  document the pre-#11 behavior; an explicit disposition for #9 (close as
  superseded, or re-file ask 2 in `sympoies/nils-cli`).
- **Out of scope**: any change to `sympoies/nils-cli` source (this repo consumes
  a pinned release, it does not implement it); moving the nils-cli pin;
  re-litigating the #6 fast-forward decision that #11 already settled; the ~40
  stale managed worktrees on this checkout (real hygiene debt, but unrelated —
  `meta:worktree-triage` owns it).

## Assumptions

1. v1.25.13 being *both* minimum and validated in `docs/source/nils-cli-pin.yaml`
   means every host running this repo's gates has `git-cli push`,
   `git-cli sync-default`, and the faithful `observe --dry-run`. Consumer docs
   may therefore name them unconditionally, with no capability fallback.
2. Closing a `area::cli` issue in this repo on the strength of a released
   upstream fix is correct when the pinned floor guarantees the fix; the durable
   record belongs in the closure comment, not a new in-repo document.
3. Lane B's skill edit requires a render-golden refresh, so it is the only lane
   that writes under `tests/golden/`. Three product trees are gated, not two:
   `codex`, `claude`, **and `hermes`** (gate position 4). Gate position 6 runs
   `--update-golden` and then requires `git diff --exit-code tests/golden/`, so
   the goldens must be committed for the gate to pass — refreshing them in the
   working tree is not enough.
4. `core/skills/pr/deliver-pr/references/pr-lifecycle.md` is a **packaged mirror**
   of the canonical `core/skills/pr/pr-lifecycle/README.md`, and
   `skill-governance-audit` fails when they diverge. Any shared-rule edit must
   touch both.

## Lane A — Verification and closeout for #5, #6, #10 *(evidence only)*

**Goal**: #5, #6, and #10 are closed with reproducible evidence, and #6's
substituted resolution is on the record.

**Work**:
1. Re-run the #5 probe through governed surfaces only: `git-cli worktree add`
   a throwaway slug, assert `branch.<slug>.remote`/`.merge` are empty,
   `git-cli worktree remove` it.
2. Run the guard's default-delivery tests and capture the three #6 test names
   and two #10 test names as the closure evidence.
3. Comment and close #5, #6, #10. The #6 comment states the
   route-to-`sync-default` substitution and why (`--ff-only` cannot prove
   publication from local state).

**Validation**: `pytest tests/hooks/test_shared_hooks.py -k default_delivery`

**Touches**: no tracked files. Fully parallel-safe.

## Lane B — Name `git-cli push` in the merge-owning delivery skills *(the one substantive lane)*

**Goal**: an agent following a delivery skill reaches for the same surface the
guard demands, so the repair-and-push step cannot dead-end in a refusal.

**Work**:
1. In `core/skills/pr/deliver-pr/SKILL.md.tera`, replace the unqualified
   "repair, then push" / "after the repair is pushed" steps with the governed
   surface: `git-cli push --format json`, noting it pins the refspec and refuses
   the default branch. The ledger ordering from #12 is already correct and must
   not be disturbed — only the push step gains an owner.
2. Sweep the other merge-owning delivery workflows (`dispatch/`,
   `conversation/main-agent-mode`) for the same unqualified push step and give
   them the same owner.
3. Add `git-cli sync-default` as the post-merge local-sync step wherever a
   workflow tells the agent to catch `main` up after a merge.
4. Refresh render goldens for every affected product.
5. Close #7, citing the shipped surfaces plus this consumer alignment.

**Validation**:
- `agent-runtime render --product codex` and `--product claude` (clean, then
  `--update-golden` when the change is intended)
- `bash scripts/ci/all.sh`

**Touches**: `core/skills/**`, `tests/golden/**`. **This is the only lane that
writes render goldens.**

## Lane C — Converge the two open error-inbox entries *(disjoint subtree)*

**Goal**: the heuristic error inbox stops advertising a failure mode the runtime
no longer has.

**Work**:
1. `push-guard-fails-closed-on-compound-command` (open, 2026-07-25, medium):
   the compound `cd <worktree> && git push` shape is now answered by
   `REMEDY_SHELL_CONTEXT` plus `git-cli push`. Record the resolution and the
   owning change (#11 + 1.25.13), then move it to `error-inbox/archive/2026/`.
2. `managed-worktree-lockout-pushguard-ssh` (open, 2026-07-17, **high**):
   resolve only the push-guard component; the deletions-first lockout and
   slow-SSH components are separate and must be re-triaged, not archived by
   association. Split or annotate rather than closing wholesale.

**Validation**: `bash scripts/ci/all.sh` (heuristic/plan governance positions)

**Touches**: `core/policies/heuristic-system/error-inbox/**` only. No render.
Parallel-safe with Lane B.

## Lane D — Close #8, dispose of #9 *(evidence only, one decision)*

**Goal**: #8 closed on #12's evidence; #9 has an explicit, recorded disposition.

**Work**:
1. Verify `SKILL.md.tera` against #8's four asks (observe step in position, both
   constraints stated inline, both payload shapes documented, prereq raised) and
   close #8.
2. **Decision required** — #9 ask 2 (`observe validate` / `--validate-only`):
   - *Option 1 (recommended)*: close #9 as delivered-with-substitution, recording
     that the faithful `--dry-run` covers the validate-without-writing need.
   - *Option 2*: close asks 1 and 3 here and re-file ask 2 as an API-shape
     request in `sympoies/nils-cli`, where the surface is owned.

**Touches**: no tracked files. Fully parallel-safe.

## Ordering And Parallel Assignment

```
Lane A  (verify #5/#6/#10)  ─┐
Lane D  (close #8, decide #9)─┼─ start immediately, no file conflicts
Lane C  (error-inbox)        ─┘   (C commits; A and D do not)
Lane B  (skills + render) ────── the only render-conflicting lane
                                  #7 closes only after B lands
```

- **Only two ordering constraints exist**: #7 cannot close until Lane B lands,
  and Lane C's archival of `push-guard-fails-closed-on-compound-command` should
  cite Lane B's consumer alignment, so C's *commit* is best sequenced after B's
  content is settled (C can be drafted in parallel and rebased).
- **The conflict surface is `tests/golden/`**, not `targets/` — `targets/` holds
  product adapter source, which no lane here edits. Goldens are regenerated
  wholesale across all three product trees, so two sessions editing any skill
  source will collide there. Lane B must be the sole owner of skill edits for the
  duration.
- **Lanes A and D touch no tracked files at all** — they produce issue comments
  and closures. They are safe to hand to a parallel session with no coordination
  beyond "do not close #7."

### Recommended split

| Session | Lanes | Why it is safe |
| --- | --- | --- |
| This session | **B** | Owns all skill edits and the sole render-golden refresh; runs the full gate |
| Parallel session 1 | **C** | `error-inbox/**` only — disjoint from `core/skills/**` and `targets/**`; no render |
| Parallel session 2 | **A + D** | Zero tracked-file writes; evidence gathering and issue closure only |

Each committing lane (B, C) delivers on its own managed-worktree branch as a
separate PR. Lanes A and D need no branch.

## Risks

- **Closing an `area::cli` issue without an in-repo change looks like a silent
  drop.** Mitigation: every such closure (#5, #7, #9) cites the released version
  and the pinned floor that guarantees it.
- **#6's substituted resolution could read as the proposal having been adopted.**
  Mitigation: Lane A's closure comment states the substitution explicitly.
- **Archiving `managed-worktree-lockout-pushguard-ssh` wholesale would bury two
  unresolved high-severity components.** Mitigation: Lane C resolves only the
  push-guard component.
- **Lane B is a docs-shaped change to a merge-owning skill**, so an error there
  degrades the delivery path itself. Mitigation: render-golden diff review plus
  the full `scripts/ci/all.sh` gate before delivery.

## Execution Record — 2026-08-03

All four lanes ran in one session rather than being split across parallel
sessions; the parallelism analysis above is retained because it is what makes the
split safe if this shape recurs.

Delivered as three PRs: **#16** (Lane B, skills), **#17** (Lane C, error inbox),
and **#18** (this bundle). All three were published with `git-cli push` — the
surface Lane B documents — which is the closest thing to an end-to-end test this
change has.

| Issue | Outcome |
| --- | --- |
| #5 | Closed — fixed in v1.25.13, verified by probe (`worktree add` leaves no upstream) |
| #6 | Closed — #11, with proposal 2 recorded as answered by substitution (raw fast-forward routed to `git-cli sync-default`, not admitted) |
| #7 | Closed on Lane B — surfaces shipped in v1.25.13, consumer layer aligned |
| #8 | Closed — #12, verified against all four asks |
| #9 | Closed — asks 1 and 3 delivered in v1.25.13; ask 2 refiled upstream as `sympoies/nils-cli#1428` (surface symmetry only; no functional gap) |
| #10 | Closed — #11, all four asks; observed live when a `cd &&` invocation was refused with a message that named the condition and the fix |

Lane B landed one behavior-relevant addition beyond the plan: `git-cli` was
absent from every affected skill's CLI floor even though `git-cli worktree remove`
was already in use, so the floors now name `git-cli >=1.25.13` explicitly.

Lane C resolved `push-guard-fails-closed-on-compound-command` (promoted and
archived) and re-triaged `managed-worktree-lockout-pushguard-ssh` to criterion
(a) only. (a) was re-verified as still unmet at runtime:
`checkout-lease-guard.dirty_adoption_enabled()` gates on
`AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION`, which is unset on this host, so the
adopt-dirty verbs remain inert.

### Two pre-existing gate failures, unrelated to this work

`scripts/ci/all.sh` position 13 fails on `main` itself, on two independent tests
with different root causes. Both were reproduced on an unmodified primary checkout
at `db0d5109`, so neither is lane fallout. Positions 1–12 pass; because the gate
stops at the first failing position, positions 14–17 were run individually for both
lanes and all pass.

1. **#15** — `test_checkout_lease_ref_safe_exception_rejects_reference_transaction_hook`
   (`AssertionError: unexpectedly None`). The guard fails *open*: it emits no
   decision where it should refuse the dirty-checkout ref-only exception because an
   executable `reference-transaction` hook could write checkout content.
2. **#19** — `test_shadow_is_side_effect_free_for_stateful_capabilities`. The
   snapshot reads a shared live state root, so concurrent `agent-session` writes
   land between the before and after comparison. #11 bound this only for the case
   where `AGENT_HOME` is *absent* from the environment; this host exports it, which
   is the documented operating configuration.

Both are out of scope here, but they mean `main` is red independently of this work,
and #19 additionally means the side-effect-freedom assertion cannot currently prove
what it claims.
