# Plan: Add governed dirty-checkout adoption

## Overview

Add an off-by-default, challenged ownership transition that lets an agent adopt
an already dirty physical Git checkout only after an explicit user turn. The
normal checkout lease remains unconditional: advisory context is private until
implementation begins, authorization is represented by a short-lived
same-session challenge bound to an exact dirty snapshot, and a governed CLI
command consumes that challenge under the lease lock before writing a
privacy-safe receipt. Every ambiguous, stale, racing, foreign-owned, or
unsupported state fails closed and retains the managed-worktree escape.

## Read First

- Primary source: `docs/plans/2026-07-17-dirty-checkout-adoption/dirty-checkout-adoption-discussion-source.md`
- Source type: discussion-to-implementation-doc
- Runtime policy: `core/policies/work-tier-levels.md`, `core/policies/git-delivery.md`, `core/policies/files-hooks-validation.md`, `core/policies/evidence-control-plane.md`
- Hook contract: `core/hooks/README.md`, `core/hooks/shared/checkout-lease-guard.py`, `core/hooks/shared/hook_common.py`, `targets/codex/hooks/config.block.toml`, `core/hooks/claude/settings.hooks.jsonc`
- Coupled CLI owner: `sympoies/nils-cli` (`git-cli worktree` command family)
- Related but not duplicate: <https://github.com/graysurf/agent-runtime-kit/issues/601>
- Open questions carried into execution: the final CLI naming may change only if nils-cli maintainers identify a command-family collision; the challenge, snapshot, lease, and receipt contracts below must not weaken

## Scope

- In scope: `AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION=1`; private advisory and challenge issuance; canonical dirty snapshot; challenged adopt and receipt-bound revoke commands; lease-schema evolution; Codex/Claude wiring; policy and support-matrix updates; render/golden coverage; coupled validation, PR delivery, release/pin convergence, and deploy-readiness audit.
- Out of scope: automatic or inferred authorization, natural-language parsing in hooks, raw env bypasses, force takeover of another live session, Git-operation continuation, automatic stash/reset/clean/commit, dirty submodules and special files in v1, Hermes hook enforcement, and live runtime activation.

## Frozen contract

1. The feature flag is a master admission flag, not a safety-disable flag. When absent, no challenge is issued and `adopt-dirty` fails typed; the existing dirty-checkout mutation block, same-session refresh, foreign-lease block, worktree-add escape, and Stop audit remain active.
2. A dirty `UserPromptSubmit` event creates at most one current challenge per session and checkout. The private context tells the agent to remain silent for read-only Q&A and, before implementation, ask the user to choose read-only inspection plus explicit takeover or a managed worktree.
3. A challenge is mode-0600, bounded, one-time, default-five-minute state containing schema version, random token digest, session-key digest, repository/common-dir key, checkout root key, checkout-instance sentinel, snapshot ID, HEAD/branch summary, user-turn digest, and issued/expiry timestamps. Raw prompt, diff, paths, and file contents are excluded.
4. The agent invokes `git-cli worktree adopt-dirty` only after an unambiguous user turn authorizes the exact warned state. It supplies the opaque challenge token and a non-empty, regular, non-symlink UTF-8 reason file of at most 2,000 bytes. The receipt retains only the reason digest.
5. The lease guard recognizes only a sole governed adoption command with no co-resident repository mutation as an admission escape. The CLI re-resolves the physical checkout, acquires the existing lease lock, rejects a live foreign lease or Git operation, recalculates the snapshot, atomically consumes the challenge, writes the adopted lease, and returns structured JSON. Invalid invocation never acquires a lease.
6. `git-cli worktree dirty-snapshot` is the sole canonical fingerprint implementation. It binds checkout/common-dir identity, checkout-instance sentinel, HEAD and symbolic branch, raw index-stage entries, staged and unstaged Git content, and untracked regular-file/symlink content. It uses NUL-safe path handling, disables external diff/text conversion, streams hashes, checks each object and the full snapshot for drift, and returns no content.
7. V1 rejects unmerged index stages, active merge/rebase/cherry-pick/revert/sequencer/bisect/index-lock state, dirty submodules, filesystem special files, symlink/path escape, malformed Git output, and configured resource-bound overflow. These are typed unsupported states, not lossy fingerprints.
8. Lease schema v2 is backward-readable and preserves adoption metadata across same-session refresh. Its adoption block contains receipt schema/ID, snapshot ID, authorization-turn digest, reason digest, adopted time, and challenge issue time. V1 clean-acquisition leases remain valid during rollout.
9. Receipt-bound revocation removes only a matching current session's lease/challenge metadata after revalidating checkout instance and receipt ID. It never changes Git or filesystem content. Stop releases only clean matching-session leases and retains dirty/unverifiable leases exactly as today.
10. Snapshot equality closes prompt-to-adoption drift; lock/recheck closes competing agent admission. This is not an operating-system lock against a human or arbitrary process after acquisition. The receipt and policy must not overstate that threat boundary.

