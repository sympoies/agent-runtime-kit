# Plan: Add a governed direct-main delivery mode

## Overview

Add an explicit, auditable L0 exception that lets a maintainer-authorized agent
land one signed commit directly on the remote default branch without a PR. Work
remains isolated in a managed worktree on a non-default branch,
`semantic-commit` creates the signed commit, and a new `forge-cli repo
push-default` primitive uniquely binds the actual push URL, pins all three
remote operations to it, and verifies an expected base, one-commit shape, clean
state, signature, bounded regular reason file, absence of a second-stage Git URL
rewrite, bounded subprocess execution, fast-forward ancestry, an
exact-old-object compare-and-swap, and remote read-back. Runtime-kit policy and
hooks make that primitive the only supported agent route while keeping PR
delivery as the default.

## Read First

- Primary source: `docs/plans/2026-07-16-direct-main-delivery-mode/direct-main-delivery-mode-discussion-source.md`
- Source type: discussion-to-implementation-doc
- Runtime policy: `core/policies/work-tier-levels.md`, `core/policies/git-delivery.md`, `core/policies/files-hooks-validation.md`
- Hook contract: `core/hooks/README.md`, `targets/codex/hooks/config.block.toml`, `core/hooks/claude/settings.hooks.jsonc`
- Coupled CLI owner: `sympoies/nils-cli` (`forge-cli` repo command family)
- Open questions carried into execution: whether release/pin convergence can complete without changing any live runtime home; live activation remains approval-gated regardless

## Scope

- In scope: one new nils-cli governed push command and tests; direct-default-push and default-branch-commit hook gates; read-only classifier corrections; policy/enforcement matrix corrections; render/golden refresh; coupled validation, PR delivery, release/pin convergence, and deploy-readiness audit.
- Out of scope: more than one commit, forced updates, unsigned commits, provider-rule bypass, automatic approval inference, direct merges, and live runtime activation.

## Assumptions

1. The provider default branch remains discoverable through the existing `forge-cli repo view` adapter.
2. An expected-base precondition plus fast-forward ancestry proof and an internal exact-old-object lease can provide compare-and-swap race safety without exposing any caller-controlled force option.
3. Local signature verification is available on supported hosts because tracked agent work already requires signed `semantic-commit` commits.
4. The plan may track an upstream nils-cli PR plus one runtime-kit PR; the runtime-kit PR is the plan's primary linked PR and the execution ledger records the upstream dependency.

## Sprint 1: Freeze and implement the CLI contract

**Goal**: `forge-cli repo push-default` safely delivers exactly one authorized signed commit or fails closed with a typed result.

**Demo/Validation**:
- Command(s): focused `cargo test -p nils-forge-cli` tests for success and every rejection path
- Verify: fixture remotes prove expected-base matching, signature/shape checks, no force path, race failure, and post-push SHA receipt

### Task 1.1: Open and initialize the L2 tracker

- **Location**: this plan bundle and the provider tracking issue
- **Description**: Validate and commit the bundle, open the tracking issue, initialize run state, and post the initial live checkpoint.
- **Dependencies**: none
- **Acceptance criteria**: issue is visible, run state reconciles, and source/plan/state roles are complete
- **Validation**: `plan-tooling validate`; `plan-issue tracking status --expect-visible`

### Task 1.2: Capture meaningful red for the nils-cli behavior

- **Location**: `sympoies/nils-cli/crates/forge-cli`
- **Description**: Create v2 test-first evidence, add failing contract tests for successful delivery and rejection partitions, and pass the pre-edit check before production code changes.
- **Dependencies**: Task 1.1
- **Acceptance criteria**: failures demonstrate the missing command/behavior rather than setup or fixture errors
- **Validation**: focused failing `cargo test`; `test-first-evidence check --phase pre-edit`

### Task 1.3: Implement the governed push primitive

- **Location**: `sympoies/nils-cli/crates/forge-cli`
- **Description**: Add CLI parsing, repository/default-branch resolution, clean/branch/base/one-commit/signature validation, exact-base compare-and-swap delivery, post-push read-back, typed failures, JSON receipt, docs, and completion/spec coverage.
- **Dependencies**: Task 1.2
- **Complexity**: 8
- **Acceptance criteria**: the command never accepts force input, never authors on the default branch, rejects stale base or non-single-commit shape, and returns the exact remote head after success
- **Validation**: focused and affected forge-cli test suites; repo-required nils-cli validation

### Task 1.4: Deliver and review the nils-cli change

- **Location**: `sympoies/nils-cli`
- **Description**: Commit through `semantic-commit`, deliver the upstream PR without merge, run the required specialist review gate, repair findings, and merge only after provider gates converge.
- **Dependencies**: Task 1.3
- **Acceptance criteria**: upstream PR is merged with green checks and provider-confirmed delivered head
- **Validation**: `forge-cli pr deliver --no-merge`; specialist reviews; `forge-cli pr merge`

## Sprint 2: Integrate runtime policy and enforcement

**Goal**: policy, hooks, rendered surfaces, and tests agree that PR is the default and governed direct-main is the sole explicit exception.

