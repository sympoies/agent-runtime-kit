# Plan: Separate nils-cli compatibility floor from validated pin

## Overview

Replace the single exact nils-cli pin role with a compatibility floor plus an
exact validated release. A newer admitted local host must reach behavioral
validation, while CI continues to prove the exact minimum and exact validated
surfaces and packaging remains checksum-bound to the validated release.

This is one serial cross-repository L2 delivery. `sympoies/nils-cli` first ships
schema-v2 doctor behavior; after an explicitly authorized release,
`graysurf/agent-runtime-kit` consumes it, migrates CI and packaging, and closes
only after provider-visible minimum/validated/canary evidence is complete.

## Read First

- Primary source: `docs/plans/2026-07-19-nils-cli-version-policy/nils-cli-version-policy-discussion-source.md`
- Source type: `discussion-to-implementation-doc`
- Execution state: `docs/plans/2026-07-19-nils-cli-version-policy/nils-cli-version-policy-execution-state.md`
- Runtime-kit policy: `AGENTS.md`, `DEVELOPMENT.md`,
  `core/policies/work-tier-levels.md`, `core/policies/git-delivery.md`,
  `core/policies/evidence-control-plane.md`, and
  `docs/source/docs-placement-retention-policy-v1.md`
- Historical rationale: archived plan
  `2026-05-24-nils-cli-version-alignment` and adoption follow-up
- Open questions carried into execution: none; nils-cli release, Homebrew
  changes, live runtime synchronization, and archive apply remain their normal
  explicit approval boundaries

## Scope

- In scope: nils-cli doctor manifest schema v2 and v1 compatibility;
  runtime-kit manifest/mirror migration; minimum and validated blocking CI;
  visible latest-stable canary; ambient local-host admission; exact validated
  Docker/checksum ownership; bump/baseline skill updates; deterministic
  acceptance; release/pin ordering; governed review, delivery, closeout, and
  archive handoff.
- Out of scope: blind compatibility claims for every newer release; weakening
  per-binary floors; ambient-version Docker builds; automatic minimum moves;
  unrelated audit-drift or hook-marker defects; hook/session plans #686/#676;
  any release, installed-runtime mutation, or archive apply without the owning
  workflow's explicit authorization.

## Execution Model

- Work tier: L2, one plan-tracking issue in `graysurf/agent-runtime-kit`.
- Ordering: plan bundle and tracker -> nils-cli meaningful red and schema v2 ->
  nils-cli PR/review/merge -> explicit release -> runtime-kit meaningful red and
  migration -> runtime-kit PR/review/merge -> optional separately authorized
  runtime synchronization -> strict closeout and archive handoff.
- Planned implementation branches:
  `feat/nils-cli-version-policy` in nils-cli and
  `feat/nils-cli-version-policy` in runtime-kit. The current runtime-kit branch
  begins as the plan-authoring branch and may be retained for implementation
  only after the next session reconciles tracker state and confirms it is clean.
- Use managed worktrees. Run cross-repository mutations with the target
  repository as CWD. Provider-visible evidence must use repository-relative
  paths and public issue/PR links, not machine-local state paths.
- Independent reviewer agents inspect exact heads only during the delivery
  phase; the implementation remains serial because the schema/release/pin
  dependencies cannot be parallelized safely.

## Invariants

1. `minimum_supported_tag` controls compatibility admission; `validated_tag`
   controls exact reproducibility. Neither field may silently substitute for the
   other.
2. Below-minimum or below any `required_clis` floor remains a hard block.
3. Above-validated is admitted with an explicit warning and must still run
   downstream behavioral validation.
4. Docker images, release SHA256 values, generated snapshots, and formal
   validated claims always bind the exact validated tag.
5. Schema v1 preserves exact `pinned_tag` semantics.
6. Minimum and validated CI roles remain visible even when their tags are equal.
7. The minimum moves only by explicit compatibility retirement; ordinary
   release uptake moves validated state only.
8. Local scripts do not implement semantic-version comparison; nils-cli owns the
   stable comparison and doctor contract.

## Sprint 1: Establish the tracker and test-first contract

**Goal**: Publish the complete L2 contract and capture meaningful red for the
upstream schema behavior before production edits.

**PR grouping intent**: `group`

**Execution Profile**: serial

### Task 1.1: Commit the plan bundle and initialize the L2 tracker

