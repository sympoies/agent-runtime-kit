# Plan: Strengthen Test-First Discipline for Durable Tests

## Overview

Upgrade the test-first contract across nils-cli and agent-runtime-kit so evidence
proves more than a non-zero command followed by green. The implementation adds a
versioned contract/test-impact ledger, meaningful-red evidence, multiple scoped
validations, explicit legacy handling, stronger engineering guidance, and
review/runtime-smoke enforcement while keeping the forge gate opt-in.

## Read First

- Primary source: `docs/plans/2026-07-11-durable-test-first-discipline/durable-test-first-discipline-discussion-source.md`
- Source type: discussion-to-implementation-doc
- Current runtime-kit contract: `core/skills/evidence/test-first-evidence/SKILL.md.tera`
- Current nils-cli record: `crates/agent-workflow-primitives/src/test_first_evidence.rs` in `sympoies/nils-cli`
- Open questions carried into execution: none

## Scope

- In scope: evidence record v2, legacy-v1 diagnostics, strict forge consumption,
  nils-cli release, runtime-kit pin/skill/reviewer/guided-flow updates,
  deterministic acceptance coverage, documentation, review, delivery, and L2
  closeout.
- Out of scope: enabling the gate by default, global coverage thresholds,
  mandatory mutation testing, retroactive migration of historical evidence, or
  generic framework-specific test discovery.

## Sprint 1: Freeze The Contract And Upstream Work

**Goal**: establish an audit-clean L2 tracker and a linked nils-cli
implementation record before production changes.

### Task 1.1: Open and initialize the runtime-kit plan tracker

- **Location**: this plan bundle and the provider plan-tracking issue
- **Description**: validate and commit source/plan/state, open the tracker with
  frozen snapshots, initialize run state, and verify provider-visible integrity.
- **Dependencies**: none
- **Acceptance criteria**: the bundle validates; source, plan, and state roles
  are visible; the issue read-back audit passes; the execution state records the
  tracker URL.
- **Validation**: `plan-tooling validate`; plan-issue dry-run, live open,
  read-back, and `record audit --expect-visible`.

### Task 1.2: Open the linked nils-cli implementation issue

- **Location**: `sympoies/nils-cli` provider issue
- **Description**: capture the released deterministic primitive scope, v1/v2
  compatibility decision, strict forge consumer, tests, and release boundary;
  link the runtime-kit tracker.
- **Dependencies**: Task 1.1
- **Acceptance criteria**: exactly one public-safe upstream issue exists with
  implementation-ready requirements and reciprocal links.
- **Validation**: provider issue read-back through `forge-cli issue view`.

### Task 1.3: Freeze evidence v2 fixtures and error taxonomy

- **Location**:
  - nils-cli `crates/agent-workflow-primitives/src/test_first_evidence.rs`
  - nils-cli `crates/agent-workflow-primitives/src/test_first_evidence/cli.rs`
  - nils-cli `crates/agent-workflow-primitives/tests/integration/test_first_evidence/`
- **Description**: turn the source document's contract delta, test-impact
  dispositions, meaningful-red, validation scopes, waiver debt, residual gaps,
  legacy handling, and deterministic identity rules into frozen positive and
  negative fixture shapes before production implementation.
- **Dependencies**: Task 1.2
- **Acceptance criteria**: fixtures cover every required field/disposition,
  grouped target, append behavior, duplicate identity, redaction, v1 diagnostic,
  and stable error discriminator; failure evidence is due to missing v2 support.
- **Validation**: focused failing cargo tests retained in test-first evidence.

## Sprint 2: Implement, Deliver, And Release Evidence V2

**Goal**: ship a backward-readable, strict-v2 evidence primitive and forge gate
consumer from nils-cli.

### Task 2.1: Implement the v2 record and CLI lifecycle

- **Location**:
  - nils-cli `crates/agent-workflow-primitives/src/test_first_evidence.rs`
  - nils-cli `crates/agent-workflow-primitives/src/test_first_evidence/cli.rs`
- **Description**: add typed contract delta and test-impact records, append-only
  failing/final evidence, meaningful-red fields, scoped validation, waiver debt,
  residual gaps, deterministic ordering/identity, redaction, v1 read/show, and
  strict v2 verification with stable errors.
