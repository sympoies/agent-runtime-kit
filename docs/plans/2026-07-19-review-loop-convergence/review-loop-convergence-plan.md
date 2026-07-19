# Plan: Converge the deliver-pr review loop

## Overview

Stop large PRs from being "reviewed forever / never merging". The delivery
specialist gate re-posts a fresh native review and fresh inline threads on every
delivery run with no cross-run idempotency; those threads then trip the
`forge-cli pr merge` unresolved-threads gate on the next run, so threads
accumulate faster than they converge. Add mechanical convergence capabilities to
`forge-cli` — idempotent native review posting keyed on head plus finding
fingerprint, mechanical `stale` disposition of `outdated` threads at the merge
gate, a required reason for the `--allow-unresolved-threads` bypass, and a bulk
disposition path — then update the agent-runtime-kit posting contract, delivery
wiring, and work-tier policy to consume them. Release and pin the coupled
nils-cli surface, and record the advance against the active
`async-bot-review-fix-loop` operation record. PR delivery stays the default and
the mandatory pre-merge gate is preserved; only its cross-run duplication is
removed.

## Read First

- Primary source: `docs/plans/2026-07-19-review-loop-convergence/review-loop-convergence-discussion-source.md`
- Source type: discussion-to-implementation-doc
- Runtime policy: `core/policies/work-tier-levels.md`, `core/policies/git-delivery.md`, `core/policies/files-hooks-validation.md`, `core/policies/review-thread-convergence.md`
- Review contract: `core/skills/code-review/code-review-specialists/references/REVIEW_OUTCOME_POSTING_CONTRACT.md`, `core/skills/code-review/code-review-specialists/references/DELIVERY_SPECIALIST_REVIEW_GATE.md`
- Heuristic system: `core/policies/heuristic-system/operation-records/async-bot-review-fix-loop/RECORD.md`
- Coupled CLI owner: `sympoies/nils-cli` (`forge-cli pr review`, `pr merge` rule 13, `pr review-threads`)
- Reference symptom: `sympoies/nils-cli#1272`
- Linked-but-orthogonal: open error-inbox entry `forge-cli-deliver-zero-required-skips-pending-checks` (nils-cli #1132)
- Open questions carried into execution: whether idempotency keys on head-SHA plus fingerprint alone suffices when a bot rewrites identical findings under a new review id; whether release/pin convergence can complete without touching any live runtime home (live activation stays approval-gated regardless)

## Scope

- In scope: forge-cli idempotent review posting, outdated→`stale` disposition and bulk disposition at rule 13, `--allow-unresolved-threads-reason`, and their tests; agent-runtime-kit posting-contract wording, delivery-skill wiring, work-tier/large-PR policy, render/golden/smoke refresh; coupled nils-cli release, pin, and consumer convergence; heuristic error-inbox case plus operation-record update.
- Out of scope: removing the mandatory gate; a draft skip that contradicts the pre-merge mandate; deleting or sweeping prior submitted reviews; provider branch-protection changes; the orthogonal #1132 check-gate fix; and applying finished runtime surfaces to live Codex/Claude homes.

## Assumptions

1. The normalized `forge-cli pr review-threads` envelope exposes stable `resolved` and `outdated` booleans and a per-thread finding fingerprint (or one can be derived deterministically from thread anchor plus body) sufficient to key idempotency.
2. Idempotent posting can be expressed as "do not create a duplicate open thread / do not re-submit an equivalent review for an unchanged head", without ever deleting or sweeping prior submitted reviews, preserving the locked posting contract.
3. Mechanically dispositioning an `outdated` thread as `stale` with a recorded rationale satisfies the convergence discipline's "every thread needs an explicit disposition" rule.
4. The plan tracks one upstream nils-cli PR (plus its release) and one runtime-kit PR; the runtime-kit PR is the plan's primary linked PR and the ledger records the upstream dependency and release, mirroring the 2026-07-16 direct-main precedent.
5. Coupled development validates against a debug nils-cli binary via `scripts/dev/with-nils-version.sh`; the full `scripts/ci/all.sh` gate runs only on-pin after the release.

## Sprint 1: forge-cli convergence capabilities

**Goal**: `forge-cli` mechanically prevents the review loop — idempotent native review posting, `outdated`→`stale` disposition and bulk disposition at rule 13, and a required-reason `--allow-unresolved-threads` bypass — or fails closed with typed results.

**Demo/Validation**:
- Command(s): focused `cargo test -p nils-forge-cli` across posting-idempotency, thread-disposition, and bypass-reason paths
- Verify: a second delivery run on an unchanged head creates no duplicate thread and re-submits no equivalent review; `outdated` threads are dispositioned `stale` with rationale; `--allow-unresolved-threads` without a reason fails closed; no prior submitted review is ever deleted

### Task 1.1: Open and initialize the L2 tracker

- **Location**: this plan bundle and the provider tracking issue
- **Description**: Validate and commit the bundle, open the tracking issue, initialize run state, and post the initial live checkpoint.
- **Dependencies**: none
- **Acceptance criteria**: issue is visible, run state reconciles, and source/plan/state roles are complete
- **Validation**: `plan-tooling validate`; `plan-issue tracking status --expect-visible`

### Task 1.2: Capture meaningful red for forge-cli convergence behavior

- **Location**: `sympoies/nils-cli/crates/forge-cli`
- **Description**: Create v2 test-first evidence and add failing tests for idempotent posting on an unchanged head, `outdated`→`stale` disposition at rule 13, bulk disposition, and required-reason bypass, then pass the pre-edit check before production edits.
- **Dependencies**: Task 1.1
- **Acceptance criteria**: failures demonstrate the missing convergence behavior rather than setup or fixture errors
- **Validation**: focused failing `cargo test`; `test-first-evidence check --phase pre-edit`

### Task 1.3: Implement idempotent native review posting (L1)

- **Location**: `sympoies/nils-cli/crates/forge-cli`
- **Description**: Key native review/thread posting on head SHA plus finding fingerprint so a re-run on an unchanged head does not open a duplicate thread or re-submit an equivalent review, while preserving within-run "post the moment a lens returns" ordering. Never delete or sweep prior submitted reviews.
- **Dependencies**: Task 1.2
- **Complexity**: 8
- **Acceptance criteria**: repeated posting on an unchanged head is a no-op for equivalent findings; a genuinely new finding or a new head still posts; prior reviews are untouched; typed result reports skipped-vs-posted
- **Validation**: focused and affected forge-cli suites

### Task 1.4: Outdated→stale disposition and bulk disposition at rule 13 (L3, L4)

- **Location**: `sympoies/nils-cli/crates/forge-cli`
- **Description**: At the unresolved-threads gate, mechanically disposition `outdated` threads as `stale` with a recorded rationale and provide a bulk disposition path for stale/preference threads, so convergence is deterministic without silently ignoring any thread.
- **Dependencies**: Task 1.2
- **Complexity**: 8
- **Acceptance criteria**: an `outdated` thread is recorded as `stale` with rationale and no longer blocks; a non-outdated unresolved thread still blocks; bulk disposition is auditable and never resolves a thread without a disposition
- **Validation**: focused and affected forge-cli suites; rule-13 gate tests

### Task 1.5: Required-reason unresolved-threads bypass (L5)

- **Location**: `sympoies/nils-cli/crates/forge-cli`
- **Description**: Add `--allow-unresolved-threads-reason`, required whenever `--allow-unresolved-threads` is set, recorded in the merge-step payload, mirroring `--allow-unchecked-tasks-reason`.
- **Dependencies**: Task 1.2
- **Acceptance criteria**: bypass without a non-empty reason fails closed; the reason is recorded in the payload; existing non-bypass behavior is unchanged
- **Validation**: focused forge-cli CLI-parsing and merge-payload tests

### Task 1.6: Deliver and review the nils-cli change

- **Location**: `sympoies/nils-cli`
- **Description**: Commit through `semantic-commit`, deliver the upstream PR without merge, run the required specialist review gate, repair findings, and merge only after provider gates converge.
- **Dependencies**: Task 1.3, Task 1.4, Task 1.5
- **Acceptance criteria**: upstream PR is merged with green checks and a provider-confirmed delivered head
- **Validation**: `forge-cli pr deliver --no-merge`; specialist reviews; `forge-cli pr merge`

## Sprint 2: runtime-kit integration, release, and closeout

**Goal**: the posting contract, delivery wiring, work-tier policy, rendered surfaces, and tests consume the new forge-cli behavior; the coupled surface is released and pinned; and the heuristic record reflects the advance.

**Demo/Validation**:
- Command(s): focused runtime-smoke + hook tests against a debug binary, then full `bash scripts/ci/all.sh` and `bash tests/hooks/run.sh` on-pin after release
- Verify: the contract documents cross-run idempotency and the new flags; goldens/smoke agree; a repeated delivery run posts no duplicate review

### Task 2.1: Capture meaningful red for runtime-kit surfaces

- **Location**: `tests/runtime-smoke/`, `tests/golden/`, relevant contract fixtures
- **Description**: Add failing smoke/golden expectations for the idempotent-posting contract wording and the new flag wiring in the delivery skills before editing the contract.
- **Dependencies**: Task 1.3
- **Acceptance criteria**: each failure identifies missing contract wording or flag wiring rather than a fixture error
- **Validation**: focused runtime-smoke; test-first pre-edit check

### Task 2.2: Update the posting contract and delivery wiring (L1, L2)

- **Location**: `core/skills/code-review/code-review-specialists/references/REVIEW_OUTCOME_POSTING_CONTRACT.md`, `.../DELIVERY_SPECIALIST_REVIEW_GATE.md`, and the delivery skills `core/skills/pr/deliver-pr`, `core/skills/dispatch/deliver-plan-tracking-issue`, and `core/skills/dispatch/deliver-dispatch-plan`
- **Description**: Document cross-run idempotency (create-not-duplicate, never sweep), the light draft-run posting note, and wire the new `--allow-unresolved-threads-reason` and disposition behavior through the delivery skills. Preserve every locked pre-merge invariant.
- **Dependencies**: Task 2.1, Task 1.6
- **Complexity**: 5
- **Acceptance criteria**: contract wording is consistent across skills, no pre-merge invariant is weakened, and rendered surfaces regenerate cleanly
- **Validation**: render + `git diff --exit-code -- tests/golden/`; focused runtime-smoke

### Task 2.3: State the work-tier / large-PR splitting expectation (L6)

- **Location**: `core/policies/work-tier-levels.md` (and the `AGENT_HOME.md` short directive only if needed)
- **Description**: Add a concise expectation that a change whose review surface is too large to converge is split into reviewable units / stacked PRs / L3 lanes rather than delivered as one giant PR.
- **Dependencies**: Task 2.1
- **Acceptance criteria**: the expectation is stated without contradicting existing tier triage, and pinned CI phrases are preserved
- **Validation**: `plan-tooling validate`; product-leak and golden gates

### Task 2.4: Heuristic case and operation-record update

- **Location**: `core/policies/heuristic-system/error-inbox/review-loop-non-convergence/`, `core/policies/heuristic-system/operation-records/async-bot-review-fix-loop/RECORD.md`
- **Description**: Open an error-inbox case with `Cluster: async-bot-review-fix-loop`, cross-linking the active operation record and its two archived siblings, and update the operation record's `Enforced-by` to reflect the newly mechanical idempotency/stale disposition. Link #1132 as orthogonal.
- **Dependencies**: Task 1.6
- **Acceptance criteria**: `heuristic-inbox verify --strict` passes for the new case and the updated record
- **Validation**: `heuristic-inbox verify --strict`

### Task 2.5: Release and pin the coupled CLI surface (gated)

- **Location**: nils-cli release workflow and runtime-kit nils-cli pin/consumer surfaces
- **Description**: After the upstream PR merges, complete the governed release boundary, then update the pin and every declared consumer through the repository-owned bump workflow without activating live runtime homes. This is the heaviest commitment and requires explicit maintainer go-ahead before the release runs.
- **Dependencies**: Task 1.6, Task 2.2
- **Acceptance criteria**: the released version exposes the new behavior; the runtime-kit pin and required floors converge; installed-vs-pinned validation passes in the controlled environment
- **Validation**: release receipts; version baseline and nils-cli surface gates

### Task 2.6: Full validation, PR review, merge, and closeout

- **Location**: runtime-kit repo-wide, provider PR, tracking issue, and plan archive handoff
- **Description**: Run the declared full gates on-pin, deliver the runtime-kit PR without merge, run independent specialist reviews, repair findings, post the review checkpoint, merge, close-ready/audit, and archive dry-run.
- **Dependencies**: Task 2.2, Task 2.3, Task 2.4, Task 2.5
- **Acceptance criteria**: all gates pass, PR merged, issue close-ready returns no blockers, read-back audit succeeds, and terminal cleanup is safe or explicitly retained
- **Validation**: `bash scripts/ci/all.sh`; `bash tests/hooks/run.sh`; provider review/merge/read-back; `plan-issue record audit`

### Task 2.7: Prove deploy readiness without activating runtime

- **Location**: released CLI, merged runtime-kit source, and dry-run runtime sync
- **Description**: Verify the completion matrix against current provider/source state and run the runtime sync/doctor path in dry-run or isolated state only. Stop before any `--apply` to live Codex/Claude homes.
- **Dependencies**: Task 2.6
- **Acceptance criteria**: all required artifacts are released/merged/green, dry-run reports an actionable update, and live runtime remains unchanged pending fresh user approval
- **Validation**: release/pin read-back; isolated doctor; `scripts/sync-runtime-surfaces.sh` dry-run

## Testing Strategy

- forge-cli unit/integration tests cover idempotent posting on an unchanged head, new-finding and new-head reposting, no-delete-of-prior-reviews, `outdated`→`stale` disposition with rationale, non-outdated threads still blocking, bulk disposition auditability, and required-reason bypass rejection.
- runtime-kit render/golden and deterministic runtime-smoke prove the contract wording and flag wiring reach Codex and Claude identically.
- Full repo gates and provider review prove coupling and delivery; an isolated/dry-run runtime check proves deploy readiness without mutating live homes.
- `heuristic-inbox verify --strict` proves the new case and updated operation record are lint-clean.

## Risks & gotchas

- Idempotency must not become "sweep/delete prior reviews": the posting contract forbids that. Key on create-not-duplicate; never mutate a prior submitted review.
- The within-run "post the moment a lens returns; never invert" invariant must survive cross-run idempotency; only equivalent re-posts on an unchanged head are suppressed.
- Fingerprint stability: if a bot re-emits an identical finding under a fresh review id, head-SHA plus fingerprint keying must still recognize it as a duplicate, or the loop persists.
- Outdated→`stale` must record a disposition, not silently resolve; silently ignoring a thread would violate the convergence discipline and could hide a genuine finding whose anchor merely moved.
- Coupled release/pin spans two repositories; live runtime activation is later than both and stays a separate explicit approval boundary. Do not run the full on-pin gate against an off-pin debug binary.

## Rollback plan

Revert the runtime-kit PR to restore the prior posting-contract wording and
delivery wiring. The new forge-cli behavior can remain unused: idempotency is a
no-op-safe superset of current posting, and the new flag is opt-in. If the CLI
behavior itself is defective, revert it in nils-cli and ship a corrective
release before any later runtime activation.