- **Location**:
  - `docs/plans/2026-07-19-nils-cli-version-policy/nils-cli-version-policy-discussion-source.md`
  - `docs/plans/2026-07-19-nils-cli-version-policy/nils-cli-version-policy-plan.md`
  - `docs/plans/2026-07-19-nils-cli-version-policy/nils-cli-version-policy-execution-state.md`
- **Description**: Validate the bundle, open one plan-tracking issue through
  `plan-issue record open --profile tracking`, initialize its private run state,
  and verify visible source/plan/state records. A provider-supported immutable
  dirty-hash snapshot may establish the tracker when the current checkout lease
  prevents staging, but the bundle must be committed before Task 1.2. Do not
  open an implementation PR or modify product code in this authoring task.
- **Dependencies**:
  - none
- **Complexity**: 3
- **Acceptance criteria**:
  - One validated three-file bundle is provider-visible on one L2 tracker with
    a committed identity or provider-supported immutable dirty-hash identity.
  - The bundle is committed before Task 1.2 production work begins.
  - `tracking status --expect-visible` recognizes the tracker and run state.
  - The next selected task remains Task 1.1 until the bundle commit exists, then
    advances to Task 1.2; no implementation/release/live apply occurs during
    plan authoring.
- **Validation**:
  - `plan-tooling validate --file`
    `docs/plans/2026-07-19-nils-cli-version-policy/nils-cli-version-policy-plan.md`
    `--format text --explain`
  - `git diff --check`
  - `plan-issue tracking status --expect-visible --format json`

### Task 1.2: Freeze schema-v2 behavior and capture nils-cli meaningful red

- **Location**:
  - `sympoies/nils-cli/crates/agent-runtime/src/doctor/version_alignment.rs`
  - `sympoies/nils-cli/crates/agent-runtime/src/doctor.rs`
  - `sympoies/nils-cli/crates/agent-runtime/tests/integration/doctor_version_alignment.rs`
  - private nils-cli test-first evidence directory
- **Description**: Document the v1/v2 manifest compatibility matrix and create
  failing tests for minimum, validated, ahead-warning, required-CLI,
  invalid-relationship, and malformed-tag behavior before production edits.
  Declare affected existing doctor/parser/snapshot tests and their retained or
  changed invariants.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 5
- **Acceptance criteria**:
  - The versioned contract defines field semantics, validation rules, check IDs,
    warning/block exit behavior, and v1 compatibility.
  - Meaningful red fails because schema-v2 behavior is absent, not due to setup,
    compilation, network, or unrelated failure.
  - Test-first pre-edit verification passes before doctor production edits.
- **Validation**:
  - focused failing nils-cli doctor/version-policy tests
  - `test-first-evidence check --phase pre-edit --format json`

## Sprint 2: Implement and release nils-cli schema v2

**Goal**: Ship the stable comparison and doctor contract needed by runtime-kit.

**PR grouping intent**: `group`

**Execution Profile**: serial in one managed nils-cli worktree

### Task 2.1: Implement manifest parsing, comparison, and typed diagnostics

- **Location**:
  - `sympoies/nils-cli/crates/agent-runtime/src/doctor/version_alignment.rs`
  - `sympoies/nils-cli/crates/agent-runtime/src/doctor.rs`
  - `sympoies/nils-cli/crates/agent-runtime/tests/integration/doctor_version_alignment.rs`
- **Description**: Add schema-v2 `minimum_supported_tag` and `validated_tag`
  support, reject invalid relationships, preserve schema-v1 exact behavior, and
  emit stable text/JSON checks. Above-validated produces a warning with
  compatibility-not-validated wording; below-minimum and required-CLI misses
  block. Keep semantic-version logic in the shared nils-cli owner.
- **Dependencies**:
  - Task 1.2
- **Complexity**: 8
- **Acceptance criteria**:
  - The full truth table in the discussion source is covered.
  - Prerelease/build metadata and malformed tags are deterministic.
  - Schema v1 exact fixtures remain byte/semantics compatible where declared.
  - Warnings leave exit status non-blocking when `block=0`.
- **Validation**:
  - focused doctor/parser tests
  - affected nils-cli test suites and snapshots
  - affected clippy, docs, and completion audits

### Task 2.2: Review, deliver, merge, and release the nils-cli capability

- **Location**:
  - nils-cli implementation PR and release workflow