- **Dependencies**: Task 1.3
- **Acceptance criteria**: new writes are v2; repeated records do not overwrite;
  strict verification enforces all objective requirements; v1 is readable but
  receives an actionable strict-mode re-record error; JSON/text contracts and
  exit codes remain stable.
- **Validation**: focused unit and CLI integration tests, help snapshots, JSON
  fixtures, redaction tests, and legacy compatibility tests.

### Task 2.2: Make forge consume strict durable evidence

- **Location**:
  - nils-cli `crates/forge-cli/src/ops/pr_create.rs`
  - nils-cli `crates/forge-cli/src/macros/pr_deliver.rs`
  - nils-cli `crates/forge-cli/src/cli.rs`
  - nils-cli forge unit/integration tests
- **Description**: require strict v2 evidence when the existing opt-in gate
  applies to feature/bug create, adopt, dry-run, and deliver paths; retain exempt
  kinds and config precedence; expose stable legacy/incomplete/unreadable errors.
- **Dependencies**: Task 2.1
- **Acceptance criteria**: complete v2 and valid waiver paths pass; v1,
  structurally incomplete v2, and missing evidence fail distinctly; exempt
  kinds remain unchanged; deliver forwards the directory without bypass.
- **Validation**: focused forge-cli tests covering every gate and forwarding
  branch.

### Task 2.3: Validate, review, deliver, and release nils-cli

- **Location**: nils-cli repository, provider PR, release, artifacts, and
  Homebrew tap
- **Description**: run declared validation, perform testing/maintainability/API
  contract/red-team review, converge findings, deliver and merge, release, and
  verify installed binaries and help/fixture behavior.
- **Dependencies**:
  - Task 2.1
  - Task 2.2
- **Acceptance criteria**: PR is merged after required review; release and
  artifacts publish; tap updates; local Homebrew install exposes v2; focused
  released-binary checks pass.
- **Validation**: nils-cli declared full gate, provider CI/review read-back,
  release artifact checks, `test-first-evidence --version`, and released v2
  fixture verification.

## Sprint 3: Consume The Durable Contract In Runtime-Kit

**Goal**: make the released v2 engineering discipline canonical, rendered,
reviewed, and exercised across supported product surfaces.

### Task 3.1: Rewrite the test-first engineering contract

- **Location**:
  - `core/skills/evidence/test-first-evidence/SKILL.md.tera`
  - `AGENT_HOME.md` only if its concise pointer needs a compatibility wording
    adjustment
- **Description**: encode contract delta, impact scan, dispositions, primary
  owner selection, meaningful red, valid spec migration, scoped implementation,
  distinct-risk expansion, suite convergence, deterministic testing, flake
  debt, coverage guidance, and risk-based final validation using released v2.
- **Dependencies**: Task 2.3
- **Acceptance criteria**: the skill is the single full contract; intentional
  spec updates cannot be confused with weakening; grouped targets keep the
  workflow proportional; no duplicate full rule set is added to home policy.
- **Validation**: source review plus rendered Codex/Claude/Hermes golden diff.

### Task 3.2: Strengthen testing review and guided implementation

- **Location**:
  - `core/agents/code-review/reviewer-testing/AGENT.md.tera`
  - `core/skills/code-review/code-review-specialists/references/specialists/testing.md`
  - `core/skills/conversation/guided-feature-build/SKILL.md.tera`
- **Description**: require review of test-delta completeness, lost invariants,
  duplicate owners, meaningful red, stable boundary, mocks/snapshots, fixture
  determinism, flake handling, validation scopes, and residual gaps; route
  guided implementation through the strengthened contract.
- **Dependencies**: Task 3.1
- **Acceptance criteria**: agent and specialist guidance agree; review can flag
  semantic gaps without claiming CLI enforcement; guided builds name the v2
  lifecycle rather than the old five-step summary.
- **Validation**: renderer/golden checks and focused review-surface acceptance.

### Task 3.3: Pin the release and add deterministic acceptance coverage

- **Location**:
  - `manifests/skills.yaml`
  - `docs/source/nils-cli-pin.yaml`
  - `docs/source/nils-cli-surface.md`
  - `tests/runtime-smoke/cases/evidence/run.sh`
  - `tests/runtime-smoke/cases/pr/run.sh`
  - `tests/runtime-smoke/acceptance-matrix.yaml`
  - affected rendered/golden/sandbox fixtures
