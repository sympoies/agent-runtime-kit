# Plan: Deliver a real read-only execution capability

## Overview

Replace runtime-kit's argv allowlist with the accepted
`execution.read-only.v1` capability through small, independently reviewable
cross-repository slices. Land the nils-cli capability and typed managed-query
contracts first, add the OS-enforced Linux inspection backend while macOS
remains explicitly fail-closed, release and pin the complete CLI surface, then
integrate through #686's single
`agent-hook` ingress, compare shadow decisions, and remove the legacy
classifier. Preserve every existing mutation and finish-line invariant while
using the already-delivered #673 convergence behavior to prevent repeated
review cycles.

## Read First

- Primary source:
  `docs/plans/2026-07-20-read-only-execution-capability/read-only-execution-capability-discussion-source.md`
- Source type: discussion-to-implementation-doc
- Owner tracker: <https://github.com/graysurf/agent-runtime-kit/issues/670>
- Integration dependency: <https://github.com/graysurf/agent-runtime-kit/issues/686>
- Deferred strict macOS backend: <https://github.com/sympoies/nils-cli/issues/1343>
- Review-convergence baseline: <https://github.com/graysurf/agent-runtime-kit/issues/673>
- Runtime policy: `core/policies/files-hooks-validation.md`,
  `core/policies/work-tier-levels.md`, and `core/policies/git-delivery.md`
- Open questions carried into execution: none. Linux may emit `os_enforced`
  after the common conformance contract passes. macOS keeps the same CLI but
  returns typed `unavailable` until a separately tracked strict backend can
  satisfy that contract.

## Scope

- In scope: nils-cli `execution.read-only.v1` schema and verification;
  same-release tool effect descriptors; `agent-run inspect`; Linux
  confinement; typed fail-closed macOS behavior; adversarial conformance;
  runtime-kit policy/feedback/migration;
  Codex/Claude parity fixtures; nils-cli release and runtime-kit pin; legacy
  classifier deletion; PR delivery, strict tracker closeout, and archive
  handoff.
- Out of scope: general provider clients as trusted producers; arbitrary
  network in the local sandbox; host attestation synthesized from current
  product settings; privileged/dedicated-user or VM-backed macOS confinement;
  issue #686 redesign; live runtime apply without fresh approval; unrelated
  hook cleanup.

## Delivery shape and convergence rule

The implementation is sequential L2 work, not L3 dispatch. Use these reviewable
PR boundaries; do not combine owner boundaries merely to reduce PR count:

1. nils-cli capability schema plus typed `agent-docs`/`forge-cli` descriptors;
2. nils-cli common inspection runner plus Linux backend;
3. nils-cli macOS fail-closed contract and cross-platform behavior completion;
4. runtime-kit shadow integration and parity fixtures after #686 ingress is
   available; and
5. runtime-kit cutover and legacy classifier removal after shadow parity.

The release/pin transition sits between 3 and 4 and uses its governed workflow.
Each PR receives one focused specialist gate. Repair only concrete blockers and
rerun only affected lenses once; P2 preferences become follow-ups. Equivalent
reviews on an unchanged head rely on #673 idempotency and are not reposted.

## Sprint 1: Capability schema and managed query contracts

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: make read-only evidence a versioned typed capability and remove raw
argv interpretation from the future decision boundary while keeping production
behavior in shadow mode.

**Demo/Validation**:

- Command: focused `cargo test` for `agent-hook`, `agent-docs`, and `forge-cli`
- Verify: exact same-release typed queries produce bound descriptors; forged,
  stale, mismatched, unknown, or state-changing variants produce no capability

### Task 1.1: Attach and initialize the L2 tracker

- **Location**: this bundle and issue #670
- **Description**: Validate the bundle, attach source/plan/state roles to the
  existing issue, initialize tracking run state, and post the initial visible
  checkpoint without opening a duplicate issue.