- **Description**: Complete test-first evidence, run the repository gate,
  deliver the feature PR, perform independent pre-merge review, converge provider
  checks/threads, merge, and only then request fresh authorization for the exact
  nils-cli release. Verify the published tag and binary behavior without
  changing runtime-kit or installed runtime homes yet.
- **Dependencies**:
  - Task 2.1
- **Complexity**: 6
- **Acceptance criteria**:
  - Provider merge truth matches the reviewed head.
  - A tagged release containing schema-v2 behavior is published only after
    explicit release authorization.
  - Published artifacts pass v1 exact and v2 fixture probes.
- **Validation**:
  - nils-cli repository full gate
  - provider checks, review summaries, threads, and merge read-back
  - released-binary doctor probes for schema v1 and v2

## Sprint 3: Consume the split policy in runtime-kit

**Goal**: Make local newer-host development work while preserving exact minimum,
validated, and packaging evidence.

**PR grouping intent**: `group`

**Execution Profile**: serial after the released nils-cli capability exists

### Task 3.1: Capture runtime-kit meaningful red and migrate the manifest

- **Location**:
  - `docs/source/nils-cli-pin.yaml`
  - `docs/source/nils-cli-minimum-digest.yaml`
  - `tests/runtime-smoke/acceptance-matrix.yaml`
  - `tests/runtime-smoke/run.sh`
  - `scripts/ci/security-hardening-audit.py`
  - `scripts/ci/version-baseline-audit.py`
  - private runtime-kit test-first evidence directory
- **Description**: Add failing runtime-kit acceptance for below-minimum block,
  exact-role passes, ahead warning plus downstream sentinel execution, malformed
  policy, equal-tag de-duplication, and validated checksum ownership. Then migrate
  the manifest to schema v2 using the released nils-cli contract.
- **Dependencies**:
  - Task 2.2
- **Complexity**: 6
- **Acceptance criteria**:
  - Meaningful red proves current exact-only behavior cannot satisfy the new
    admission contract.
  - The manifest migration names both roles and binds checksums to validated.
  - No per-binary floor is weakened or removed.
- **Validation**:
  - focused red/green version-policy fixtures
  - `test-first-evidence check --phase pre-edit --format json`
  - released schema-v2 doctor against the migrated manifest

### Task 3.2: Add ambient, minimum, validated, and canary execution paths

- **Location**:
  - `scripts/ci/all.sh`
  - `.github/workflows/ci.yml`
  - `.github/workflows/nils-cli-latest-canary.yml`
  - `scripts/ci/nils-cli-policy-matrix.py`
  - `scripts/dev/with-nils-version.sh`
  - `tests/ci/test_nils_cli_version_policy.py`
  - runtime-smoke acceptance fixtures
- **Description**: Let local `all.sh` proceed on an admitted ambient host;
  execute blocking exact minimum and validated roles in provider CI; de-duplicate
  equal tags while preserving role output; and add a visible latest-stable
  canary that never mutates policy. Ensure an ahead host reaches a downstream
  sentinel and an incompatible newer fixture fails there.
- **Dependencies**:
  - Task 3.1
- **Complexity**: 8
- **Acceptance criteria**:
  - Local host >= minimum no longer stops solely for being above validated.
  - CI always proves minimum and validated roles.
  - Latest canary reports its resolved version and failure artifact/check.
  - Network/canary failure does not masquerade as compatibility success.
- **Validation**:
  - workflow/parser fixture tests for distinct and equal tags
  - below/minimum/validated/ahead/incompatible scenario matrix
  - deterministic runtime smoke

### Task 3.3: Preserve validated packaging and update every policy mirror

- **Location**:
  - `.github/workflows/publish-image.yml`
  - `docker/build.sh`
  - `docker/Dockerfile`
  - `scripts/ci/security-hardening-audit.py`
  - `scripts/ci/version-baseline-audit.py`
  - `README.md`
  - `docs/source/nils-cli-surface.md`
  - `docs/source/nils-cli-version-workflows.md`
  - `docs/source/harness-shape-codex.md`
  - `docs/source/harness-shape-claude.md`
  - `docs/source/harness-shape-hermes.md`
  - `.agents/skills/project-version-baseline/SKILL.md`
  - `core/skills/meta/nils-cli-bump/SKILL.md.tera` and rendered/golden surfaces
- **Description**: Route every artifact-producing consumer to `validated_tag`
  and its digests; display both floor and validated state in human mirrors; and
  revise bump/version-baseline workflows so validated moves routinely while the
  floor moves only by explicit retirement. Refresh generated outputs only with
  the declared exact role that owns them.