- **Description**: bump through `meta:nils-cli-bump`, refresh the released
  surface, and prove v2 success, structural failures, old-spec dispositions,
  waiver debt, append behavior, legacy diagnostics, and forge strict-gate
  consumption without using an off-pin binary for committed output.
- **Dependencies**:
  - Task 3.1
  - Task 3.2
- **Acceptance criteria**: runtime-kit consumes only the released binary;
  deterministic probes cover required positive/negative paths; product renders
  and declared CLI floors agree; no stale v1 invocation remains in active
  guidance.
- **Validation**: evidence/pr domain runtime-smoke, render/golden, manifest
  governance, version baseline, drift, sandbox install, and product leakage
  checks.

## Sprint 4: Validate, Review, Deliver, And Close

**Goal**: merge runtime-kit with complete L2 lifecycle evidence and archive the
coordination bundle.

### Task 4.1: Run declared runtime-kit validation

- **Location**: runtime-kit repository
- **Description**: run focused checks during implementation and the complete
  project-dev contract on the released pinned nils-cli after generated output
  is final.
- **Dependencies**: Task 3.3
- **Acceptance criteria**: all declared gates pass with no unexplained skip,
  retry-only pass, off-pin output, or product leakage.
- **Validation**: `bash scripts/ci/all.sh` and `bash tests/hooks/run.sh`.

### Task 4.2: Run mandatory specialist review and converge findings

- **Location**: runtime-kit PR diff and linked evidence
- **Description**: run testing and maintainability plus API-contract and red-team
  lenses, repair findings, rerun affected validation, and resolve every provider
  thread/task before approval.
- **Dependencies**: Task 4.1
- **Acceptance criteria**: combined review approves; no unresolved thread/task;
  v1/v2 compatibility, bypass paths, policy duplication, and test-maintenance
  semantics have explicit review evidence.
- **Validation**: native review/read-back, affected-lens follow-ups, and
  lifecycle review checkpoint.

### Task 4.3: Merge, close, and archive the L2 tracker

- **Location**: runtime-kit PR, tracking issue, execution state, and plan archive
- **Description**: deliver through forge-cli, merge only after latest-head gates,
  record terminal state, pass close-ready/audit, close the tracker, and migrate
  the plan bundle according to the plan-archive workflow.
- **Dependencies**: Task 4.2
- **Acceptance criteria**: PR merged; issue terminal and audit-clean; execution
  ledger complete; bundle archived; no required task or follow-up is silently
  dropped.
- **Validation**: provider PR/issue read-back, plan-issue audit, close-ready, and
  archive query.

## Testing Strategy

- Test-first: dogfood current v1 for the upstream bootstrap, then use released
  v2 for runtime-kit production changes.
- Unit: evidence models, verifier rules, identities, ordering, redaction, error
  taxonomy, and forge gate decisions.
- Integration: CLI lifecycle, multiple records, legacy diagnostics, waiver debt,
  create/adopt/deliver paths, help/JSON/exit contracts.
- Runtime acceptance: deterministic evidence and PR domain probes plus product
  render/install/golden consistency.
- Review: testing, maintainability, API-contract, and red-team lenses in both
  repositories.

## Risks & gotchas

- Do not make one ledger entry per parametrized case; use material grouped
  targets to keep effort proportional.
- Do not make strict verification claim semantic quality it cannot prove.
- Do not accept legacy v1 silently on the strengthened forge path; return an
  actionable re-record diagnostic while preserving read/show support.
- Do not commit runtime-kit generated output from a local/off-pin nils-cli.
- Do not duplicate the full contract across home policy, skill, reviewer, and
  CLI help.
- Do not treat coverage percentage, retries, broad snapshots, or high test count
  as substitutes for distinct contract evidence.

## Rollback plan

- nils-cli retains v1 read/show support, so the v2 writer/strict consumer can be
  reverted without making existing records unreadable.
- Runtime-kit can revert its pin and rendered contract together if the released
  v2 surface has a blocking defect; never keep v2 prose on a v1-only pin.
- The opt-in gate default remains unchanged, limiting rollout impact while the
  stronger record contract stabilizes.
- Revert schema/consumer changes as a coordinated set; do not weaken verifier
  fields ad hoc to make a failing delivery pass.