- **Dependencies**: none
- **Complexity**: 2
- **Acceptance criteria**:
  - #670 carries exactly one tracking-profile source, plan, and state lifecycle
    record set.
  - The issue dashboard is `ready`, run state reconciles, and Task 1.2 is the
    next implementation action.
- **Validation**:
  - `plan-tooling validate --format text --explain`
  - `plan-issue tracking status --profile tracking --expect-visible`

### Task 1.2: Capture contract-first red for capability verification

- **Location**: `sympoies/nils-cli` `agent-hook` schemas, evaluator, fixtures,
  and tests
- **Description**: Create v2 test-first evidence and failing tests for
  `execution.read-only.v1`, producer identity/version/digest, cwd/target/argv
  binding, freshness, and fail-closed unknown behavior before production edits.
- **Dependencies**: Task 1.1
- **Complexity**: 5
- **Acceptance criteria**:
  - Meaningful red proves the capability is absent rather than failing on test
    setup.
  - The contract distinguishes `os_enforced`, `tool_contract`, and reserved
    `host_attested` without accepting current permission mode.
  - Missing or mismatched evidence cannot bypass `project-dev`.
- **Validation**:
  - focused failing `cargo test`
  - `test-first-evidence check --phase pre-edit`

### Task 1.3: Implement the capability in shadow mode

- **Location**: `sympoies/nils-cli` `agent-hook` capability schema,
  normalization, evaluator, trace, and Codex/Claude fixtures
- **Description**: Implement strict parsing and verification, request-local
  binding, typed decisions, and privacy-safe trace output. Shadow evaluation
  records comparison evidence but cannot change allow/block behavior yet.
- **Dependencies**: Task 1.2
- **Complexity**: 8
- **Acceptance criteria**:
  - Only trusted same-release producers can construct valid evidence.
  - Codex and Claude normalize equivalent requests to the same decision.
  - Shadow mode has no admission, state, or provider side effect.
  - Unknown and malformed evidence remain fail-closed.
- **Validation**:
  - focused and affected `agent-hook` suites
  - schema/fixture golden tests
  - workspace clippy for affected crates

### Task 1.4: Add tool-owned operation effect descriptors

- **Location**: `sympoies/nils-cli` typed `agent-docs` and `forge-cli` command
  enums plus shared descriptor contract
- **Description**: Export same-release `OperationEffectDescriptor` values for
  the initial exact query-only commands. Keep mutation, output-writing,
  passthrough, plugin, unknown-flag, and general provider-client variants
  unclassified or mutation-capable.
- **Dependencies**: Task 1.3
- **Complexity**: 8
- **Acceptance criteria**:
  - Descriptors originate beside the owning parsed command, not from a runtime-
    kit argv table.
  - Exact supported queries bind executable, release, parsed variant,
    arguments, provider effect, and allowed managed-state reads.
  - `agent-docs` preparation/activation and every provider write return no
    read-only descriptor.
  - Direct `gh`, `glab`, `curl`, passthroughs, plugins, and unknown flags are
    never admitted.
- **Validation**:
  - command-enum exhaustiveness and descriptor tests
  - focused `agent-docs` and `forge-cli` integration suites
  - adversarial flags and executable-shadow fixtures

### Task 1.5: Deliver the capability/descriptor PR

- **Location**: `sympoies/nils-cli`
- **Description**: Commit via `semantic-commit`, deliver without merging, run
  testing, maintainability, security, and API-contract lenses, repair only
  concrete blockers, and merge after provider checks and thread gates pass.
- **Dependencies**: Task 1.3, Task 1.4
- **Complexity**: 4
- **Acceptance criteria**:
  - The PR is merged with exact-head test-first, validation, review, and
    provider evidence.
  - No runtime-kit production behavior changes in this slice.
- **Validation**:
  - affected nils-cli suites and local-fast gate
  - `forge-cli pr deliver --no-merge`
  - one focused specialist gate and `forge-cli pr merge`