## Assumptions

1. Codex and Claude continue to provide stable opaque session IDs to hook payloads; only their SHA-256 digests enter runtime state.
2. The nils-cli command can share the runtime state-path and schema contract without receiving the raw hook session ID because the random bearer challenge already embeds the hashed session binding created by the hook.
3. The current canonical dirty predicate remains `git status --porcelain=v1 --untracked-files=all --ignore-submodules=none`; snapshot logic may add NUL-safe/content probes but must not silently narrow what counts as dirty.
4. The plan may track one upstream nils-cli PR and one runtime-kit PR; the runtime-kit PR is the primary linked PR and the execution ledger records the released upstream dependency.
5. Live Codex/Claude sync is not authorized by plan creation or later implementation and remains a separate maintainer decision.

## Sprint 1: Freeze and implement the CLI/state contract

**Goal**: Produce one canonical snapshot and one race-checked challenge-to-lease transition with typed outputs and cross-language schema fixtures.

**Demo/Validation**:
- Command(s): focused `cargo test -p nils-git-cli` unit/integration suites plus runtime-kit lease fixture tests
- Verify: exact-state success produces a v2 lease and receipt; every stale, foreign, unsupported, malformed, or racing case leaves working-tree content untouched and acquires no lease

### Task 1.1: Open and initialize the L2 tracker

- **Location**: this plan bundle and the provider tracking issue
- **Description**: Validate and commit the bundle, open the tracking issue, initialize run state, and verify visible source/plan/state lifecycle records. Do not begin implementation in this task.
- **Dependencies**: none
- **Acceptance criteria**: the issue is visible, run state reconciles, and all three bundle roles are complete
- **Validation**: `plan-tooling validate`; `plan-issue tracking status --expect-visible`

### Task 1.2: Capture meaningful red for snapshot and adoption behavior

- **Location**: `sympoies/nils-cli/crates/git-cli` and runtime-kit lease-schema fixtures
- **Description**: Create v2 test-first evidence and failing tests for snapshot sensitivity, challenged success, schema compatibility, and every rejection partition before production edits.
- **Dependencies**: Task 1.1
- **Acceptance criteria**: failures demonstrate missing behavior rather than fixture, permissions, or command-routing errors; affected-test decisions include both repositories
- **Validation**: focused failing Cargo and Python tests; `test-first-evidence check --phase pre-edit`

### Task 1.3: Implement canonical snapshot, adopt, and revoke commands

- **Location**: `sympoies/nils-cli/crates/git-cli`
- **Description**: Add `dirty-snapshot`, `adopt-dirty`, and receipt-bound revocation; bounded challenge/reason parsing; common-dir/checkout-instance resolution; canonical NUL-safe streaming fingerprint; lock/recheck/consume/write transaction; v2 envelope/receipt schemas; typed failures; help/completion/docs; and fixture export for runtime-kit.
- **Dependencies**: Task 1.2
- **Complexity**: 9
- **Acceptance criteria**: content-only changes alter the snapshot; stale or reused challenges fail; foreign leases and Git operations fail; no command mutates Git content; success writes exactly one matching adopted lease and privacy-safe receipt
- **Validation**: focused and affected git-cli suites; nils-cli repository-required validation