- **Dependencies**:
  - Task 3.2
- **Complexity**: 8
- **Acceptance criteria**:
  - Docker/publish dry-runs use validated tag and matching digests.
  - Baseline audit rejects either-role mirror drift.
  - Bump guidance never auto-moves minimum or calls an ahead host validated.
  - Codex, Claude, and Hermes rendered/golden guidance agrees.
- **Validation**:
  - `docker/build.sh --dry-run`
  - `python3 scripts/ci/security-hardening-audit.py`
  - `python3 scripts/ci/version-baseline-audit.py check`
  - render/golden and skill-governance checks

### Task 3.4: Review, deliver, merge, and verify runtime-kit

- **Location**:
  - runtime-kit implementation PR and L2 tracker
- **Description**: Complete the affected/full validation matrix, deliver the
  PR without merging, run required independent review, disposition native
  summaries/threads/tasks, post the issue-side review checkpoint, merge through
  `forge-cli`, and read back provider main. Do not synchronize installed runtime
  homes unless separately authorized after merge.
- **Dependencies**:
  - Task 3.3
- **Complexity**: 7
- **Acceptance criteria**:
  - Full CI and hook suites pass using the released schema-v2 nils-cli.
  - Minimum, validated, and canary evidence is linked from the tracker.
  - Provider merge SHA and main read-back are consistent.
  - No unauthorized Homebrew or live runtime mutation occurred.
- **Validation**:
  - `bash scripts/ci/all.sh`
  - `bash tests/hooks/run.sh`
  - provider checks, reviews, threads, tasks, merge, and main read-back

## Sprint 4: Close out and archive

**Goal**: Prove the new policy is durable, finish optional approved activation,
and close the L2 lifecycle without local ambiguity.

**PR grouping intent**: `per-sprint`

**Execution Profile**: serial

### Task 4.1: Run post-merge acceptance and optional authorized activation

- **Location**:
  - merged runtime-kit main and isolated/runtime acceptance artifacts
- **Description**: Re-run bounded post-merge probes for admitted ahead host,
  exact minimum, exact validated, and packaging identity. If the maintainer
  separately authorizes runtime synchronization, apply and verify through the
  normal sync workflow; otherwise record activation as not requested and do not
  block policy closeout unless the plan's delivered behavior requires it.
- **Dependencies**:
  - Task 3.4
- **Complexity**: 4
- **Acceptance criteria**:
  - Post-merge source and provider main match.
  - The four declared policy roles produce the expected results.
  - Any live apply has explicit authorization and verified receipts; otherwise
    no installed runtime was changed.
- **Validation**:
  - released doctor scenario matrix
  - exact validated packaging dry-run
  - optional approved runtime doctors/receipts only when activated

### Task 4.2: Audit, close, archive, and clean local worktrees

- **Location**:
  - L2 tracker, plan archive, and managed worktrees
- **Description**: Finalize every ledger row, post state/validation/review
  evidence, require strict `tracking close-ready --expect-visible`, close through
  `plan-issue record close`, read back and audit provider evidence, run archive
  discovery/migration dry-run, apply only with explicit archive authorization,
  then perform exactly-once local cleanup under provider merge/head proof.
- **Dependencies**:
  - Task 4.1
- **Complexity**: 5
- **Acceptance criteria**:
  - Close-ready reports `ready=true` and no blockers.
  - Closed provider state and labels read back correctly.
  - Archive routing is reported truthfully and applied only if authorized.
  - Dirty, locked, or unverifiable worktrees are retained; eligible worktrees and
    matching disposable branches are cleaned separately and safely.
- **Validation**:
  - `plan-issue tracking close-ready --expect-visible --format json`
  - `plan-issue record audit --profile tracking --expect-visible --format json`
  - `plan-archive discover --format json`
  - provider and local cleanup read-back

## Issue Closeout Gate

The tracker may close only when both repositories' required work is merged, the
nils-cli schema-v2 release is provider-proven, runtime-kit minimum and validated
blocking lanes are green, the latest canary has visible terminal evidence, exact
validated packaging is proven, required reviews/threads/tasks are converged, the
ledger is complete, and strict close-ready returns no blockers. A skipped live
runtime apply is acceptable only when it was never authorized or required; it
must be stated explicitly rather than implied complete.