## Sprint 2: OS-enforced inspection runner

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: run arbitrary local inspection commands in a verified, bounded,
network-denied sandbox whose complete process tree cannot mutate durable state
on supported backends, while unsupported platforms fail closed without
claiming enforcement.

**Demo/Validation**:

- Command: Linux adversarial conformance plus macOS fail-closed contract tests
- Verify: Linux compound reads succeed while durable writes, network, escape,
  survivors, inherited credentials/fds, and scratch persistence fail; macOS
  returns typed `unavailable` and emits no `os_enforced` descriptor

### Task 2.1: Freeze the common runner and conformance contract

- **Location**: `sympoies/nils-cli` `agent-run`, sandbox backend interface,
  fixtures, and v2 test-first evidence
- **Description**: Add meaningful failing tests for CLI parsing, backend
  availability, durable-root discovery, private ephemeral roots, process-tree
  containment, cleanup, resource bounds, and evidence binding before runner
  implementation.
- **Dependencies**: Task 1.5
- **Complexity**: 7
- **Acceptance criteria**:
  - `agent-run inspect --cwd <path> -- <argv...>` has an exact non-fallback CLI
    contract.
  - Conformance tests prove effects, not backend implementation details.
  - Unsupported/unverifiable backends fail closed with typed diagnostics.
- **Validation**:
  - focused meaningful red on Linux and macOS fixtures where available
  - `test-first-evidence check --phase pre-edit`

### Task 2.2: Implement and deliver the Linux backend

- **Location**: `sympoies/nils-cli` `agent-run` Linux sandbox backend and common
  capability producer
- **Description**: Implement the common runner plus Linux confinement, private
  ephemeral environment, credential/fd hygiene, process/output/time limits,
  cleanup, and `os_enforced` evidence emission. Deliver as its own PR.
- **Dependencies**: Task 2.1
- **Complexity**: 10
- **Acceptance criteria**:
  - The Linux backend passes every common positive and adversarial conformance
    case.
  - Background or descendant processes cannot survive or gain durable/network
    effects.
  - Capability evidence is emitted only after backend enforcement and exact
    request binding are established.
- **Validation**:
  - focused Linux sandbox/conformance suites
  - affected workspace clippy and local-fast gate
  - testing, maintainability, security, and red-team review lenses

### Task 2.3: Validate and deliver typed fail-closed macOS behavior

- **Location**: `sympoies/nils-cli` `agent-run` non-Linux backend boundary and
  cross-platform contract tests
- **Description**: Preserve the same `agent-run inspect` CLI on macOS, but
  return a stable typed `unavailable` result and never emit `os_enforced` while
  the strict backend is unavailable. Record the full macOS backend as a linked
  follow-up instead of weakening the common contract.
- **Dependencies**: Task 2.2
- **Complexity**: 4
- **Acceptance criteria**:
  - macOS accepts the same exact CLI syntax and fails with
    `sandbox-backend-unavailable` plus `EX_UNAVAILABLE`.
  - `operation-effect --format json` returns a typed unavailable envelope and
    never produces an `os_enforced` descriptor on macOS.
  - The hook can route this unavailability to exact-target `project-dev`
    preparation without granting a read-only bypass.
  - A linked follow-up issue owns any future privileged/dedicated-user or VM
    backend and the common contract remains unchanged.
  - Linux conformance remains green.
- **Validation**:
  - focused macOS CLI and operation-effect contract tests
  - cross-platform CI
  - affected workspace clippy and local-fast gate
  - one focused review gate for any delivered nils-cli change

### Task 2.4: Prove end-to-end nils capability behavior

- **Location**: `sympoies/nils-cli` integration fixtures across `agent-run`,
  `agent-hook`, `agent-docs`, and `forge-cli`
- **Description**: Bind both producer families into exact request evaluation
  and prove positive, adversarial, cross-repository, stale-evidence, and
  unsupported-backend decisions without enabling runtime-kit cutover.
