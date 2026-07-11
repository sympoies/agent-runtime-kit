# Plan: Implement the Intent-Level Skill Exposure Contract

## Overview

Implement #561 as the architecture and enforcement substrate for #562. The
delivery is sequential across two repositories: first release typed skills
manifest v2 support from nils-cli, then consume that release in runtime-kit,
migrate the live manifest to v2, seed the 66-skill pending disposition ledger,
and prove governance/render/install parity.

The plan intentionally does not add a metadata-only opt-in profile. Active v2
skills use honest `default` exposure; advanced skills remain unavailable until a
future cross-product install mechanism exists. Current skills remain visibly
discoverable through an explicit frozen pending-disposition set until #562 replaces
each pending disposition.

## Read First

- Primary source: `docs/plans/2026-07-11-skill-exposure-contract/skill-exposure-contract-discussion-source.md`
- Source type: discussion-to-implementation-doc
- Owning architecture issue: `graysurf/agent-runtime-kit#561`
- Downstream migration issue: `graysurf/agent-runtime-kit#562`
- Runtime-kit schema/governance: `core/docs/schemas/skills.schema.json`, `manifests/skills.yaml`, `scripts/ci/skill-governance-audit.sh`
- nils-cli parser/renderer: `crates/agent-runtime/src/render/manifest.rs`, `crates/agent-runtime/src/render/writer.rs`, `crates/agent-runtime/src/commands/list_skills.rs`
- Open questions carried into execution: none

## Scope

- In scope: nils-cli v2 parser/validation/reporting plus release; runtime-kit v2
  schema/live migration, frozen pending baseline, pending disposition manifest,
  admission governance, product documentation, fixtures, render/install/stale
  validation, PR delivery, merge, and plan closeout.
- Out of scope: final 66-skill dispositions and agent-only behavior migrations,
  optional installation profiles, Browser/Evidence migration, or private host
  configuration.

## Sprint 1: Freeze the L2 record and upstream contract

**Goal**: establish durable tracking and a linked nils-cli implementation record
before production changes.

### Task 1.1: Open and initialize the runtime-kit plan tracker

- **Location**: this plan bundle and provider plan-tracking issue
- **Description**: validate and commit the bundle, open the tracking issue with
  source/plan/initial-state evidence, initialize run state, and link #561/#562.
- **Dependencies**: none
- **Acceptance criteria**: plan validation passes; source, plan, and state roles
  are provider-visible and audit-clean; run state reconciles.
- **Validation**: `plan-tooling validate`; `plan-issue tracking status --expect-visible`.

### Task 1.2: Open the linked nils-cli follow-up

- **Location**: `sympoies/nils-cli` provider issue
- **Description**: record the parser/schema/reporting dependency, link runtime-kit
  #561 and the plan tracker, and constrain the work to deterministic primitives.
- **Dependencies**: Task 1.1
- **Acceptance criteria**: one public-safe issue exists with implementation and
  release acceptance criteria.
- **Validation**: provider read-back through `forge-cli issue view`.

## Sprint 2: Implement and release nils-cli manifest v2 support

**Goal**: ship a backward-compatible released primitive that runtime-kit can pin.

### Task 2.1: Capture failing parser and contract tests

- **Location**: nils-cli `crates/agent-runtime`
- **Description**: add tests proving the current parser rejects skills schema v2
  and lacks deterministic invocation/exposure metadata reporting. Record
  fail-first evidence before production edits.
- **Dependencies**: Task 1.2
- **Acceptance criteria**: focused tests fail for the intended missing behavior,
  not fixture/setup errors.
- **Validation**: focused `cargo test` command retained in test-first evidence.

### Task 2.2: Add per-manifest versioning and typed v2 validation

- **Location**: nils-cli manifest model/loading modules
- **Description**: preserve v1 compatibility, allow skills v2 without changing
  unrelated manifest versions, parse invocation/exposure/migration metadata, and
  reject invalid combinations with stable errors.
- **Dependencies**: Task 2.1
- **Acceptance criteria**: v1 unchanged; v2 valid cases load; unknown internal,
  advanced/default, unsupported opt-in, unbounded compatibility, and invalid
  pending-disposition membership fail closed.
- **Validation**: focused unit/integration tests.

### Task 2.3: Add deterministic metadata reporting and compatibility coverage

- **Location**: nils-cli `agent-runtime list-skills`, renderer tests, fixtures
- **Description**: report semantic role, parent intents, exposure, and pending-disposition
  state for each installed skill while preserving the existing output contract
  compatibly; prove retired-output reconciliation still works under v2.
- **Dependencies**: Task 2.2
- **Acceptance criteria**: Codex/Claude/Hermes reports agree; v1 reports remain
  accepted; v2 metadata is deterministic; removal cleanup regression passes.
- **Validation**: focused list/render integration tests.

### Task 2.4: Validate, review, deliver, and release nils-cli

- **Location**: nils-cli repo and release surfaces
- **Description**: run repo-declared validation, specialist review, deliver and
  merge the PR, release the next nils-cli version, and verify the released
  binaries expose the contract.
- **Dependencies**:
  - Task 2.2
  - Task 2.3
- **Acceptance criteria**: PR merged after review; release published; installed
  released binary passes version/help and focused fixture checks.
- **Validation**: nils-cli declared full validation plus release read-back.

## Sprint 3: Consume v2 in runtime-kit

