# Plan: Adaptive checkout lease and workflow cleanup

## Overview

Add one product-neutral checkout writer lease, wire it through supported agent
hooks, and make safe merged-worktree cleanup an explicit terminal responsibility
of the PR, L2, and L3 delivery workflows. Deliver the result through one tracked
PR, then activate and verify the merged runtime on both requested roles.

## Read First

- Primary source: docs/plans/2026-07-15-adaptive-checkout-lease-cleanup/adaptive-checkout-lease-cleanup-discussion-source.md
- Source type: discussion-to-implementation-doc
- Open questions carried into execution: none

## Scope

- In scope: checkout identity, session-scoped lease state, dirty/foreign/stale
  decisions, explicit-edit and conservative shell-mutation gates, Stop audit,
  Codex/Claude rendering, Hermes capability declaration, terminal delivery
  cleanup, tests, PR delivery, dual-role activation.
- Out of scope: mandatory worktrees for every edit, destructive cleanup,
  complete shell-language interpretation, or a nils-cli release unless a
  genuinely missing product-neutral primitive is discovered.

## Sprint 1: Establish the checkout lease contract

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: Capture meaningful failing tests and implement the shared adaptive
writer lease with equivalent supported hook wiring.

**Demo/Validation**:

- Command: focused checkout-lease tests in `tests/hooks/test_shared_hooks.py`
- Verify: clean direct edit, owned refresh, dirty/foreign block, stale reclaim,
  recreated-worktree invalidation, Git-operation block, and read-only behavior.

### Task 1.1: Capture the lease contract with failing tests

- **Location**:
  - `tests/hooks/test_shared_hooks.py`
  - runtime test-first evidence under `agent-out`
- **Description**: Add focused contract coverage before production edits and
  retain a meaningful red at the hook-wiring boundary. Record changed,
  retained, and invariant behavior in the v2 test-first evidence contract.
- **Dependencies**:
  - none
- **Complexity**: 4
- **Acceptance criteria**:
  - The absent hook wiring fails the intended contract before production edits.
  - Functional fixtures cover lease acquisition, conflict, stale recovery,
    checkout reincarnation, operation state, and read-only escape paths.
  - The pre-edit test-first gate verifies successfully.
- **Validation**:
  - focused `python3 -m unittest` invocation for checkout lease tests
  - `test-first-evidence check --phase pre-edit`

### Task 1.2: Implement and render the shared checkout lease guard

- **Location**:
  - `core/hooks/shared/checkout-lease-guard.py`
  - `core/hooks/shared/hook_common.py`
  - `core/hooks/claude/settings.hooks.jsonc`
  - `targets/codex/link-map.yaml`
  - `targets/codex/hooks/config.block.toml`
  - rendered targets and golden fixtures
- **Description**: Implement atomic session-scoped lease acquisition using
  canonical Git identity and a checkout-instance sentinel. Wire explicit edit
  tools and conservative high-confidence Bash mutations, preserve read-only
  access, and add non-destructive Stop audit reporting.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 8
- **Acceptance criteria**:
  - Same-session refresh succeeds after the owner dirties the checkout.
  - Live foreign leases and unowned dirty state block mutation with actionable
    worktree guidance.
  - Only clean expired leases can be reclaimed; removed/recreated worktrees do
    not inherit ownership.
  - Pre-existing unowned Git operations and missing explicit-edit identity fail
    closed; an existing owner can resolve an operation it initiated.
  - Supported Codex and Claude surfaces are semantically equivalent and Hermes
    makes no unsupported hook claim.
- **Validation**:
  - focused checkout-lease tests
  - `bash tests/hooks/run.sh`

## Sprint 2: Make terminal cleanup part of delivery

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: Ensure successful delivery closes the local lifecycle without risking
dirty, locked, or unmerged work.

**Demo/Validation**:

- Command: render/governance tests plus workflow contract tests
- Verify: PR, L2, and L3 instructions all place cleanup after terminal duties
  and use only the managed worktree removal surface.

### Task 2.1: Add terminal workflow cleanup policy and workflow contracts

- **Location**:
  - `core/policies/git-delivery.md`
  - `core/skills/pr/deliver-pr/`
  - `core/skills/dispatch/deliver-plan-tracking-issue/`
  - `core/skills/dispatch/deliver-dispatch-plan/`
  - related workflow contract tests