- **Dependencies**: Task 1.5, Task 2.2, Task 2.3
- **Complexity**: 6
- **Acceptance criteria**:
  - Compound local reads use `os_enforced` on Linux; macOS returns typed
    `unavailable` and requires the safe preparation route.
  - Managed network/state reads use `tool_contract` on both platforms.
  - A copied descriptor/receipt or activation from another checkout fails.
  - No legacy runtime-kit classifier is needed to establish nils capability
    truth.
- **Validation**:
  - full affected nils-cli test set on Linux and macOS
  - cross-crate integration and doctests

## Sprint 3: Release, pin, and runtime-kit shadow integration

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: consume a released capability through #686's single ingress and
prove parity before changing production admission.

**Demo/Validation**:

- Command: released-surface version readback plus deterministic runtime-kit
  hook comparisons
- Verify: legacy/new decisions agree for retained safe shapes and all mutation,
  unknown, binding, and regression cases before cutover

### Task 3.1: Reconcile the #686 ingress dependency

- **Location**: issue #686, its merged runtime-kit integration, and released
  `agent-hook` contract
- **Description**: Read the live #686 dashboard and provider heads. Proceed
  only when its single runtime-kit ingress and Task 2.4 delivery are merged and
  stable enough to host the new capability rule. Do not reopen #686 design or
  patch its already-delivered lane from #670.
- **Dependencies**: Task 2.4
- **Complexity**: 3
- **Acceptance criteria**:
  - One released, typed `agent-hook` ingress owns runtime-kit evaluation.
  - No competing provider registration or legacy sibling writer is introduced.
  - If #686 is not ready, #670 records this one concrete dependency blocker;
    completed nils work remains valid.
- **Validation**:
  - #686 tracking status/read-back
  - installed `agent-hook --version` and doctor/readback

### Task 3.2: Release the complete nils-cli surface and advance the pin

- **Location**: nils-cli release workflow and runtime-kit version pin/consumer
  surfaces
- **Description**: With fresh maintainer release authorization, publish one
  signed nils-cli release containing both producer families, verify release/tap
  artifacts, then advance the runtime-kit pin and every declared consumer
  through `meta:nils-cli-bump`. Do not activate live runtime homes.
- **Dependencies**: Task 2.4, Task 3.1
- **Complexity**: 6
- **Acceptance criteria**:
  - Released binaries expose the exact schema, descriptor, Linux runner
    enforcement, and macOS fail-closed behavior validated above.
  - Runtime-kit pins and required CLI floors converge through the governed
    bump PR.
  - Installed/isolated readback matches the pinned version; no unreleased debug
    binary is called validated.
- **Validation**:
  - release and package-manager receipts
  - `project-version-baseline`/version-alignment gates
  - runtime-kit pin PR provider checks

### Task 3.3: Add the runtime-kit rule in shadow mode

- **Location**: `graysurf/agent-runtime-kit` versioned hook policy, feedback,
  Codex/Claude fixtures, and deterministic hook tests
- **Description**: Consume `execution.read-only.v1` at the #686 ingress, route
  local exploration to `agent-run inspect`, route managed queries through tool
  contracts, and compare the capability decision with the legacy classifier.
  Shadow results are evidence only and cannot bypass existing production
  admission.
- **Dependencies**: Task 3.1, Task 3.2
- **Complexity**: 8
- **Acceptance criteria**:
  - Equivalent Codex/Claude requests normalize identically.
  - Every mismatch is classified and resolved against the frozen capability
    invariant, never by expanding the legacy allowlist.
  - Unknown feedback offers exactly two finite routes: `agent-run inspect`, or
    prepare `project-dev` for the exact target and rerun.
  - Mutation and finish-line regression fixtures remain green.