### Task 1.4: Deliver and review the nils-cli change

- **Location**: `sympoies/nils-cli`
- **Description**: Commit through `semantic-commit`, deliver the upstream PR without merge, run testing, maintainability, API-contract, and security specialist review, repair findings, and merge only after provider gates converge.
- **Dependencies**: Task 1.3
- **Acceptance criteria**: upstream PR is merged, all review findings are dispositioned, and the provider-confirmed head matches validated evidence
- **Validation**: `forge-cli pr deliver --no-merge`; specialist review gate; `forge-cli pr merge`

## Sprint 2: Integrate advisory UX and lease enforcement

**Goal**: Codex and Claude provide the optional user-friendly decision point while the hard writer lease remains deterministic and product policy stays accurate.

**Demo/Validation**:
- Command(s): focused hook tests, product render/golden tests, `bash scripts/ci/all.sh`, and `bash tests/hooks/run.sh`
- Verify: Q&A has no visible dirty-state interruption; implementation receives the two-choice cue; only a current exact challenge adopts; disabling the flag restores current behavior; worktree escape and Stop remain non-destructive

### Task 2.1: Capture meaningful red for runtime hook behavior

- **Location**: `tests/hooks/test_shared_hooks.py`
- **Description**: Add failing acceptance tests for flag-off silence, clean silence, private dirty advisory, same-session suppression, post-warning turn binding, sole-command classification, challenge expiry/reuse, state drift, foreign lease, Git operation, v1/v2 lease reading, refresh preservation, revoke, Stop, and Codex/Claude/Hermes capability boundaries.
- **Dependencies**: Task 1.3
- **Acceptance criteria**: each failure maps to one frozen contract clause and proves the existing mutation block is not weakened
- **Validation**: focused Python unittest selection; test-first pre-edit check

### Task 2.2: Implement challenge issuance and lease integration

- **Location**: `core/hooks/shared/`, runtime policy, and hook documentation
- **Description**: Add opt-in UserPrompt challenge/advisory behavior; consume nils-cli snapshot output; evolve lease parsing/writing to v2; preserve adoption metadata on refresh; add exact `adopt-dirty` and revoke routing; document authorization, expiry, receipt, threat, recovery, and worktree fallback contracts.
- **Dependencies**: Task 2.1
- **Complexity**: 9
- **Acceptance criteria**: hooks never parse authorization language, never expose raw prompt/diff/reason, never auto-modify unknown changes, and fail closed on missing/unsupported CLI or state
- **Validation**: focused hook and schema-conformance tests

### Task 2.3: Wire product parity and release/pin the CLI

- **Location**: Codex/Claude hook source configs, link/render manifests, support matrix, nils-cli release workflow, and runtime-kit pin/consumer surfaces
- **Description**: Register the advisory hook for Codex and Claude, keep Hermes accurately unsupported, refresh generated/golden surfaces, release the merged nils-cli command, and update pins/floors through repository-owned workflows without applying live homes.
- **Dependencies**: Task 1.4, Task 2.2
- **Acceptance criteria**: rendered Codex and Claude configs invoke the same shared contract; released CLI and runtime-kit pins converge; Hermes claims no enforcement; live homes remain unchanged
- **Validation**: render/drift gates; release receipts; installed-vs-pinned validation in a controlled environment

### Task 2.4: Full validation and PR review