**Goal**: make #561's contract live, governed, and ready for #562's migration.

### Task 3.1: Add runtime-kit v2 and disposition schemas

- **Location**: `core/docs/schemas/skills.schema.json`, new disposition schema
- **Description**: define semantic role, intents, example request, admission
  rationale, default exposure, compatibility lifecycle, frozen pending migration,
  and pending/reviewed destination vocabulary.
- **Dependencies**: Task 2.4
- **Acceptance criteria**: positive and negative schema fixtures cover every
  required combination; no valid active internal or unsupported opt-in shape.
- **Validation**: schema/governance fixture tests.

### Task 3.2: Migrate live manifests and seed the #562 ledger

- **Location**: `manifests/skills.yaml`, new skill disposition manifest
- **Description**: move skills manifest to v2, freeze exactly the current 66 IDs
  as pending-disposition under #562, and seed one pending disposition row per ID.
- **Dependencies**: Task 3.1
- **Acceptance criteria**: active/source/plugin/render inventories remain exactly
  aligned; no skill is hidden or removed; pending baseline cannot grow.
- **Validation**: governance audit and deterministic ID/count checks.

### Task 3.3: Enforce retained-skill admission and migration integrity

- **Location**: `scripts/ci/skill-governance-audit.sh` and fixtures
- **Description**: require metadata for every non-pending v2 entry, reject thin
  wrappers/bookkeeping/child phases without an encoded direct-user exception,
  validate compatibility lifecycle, and cross-check active/pending/disposition
  sets.
- **Dependencies**: Task 3.2
- **Acceptance criteria**: requested negative fixtures fail for stable reasons;
  create/remove lifecycle fixtures use v2 correctly; #562 pending rows are
  complete.
- **Validation**: governance repo/create/remove plus new admission fixtures.

### Task 3.4: Refresh product diagnostics, docs, renders, and goldens

- **Location**: product support docs, runtime-smoke expectations, rendered builds,
  goldens, nils-cli pin/surface docs
- **Description**: pin the released nils-cli, document filesystem discovery and
  the default-only exposure decision, refresh deterministic diagnostics and
  generated artifacts, and prove stale managed skills are removable without
  touching private/operator roots.
- **Dependencies**:
  - Task 3.1
  - Task 3.2
  - Task 3.3
- **Acceptance criteria**: Codex/Claude/Hermes report equivalent metadata or an
  explicit tested exception; generated and installed inventories agree.
- **Validation**: render/golden/drift/install/runtime-smoke/stale-prune checks.

## Sprint 4: Validate, review, deliver, and close

**Goal**: merge runtime-kit #561 with strict L2 lifecycle evidence and leave a
clear #562 handoff.

### Task 4.1: Run declared validation

- **Location**: runtime-kit repo-wide
- **Description**: run focused checks during repair, then the full project-dev
  contract against the released pinned nils-cli.
- **Dependencies**:
  - Task 3.4
- **Acceptance criteria**: `bash scripts/ci/all.sh` and `bash
  tests/hooks/run.sh` pass on pin.
- **Validation**: retained command logs and lifecycle validation checkpoint.

### Task 4.2: Run mandatory specialist review and converge findings

- **Location**: runtime-kit PR diff
- **Description**: run testing and maintainability lenses plus any risk-selected
  lenses, post native review events in required order, repair findings, and
  sweep every review thread/task.
- **Dependencies**: Task 4.1
- **Acceptance criteria**: combined approval, no unresolved thread, no unchecked
  task, and issue-side review evidence recorded before merge.
- **Validation**: provider review read-back and affected-lens reruns.

### Task 4.3: Merge, close the tracker, and complete #561

- **Location**: runtime-kit PR, plan tracker, #561
- **Description**: merge through `forge-cli`, pass close-ready, run canonical
  plan-tracking closeout, commit terminal execution state as required, and ensure
  #561 is closed by the delivered PR or explicit follow-up.
- **Dependencies**: Task 4.2
- **Acceptance criteria**: PR merged; plan tracker closed and audit-clean; #561
  closed; no required task pending.
- **Validation**: provider PR/issue read-back and `record audit --expect-visible`.

### Task 4.4: Reassess #562 against the landed contract

- **Location**: runtime-kit issue #562
- **Description**: compare #562's taxonomy, inventory, intent, hook, and migration
  design to the actual v2 implementation. Record any required design changes and
  whether implementation can proceed.
- **Dependencies**: Task 4.3
- **Acceptance criteria**: evidence-backed ready/blocked decision; any necessary
  #562 edits or follow-up comment posted without duplicating #561 ownership.
- **Validation**: provider read-back of #562 and landed main files.

## Testing Strategy

- Test-first evidence for both repositories before production edits.
- nils-cli focused parser/validation/list/render tests, then its declared full
  gate.
- Runtime-kit schema and governance negative fixtures, renderer/golden/drift,
  deterministic three-product list/install/stale cleanup, full CI, and hooks.
- Mandatory provider-native specialist review for both delivered PRs.
- Strict plan-tracking lifecycle audit and close-ready before tracker close.

## Rollback Plan

- Runtime-kit can return `manifests/skills.yaml` to schema v1 while the released
  nils-cli retains additive v1/v2 compatibility.
- The pending disposition manifest and governance can be reverted without
  changing installed skill behavior.
- No user-facing skill is removed by #561; #562 owns later removals and their
  replacement verification.