- **Validation**:
  - meaningful red and v2 test-first pre-edit check
  - focused hook/policy/runtime-smoke cases
  - `bash tests/hooks/run.sh`
  - full `bash scripts/ci/all.sh` against the pinned release

### Task 3.4: Deliver the runtime-kit shadow PR

- **Location**: `graysurf/agent-runtime-kit`
- **Description**: Deliver the shadow integration independently. Run testing,
  maintainability, security, and data-migration lenses; merge only after parity
  evidence, provider checks, and thread gates converge.
- **Dependencies**: Task 3.3
- **Complexity**: 4
- **Acceptance criteria**:
  - Shadow integration is merged without deleting or bypassing legacy
    production behavior.
  - All comparison gaps have an explicit invariant-based disposition.
- **Validation**:
  - declared project gates
  - one focused specialist gate
  - exact-head provider merge read-back

## Sprint 4: Cut over, remove heuristics, and close

**PR grouping intent**: `group`
**Execution Profile**: `serial`

**Goal**: make capability evidence the sole read-only bypass, delete the legacy
classifier, prove regression safety, and complete strict L2 closeout.

**Demo/Validation**:

- Command: full hook/CI stack plus isolated disposable Codex/Claude acceptance
- Verify: reads use capability producers; mutation/unknown still require exact
  preparation; the four legacy surfaces no longer participate in production

### Task 4.1: Cut over and delete the legacy classifier

- **Location**: `core/hooks/shared/pre-edit-intent-gate.py`, versioned
  `agent-hook` policy, product fixtures, docs, and tests
- **Description**: Make valid capability evidence the only read-only bypass and
  remove `READ_ONLY_EXECUTABLES`, `READ_ONLY_GIT_SUBCOMMANDS`,
  `GH_READ_ONLY_SUBCOMMANDS`, `simple_shell_words`, and their production
  decision path. Retain only migration history needed by tests/docs.
- **Dependencies**: Task 3.4
- **Complexity**: 9
- **Acceptance criteria**:
  - No runtime-kit argv allowlist or raw shell-word parser can authorize a read.
  - Valid `os_enforced` and `tool_contract` evidence admits only the exact bound
    request.
  - Known mutation and unknown require exact target `project-dev` preparation.
  - All positive, adversarial, and regression acceptance cases pass on Codex
    and Claude fixtures.
- **Validation**:
  - focused meaningful red/pre-edit evidence
  - `bash tests/hooks/run.sh`
  - deterministic runtime-smoke
  - `bash scripts/ci/all.sh`

### Task 4.2: Deliver, review, and merge the cutover PR

- **Location**: runtime-kit PR and issue #670 checkpoints
- **Description**: Deliver without merge, run one focused gate with testing,
  maintainability, security, and red-team lenses, repair only blocking findings,
  post the issue review checkpoint, and merge after all provider gates pass.
- **Dependencies**: Task 4.1
- **Complexity**: 5
- **Acceptance criteria**:
  - Exact-head validation and review evidence are complete.
  - No unresolved non-outdated thread, unchecked task, current-head change
    request, or provider check remains.
  - Repeated review on an unchanged head creates no duplicate review/thread.
- **Validation**:
  - `forge-cli pr deliver --no-merge`
  - specialist review outcome and current-head read-back
  - `plan-issue tracking checkpoint --post state,review`
  - `forge-cli pr merge`

### Task 4.3: Prove deploy readiness without live activation

- **Location**: released nils-cli, merged runtime-kit main, isolated runtime
  homes, and dry-run sync
- **Description**: Verify installed/pinned/source convergence and run isolated
  or disposable Codex/Claude acceptance. Stop before any live-home `--apply`
  unless fresh maintainer deployment authorization is present.
- **Dependencies**: Task 4.2
- **Complexity**: 5
- **Acceptance criteria**:
  - Isolated acceptance proves Linux compound reads, macOS typed unavailability,
    managed queries, mutation blocks, and cross-repository binding.
  - Dry-run sync reports an actionable, reversible update.
  - No live runtime home changes without fresh approval.