- **Description**: Define and apply one terminal cleanup sequence after provider,
  issue, archive, deployment, and local closeout duties. Restore a direct
  primary checkout or remove a safe merged managed worktree and its branch;
  retain and report all unsafe state.
- **Dependencies**:
  - Task 1.2
- **Complexity**: 6
- **Acceptance criteria**:
  - Stop remains audit-only and never removes worktrees.
  - All three delivery paths invoke cleanup only at their true terminal edge.
  - Cleanup uses `git-cli worktree`, never direct mutating `git worktree`.
  - Dirty, locked, unmerged, or failed-terminal state is retained with a
    recovery report.
- **Validation**:
  - focused workflow contract tests
  - `bash scripts/ci/render.sh --check`

### Task 2.2: Refresh generated product surfaces and documentation mirrors

- **Location**:
  - `targets/codex/`
  - `targets/claude/`
  - `targets/hermes/`
  - `tests/golden/`
  - `SUPPORT_MATRIX.md`
- **Description**: Run the governed render path and update only the generated
  surfaces required by the new shared hook and workflow wording.
- **Dependencies**:
  - Task 2.1
- **Complexity**: 4
- **Acceptance criteria**:
  - Render check is clean and generated surfaces match canonical sources.
  - Product capability claims remain truthful.
- **Validation**:
  - repository render/golden validation selected by `DEVELOPMENT.md`

## Sprint 3: Review, deliver, activate, and close

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: Pass strict local and provider gates, merge the PR, activate both
runtime roles from merged `main`, and close the L2 record and local worktree.

**Demo/Validation**:

- Command: `bash scripts/ci/all.sh` and `bash tests/hooks/run.sh`
- Verify: local gates, specialist review, provider checks, dual-role deployed
  revision, tracker close audit, and safe terminal worktree cleanup all pass.

### Task 3.1: Run full validation and delegated pre-merge review

- **Location**:
  - complete change set
  - runtime evidence under `agent-out`
- **Description**: Run the declared project validation, render and status
  checks, then complete mandatory testing and maintainability review with
  provider-visible disposition of actionable findings.
- **Dependencies**:
  - Task 2.2
- **Complexity**: 6
- **Acceptance criteria**:
  - Full repository CI and hook suites pass.
  - Required review lenses approve or all findings are repaired and rechecked.
  - Test-first, docs-impact, validation, and workflow-usage records verify.
- **Validation**:
  - `bash scripts/ci/all.sh`
  - `bash tests/hooks/run.sh`
  - review gate and unresolved-thread read-back

### Task 3.2: Deliver and merge the tracked PR

- **Location**:
  - provider tracking issue
  - provider pull request
- **Description**: Commit with the governed semantic commit surface, deliver
  through `forge-cli pr deliver --no-merge`, post required review evidence,
  satisfy provider checks, merge without force-pushing `main`, and checkpoint
  the L2 tracker.
- **Dependencies**:
  - Task 3.1
- **Complexity**: 5
- **Acceptance criteria**:
  - PR is merged with the tracking issue referenced.
  - Provider checks and unresolved-thread gates are green.
  - Tracking lifecycle comments and run state agree with provider truth.
- **Validation**:
  - strict provider PR read-back
  - `plan-issue tracking review checkpoint`

### Task 3.3: Activate both runtime roles and perform strict closeout

- **Location**:
  - `.agents/scripts/deploy.sh`
  - provider tracking issue
  - managed local worktree
- **Description**: Run the repository deploy entrypoint through `agent-run` for
  both requested runtime roles, verify the merged revision, complete strict L2
  close-ready/close/read-back/archive duties, then remove only safe merged local
  worktree state.
- **Dependencies**:
  - Task 3.2
- **Complexity**: 5
- **Acceptance criteria**:
  - Both roles report the merged runtime revision and pass repository-defined
    deploy verification.
  - The tracking issue closes only after lifecycle audit passes.
  - Safe managed worktree and merged local branch are removed; unsafe state is
    retained and reported.
- **Validation**:
  - repository deploy verification for each role
  - `plan-issue tracking close-ready`
  - provider read-back and archive dry-run/apply

## Completion Contract

The plan is complete only when the PR is merged, both requested runtime roles
are activated from the merged revision, the L2 tracking issue passes strict
closeout, and the local checkout/worktree audit reports either safe removal or
an explicit retained-state reason.