- **Location**: runtime-kit repository, provider PR, and tracking issue
- **Description**: Run full required gates, deliver the runtime-kit PR without merge, run one testing, maintainability, API-contract, and security review round, repair major findings, disposition residuals, and publish the combined delivery outcome.
- **Dependencies**: Task 2.3
- **Acceptance criteria**: all gates pass, the validated PR head is provider-visible, and every review finding is repaired, accepted with rationale, or routed to a follow-up
- **Validation**: `bash scripts/ci/all.sh`; `bash tests/hooks/run.sh`; provider check and review read-back

### Task 2.5: Prove deploy readiness without live activation

- **Location**: released CLI, validated runtime-kit source, and isolated/dry-run runtime sync
- **Description**: Verify the completion matrix and run runtime sync/doctor only in dry-run or isolated state. Stop before every live `--apply` operation.
- **Dependencies**: Task 2.4
- **Acceptance criteria**: all required artifacts are released and the runtime-kit PR is green; isolated proof reports the expected update; live Codex/Claude homes remain unchanged pending fresh approval
- **Validation**: release/pin read-back; isolated doctor; runtime-surface sync dry-run

### L2 terminal lifecycle

After every task-ledger row is terminal, publish the issue-side state/review checkpoint, merge the provider-bound reviewed head, pass strict close-ready, close and audit the tracker, perform archive discovery and migration dry-run, and prove safe terminal worktree cleanup. These are governed L2 lifecycle duties rather than self-referential task-ledger prerequisites. Archive apply and live runtime-home activation remain separately confirmation-gated.

## Testing Strategy

- Snapshot unit/property tests vary only file content, mode, symlink target, index stage, HEAD, branch, untracked filename bytes, and ordering to prove stable sensitivity and NUL-safe determinism.
- Integration fixtures cover staged/unstaged/untracked combinations, unborn/detached heads, deletions, renames, large streamed files, drift during hashing, unmerged indexes, submodules, special files, and resource limits.
- Adoption transaction tests cover valid one-time consumption, wrong checkout/session/instance, stale/reused token, reason-file validation, live/expired leases, lock races, state corruption, v1/v2 compatibility, refresh metadata, revoke, and receipts with no raw content.
- Hook acceptance tests cover flag and prompt behavior, sole-command parsing through supported wrappers, guarded-command allowance without a general lease bypass, same-session suppression, Stop semantics, and unchanged worktree-add remediation.
- Product rendering and deterministic smoke prove Codex/Claude parity and the Hermes ceiling. Full repository gates and specialist reviews prove coupled delivery.

## Risks & gotchas

- A porcelain status line alone is not an exact snapshot: content can change while status remains `M`. The implementation must hash staged, unstaged, and untracked content and detect in-flight changes.
- Git paths are arbitrary bytes. Any newline-delimited or lossy UTF-8 path parser can bind authorization to the wrong state; use NUL-safe byte handling throughout and omit paths from remote receipts.
- The random challenge is a bearer capability visible to the current agent context. Keep it short-lived, single-use, mode-0600 at rest, absent from provider evidence, and invalid after any snapshot drift.
- Cross-language lease state is a compatibility boundary. Versioned schemas and shared fixtures are mandatory; Python must preserve v2 adoption metadata during refresh rather than silently downgrade it.
- Hooks are mechanical guardrails, not a security sandbox. The lock coordinates participating agent sessions; it cannot prevent a human or arbitrary process from editing after adoption.
- Feature disable, CLI absence, malformed state, and product capability uncertainty must fail closed for takeover while retaining read-only inspection and managed-worktree remediation.
- Release/pin work spans two repositories. Live activation remains later than both and requires fresh approval.

## Rollback plan

Disable `AGENT_RUNTIME_DIRTY_CHECKOUT_ADOPTION` to stop new advisory challenges
and adoptions without weakening ordinary lease enforcement. Revert the
runtime-kit PR to remove hook routing while retaining v1/v2 lease read
compatibility long enough for existing receipts to expire. If the CLI contract
is defective, revert it in nils-cli and ship a corrective release before any
runtime activation. Rollback never deletes a dirty lease or modifies checkout
content; operators may revoke a matching receipt or wait for the normal lease
recovery path.