**Demo/Validation**:
- Command(s): focused hook tests, deterministic runtime smoke, full `scripts/ci/all.sh`, full hook suite
- Verify: raw default-branch pushes and default-branch commits are blocked; feature pushes and read-only inspection remain allowed; the governed command is routed without weakening force protection

### Task 2.1: Capture meaningful red for runtime-kit hooks

- **Location**: `tests/hooks/test_shared_hooks.py`
- **Description**: Add failing acceptance tests for raw normal/force default pushes, default-branch `semantic-commit`, allowed feature push, governed CLI route, and read-only help/dry-run classification.
- **Dependencies**: Task 1.3
- **Acceptance criteria**: each failure identifies a missing or misleading enforcement contract
- **Validation**: focused Python unittest selection; test-first pre-edit check

### Task 2.2: Align policy and hook implementation

- **Location**: `AGENT_HOME.md`, `core/policies/work-tier-levels.md`, `core/policies/git-delivery.md`, `core/hooks/README.md`, shared hooks, and product hook configs
- **Description**: Document the explicit L0 exception and delivery receipt model; add hook enforcement and default-branch semantic-commit restriction; correct read-only classification and overstated hook claims; keep Stop as a reporter.
- **Dependencies**: Task 2.1
- **Complexity**: 8
- **Acceptance criteria**: one canonical decision/enforcement matrix exists and all short summaries link to it without contradictory PR-floor wording
- **Validation**: focused hook tests; config/render contract checks

### Task 2.3: Release and pin the coupled CLI surface

- **Location**: nils-cli release workflow and runtime-kit nils-cli pin/consumer surfaces
- **Description**: Complete the governed release boundary required for runtime-kit to consume the command, then update the pin and every declared consumer through the repository-owned bump workflow without activating live runtime homes.
- **Dependencies**: Task 1.4, Task 2.2
- **Acceptance criteria**: released version exposes `forge-cli repo push-default`; runtime-kit pin and required floors converge; installed-vs-pinned validation passes in the controlled validation environment
- **Validation**: release receipts; version baseline and nils-cli surface gates

### Task 2.4: Full validation, PR review, merge, and closeout

- **Location**: runtime-kit repo-wide, provider PR, tracking issue, and plan archive handoff
- **Description**: Run the declared full gates, deliver the runtime-kit PR without merge, run independent specialist reviews, repair findings, post review checkpoint, merge, close-ready/audit, and archive dry-run.
- **Dependencies**: Task 2.3
- **Acceptance criteria**: all gates pass, PR is merged, issue close-ready returns no blockers, read-back audit succeeds, and terminal cleanup is safe or explicitly retained
- **Validation**: `bash scripts/ci/all.sh`; `bash tests/hooks/run.sh`; provider review/merge/read-back; `plan-issue record audit`

### Task 2.5: Prove deploy readiness without activating runtime

- **Location**: released CLI, merged runtime-kit source, and dry-run runtime sync
- **Description**: Verify the completion matrix against current provider/source state and run the runtime sync/doctor path in dry-run or isolated state only. Stop before any `--apply` to live Codex/Claude homes.
- **Dependencies**: Task 2.4
- **Acceptance criteria**: all required artifacts are released/merged/green, dry-run reports an actionable update, and live runtime remains unchanged pending fresh user approval
- **Validation**: release/pin read-back; isolated doctor; `scripts/sync-runtime-surfaces.sh` dry-run

## Testing Strategy

- CLI unit/integration tests cover parsing, clean checkout, non-default authoring branch, expected-base equality, exact one-commit shape, signature validation, verified fast-forward delivery with an exact old-object lease, stale/racing remote failure, and post-push remote SHA.
- Hook acceptance tests cover common argv/refspec forms, aliases and shell wrappers already supported by the classifier, governed-command allowance, force rejection, feature-branch allowance, and read-only command classification.
- Runtime rendering/golden and deterministic smoke prove Codex and Claude receive the same hook contract.
- Full repo gates and provider review prove coupling and delivery; an isolated/dry-run runtime check proves deploy readiness without mutating live homes.

## Risks & gotchas

- Default-branch discovery must fail closed; hard-coding `main` would mis-handle repositories with another default.
- Hook parsing is a guardrail, not a security sandbox. The nils-cli primitive remains the authoritative state-changing contract and remote branch rules remain defense in depth.
- Signature verification must distinguish unsigned, bad, and unverifiable commits and provide actionable typed output without leaking secrets.
- A provider race after precheck must fail the exact-base compare-and-swap. The implementation must never weaken the expected old object, accept caller-controlled force input, or retry with a broader lease.
- Release and pin work spans two repositories. Live runtime activation is later than both and remains a separate explicit approval boundary.

## Rollback plan

Revert the runtime-kit PR to restore PR-only agent policy and hook routing. The
new nils-cli command may remain unused; it cannot bypass remote rules and still
requires its explicit arguments. If the CLI contract itself is defective,
revert it in nils-cli and ship a corrective release before any later runtime
activation.