- **Validation**:
  - version and doctor readback
  - isolated product/runtime smoke
  - `scripts/sync-runtime-surfaces.sh` dry-run

### Task 4.4: Strict tracker closeout and archive handoff

- **Location**: issue #670, plan run state, provider read-back, and plan archive
- **Description**: Finalize every ledger row and linked PR, require
  `tracking close-ready --expect-visible` to return ready with no blockers,
  close through the tracking profile, audit the closed issue, run archive
  discovery/migration dry-run, and perform safe terminal worktree cleanup.
- **Dependencies**: Task 4.3
- **Complexity**: 4
- **Acceptance criteria**:
  - All tasks and required PRs are terminal with validation/review evidence.
  - #670 closes only after strict readiness and provider read-back pass.
  - Archive apply remains explicit-confirmation-gated.
  - Local cleanup is completed only with provider head proof; ambiguous state
    is retained and reported.
- **Validation**:
  - `plan-issue tracking close-ready --profile tracking --expect-visible`
  - `plan-issue record close --profile tracking`
  - closed issue read-back plus `plan-issue record audit --expect-visible`
  - `plan-archive discover` and migration dry-run

## Testing strategy

- Capability unit/property tests cover schema versioning, exact producer
  identity, release/digest binding, target/cwd/argv binding, freshness,
  copied/forged evidence, and closed-enum exhaustiveness.
- Descriptor tests exhaust every typed `agent-docs` and `forge-cli` command
  variant so additions default to unknown until the owner classifies them.
- Common sandbox conformance proves observable write/network/process/resource
  effects on Linux. macOS contract tests prove the same CLI fails closed with
  typed unavailability and cannot emit enforcement evidence; a future backend
  must pass the unchanged common conformance suite before enablement.
- Runtime-kit tests compare legacy and capability decisions in shadow, then
  prove the legacy path is absent after cutover. Codex and Claude fixtures must
  agree semantically.
- Full repository gates, exact-head provider checks, independent specialist
  review, and disposable runtime acceptance close the integration boundary.

## Risks and gotchas

- A launcher promise is not enforcement: evidence is valid only after the
  backend establishes containment and binds the exact request.
- A writable inherited fd, linked Git admin path, helper process, background
  child, or mutable state socket can violate read-only despite a read-only
  mount; conformance must test all of them.
- Networked managed queries cannot be solved by allowing arbitrary network in
  `agent-run inspect`; tool contracts remain exact and owner-defined.
- Descriptor exhaustiveness must fail closed when command enums gain variants.
- Apple public unprivileged primitives do not currently provide strict
  descendant containment plus job-local hard process and aggregate-memory
  bounds. Keep that work in the linked follow-up rather than silently degrading
  `execution.read-only.v1`.
- #686 may advance while nils work is underway. Re-read its provider state at
  Task 3.1 and integrate only through its merged ingress; do not cherry-pick or
  edit its active delivery branch.
- Shadow mode must not become a permanent dual authority. It exists only to
  validate migration before the cutover PR.
- Re-running delivery must not restart broad review. Use current-head review
  read-back, #673 idempotency, targeted repair, and the explicit stop rule.

## Rollback plan

- Before cutover, keep an unsupported OS backend disabled and return a typed
  unavailable result; never fall back while claiming read-only capability.
- A released descriptor or runner defect receives a corrective nils-cli
  release. Runtime-kit does not advance its pin until the corrected surface is
  verified.
- If shadow parity fails, retain the current legacy admission path, record the
  concrete mismatch, and repair the capability producer/consumer; do not grow
  the allowlist.
- After cutover, revert the runtime-kit cutover PR to restore the last released
  legacy policy while keeping unused nils capability code in place. Re-enable
  only after the failed acceptance boundary is repaired and targeted review
  passes.
