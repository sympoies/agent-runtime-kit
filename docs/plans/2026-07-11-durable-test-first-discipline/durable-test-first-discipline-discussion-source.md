# Durable Test-First Discipline Implementation Handoff

## Status

- Date: 2026-07-11
- Source: in-session review of the current test-first policy, skill, reviewer,
  released evidence CLI, and delivery gate
- Intended next step: execute the linked L2 plan across nils-cli and
  agent-runtime-kit, then close the plan tracker
- Retention: coordination artifact; archive through plan-tracking closeout after
  delivery

## Purpose

Strengthen test-first from a red-to-green evidence minimum into a durable test
maintenance contract. Tests produced or changed by the workflow must remain
trustworthy executable specifications: they should fail for the intended
contract regression, survive behavior-preserving refactors, avoid redundant
coverage, and evolve deliberately when a specification changes.

## Confirmed Facts

- `AGENT_HOME.md` currently requires failing-test evidence or a waiver before
  production edits, but delegates all engineering judgment to
  `test-first-evidence`.
- `core/skills/evidence/test-first-evidence/SKILL.md.tera` currently defines five
  steps: classify, capture a focused failing test, waive when appropriate,
  implement to green, and run the smallest meaningful related validation.
- The current skill does not require an existing-test impact scan, a contract
  delta, classification of old-spec tests, a rationale for updated/deleted
  tests, or a duplicate/brittleness convergence pass.
- The current testing specialist checks changed behavior, brittle assertions,
  missing regressions, deterministic fixtures, and validation relevance. It
  does not explicitly check meaningful-red evidence, intentional old-spec
  migration, lost invariants after deletion, duplicate behavioral ownership,
  or whether the chosen test layer is stable.
- nils-cli `crates/agent-workflow-primitives/src/test_first_evidence.rs` writes
  `test-first-evidence.record.v1`. The record has free-form classification and
  production paths, at most one failing test or waiver, and at most one final
  validation.
- Record v1 `verify` treats any non-zero failing command, or any waiver, plus one
  passing final validation as complete. It cannot prove that the failure reason
  matches the intended missing behavior or that affected old tests were
  reconciled.
- `crates/forge-cli/src/ops/pr_create.rs` delegates the feature/bug delivery gate
  to that same completeness result. The gate remains opt-in through
  `[test_first].require`.
- Plan-archive searches for `test maintenance`, `meaningful red`, and `old spec`
  found no existing plan. Earlier `test-first` hits concern skill migration and
  acceptance coverage, not this contract.

## Objective And Quality Model

A durable test should satisfy all four properties:

1. **Contract ownership**: it names the observable behavior or invariant it
   protects.
2. **Distinct risk**: it protects a failure mode not already adequately owned
   elsewhere.
3. **Stable boundary**: it asserts public outcome, state, error, or protocol
   behavior rather than incidental implementation structure.
4. **Diagnostic failure**: when the contract breaks, it fails deterministically
   for the expected reason.

Coverage remains a gap-discovery signal, not proof of behavioral completeness
and not a reason by itself to add another case.

## Decisions

1. Replace the current five-step discipline with a contract-delta and
   test-lifecycle workflow:
   - classify the production change;
   - declare retained, changed, removed, and added behaviors plus invariants;
   - inspect materially affected existing tests, fixtures, snapshots, mocks,
     contract consumers, and higher-level journeys;
   - disposition affected test targets as `keep`, `update-spec`,
     `remove-superseded`, `add-missing`, or `refactor-only`;
   - choose the primary owner test at the lowest stable boundary that directly
     proves the contract;
   - capture a meaningful red for the expected failure reason;
   - implement the smallest production change;
   - add only distinct-risk coverage;
   - converge the suite for duplication, brittleness, and determinism;
   - validate the focused test, affected suite, and any shared contract
     consumers.
2. An intentional specification update is not test weakening. Update a still
   valuable old-spec test to the new expectation before production code and use
   that expected failure as red evidence.
3. Delete an obsolete test only when its behavior no longer exists or another
   named owner test preserves every still-valid invariant. Pure deletion does
   not satisfy failing-test evidence.
4. Do not require one ledger row per individual parametrized case. A test target
   may be a test name, path, suite, fixture family, or snapshot group when the
   group shares one disposition and rationale.
5. The primary owner test is chosen by stable behavioral boundary, not by a
   rigid unit-first rule. Unit/property, integration, contract, and E2E tests
   each remain valid when they uniquely protect the relevant risk.
6. A failing command counts only when expected and observed failure reasons are
   recorded and agree at the engineering-review level. Compilation, setup,
   environment, fixture, or unrelated failures do not count as meaningful red.
7. Prefer table-driven, parameterized, or property-based tests for input spaces.
   Add multiple examples only when they represent distinct partitions or risks.
8. Assertions should prefer observable outcomes and invariants. Mock private
   call order, broad snapshots, hidden state, silent retries, and real
   time/random/network dependencies are presumed brittle and require an
   explicit reason.
9. Flaky tests are defects. Quarantine is allowed only as a time-bounded
   exception with an owner, follow-up record, expiry/removal condition, and
   substitute validation; retry-until-green is not valid evidence.
10. The full qualitative contract lives in the runtime-kit skill and testing
    reviewer. The CLI and forge gate enforce only objective record structure;
    they must not pretend to determine semantic test quality.
11. Introduce `test-first-evidence.record.v2`. New writers emit v2. Readers can
    show and diagnose v1, but upgraded feature/bug delivery gates do not accept
    legacy v1 as durable evidence unless an explicit temporary compatibility
    override is selected. The default path requires deliberate re-recording,
    because missing maintenance facts cannot be inferred safely.
12. Keep `[test_first].require` opt-in behavior unchanged. This effort
    strengthens the meaning of evidence when the gate is active; changing its
    rollout default is separate policy work.
13. Do not expand `AGENT_HOME.md` into a second full specification. Keep its
    concise pointer and make `test-first-evidence` the canonical engineering
    contract.

## Evidence V2 Contract

The exact CLI spelling may follow existing clap conventions, but the released
machine contract must represent these concepts:

- `contract_delta`
  - retained behaviors/invariants;
  - changed behaviors;
  - removed behaviors;
  - added behaviors.
- `test_impacts[]`
  - target identifier;
  - disposition: `keep`, `update-spec`, `remove-superseded`, `add-missing`, or
    `refactor-only`;
  - protected behavior/risk;
  - rationale;
  - optional replacement or primary owner test.
- `failing_tests[]`
  - command, exit code, test/scenario identifier, expected failure, observed
    failure, summary, and artifacts.
- `waiver`
  - reason, why red evidence is impractical, substitute validations, and any
    expiry/follow-up for time-bounded exceptions.
- `final_validations[]`
  - command/manual step, status, scope (`focused`, `affected-suite`,
    `contract-consumer`, `full`, or `manual`), summary, and artifacts.
- `residual_gaps[]`
  - explicitly accepted missing coverage or validation with reason and
    follow-up when required.

For testable behavior changes, strict v2 verification must require:

- a non-empty contract delta;
- at least one affected-test declaration or an explicit declaration that no
  existing test target is affected;
- a rationale for every update/remove disposition;
- a replacement/owner declaration for removal when a valid invariant remains;
- at least one meaningful failing test, unless a complete waiver exists;
- at least one passing focused final validation;
- passing affected-suite or contract-consumer validation when the impact
  declaration says those scopes exist;
- no duplicate test-impact identity/disposition entries;
- explicit residual gaps rather than silent omissions.

The verifier must not claim semantic agreement between expected and observed
failure text, non-duplication of behavior, or correct abstraction level. Those
remain review judgments.

## Scope

### nils-cli

- Add record v2 models, commands/flags, rendering, redaction, deterministic
  ordering, strict verification, legacy-v1 diagnostics, and migration errors in
  `crates/agent-workflow-primitives`.
- Preserve the public JSON envelope and stable exit-code/error-kind conventions.
- Update forge-cli feature/bug gate consumption, create/deliver forwarding, help,
  unit/integration fixtures, and compatibility behavior.
- Release the implementation and publish the Homebrew surface before
  runtime-kit consumes it.

### agent-runtime-kit

- Rewrite `core/skills/evidence/test-first-evidence/SKILL.md.tera` around the
  durable lifecycle contract and v2 CLI.
- Expand testing specialist guidance in both
  `core/agents/code-review/reviewer-testing/AGENT.md.tera` and
  `core/skills/code-review/code-review-specialists/references/specialists/testing.md`.
- Keep generated product surfaces aligned through manifests, required CLI
  floors, renders, goldens, sandbox/install expectations, and deterministic
  runtime-smoke evidence probes.
- Update guided implementation and delivery references that summarize the
  test-first contract.
- Update the pinned nils-cli surface through the governed release/bump workflow.

## Non-Scope

- Turning the test-first gate on by default for every repository.
- A universal line/branch coverage threshold or a requirement that coverage
  increase on every PR.
- Mandatory mutation testing on every change. Targeted mutation testing may be
  recommended for critical parsers, authorization, state machines, or other
  high-risk decision logic.
- Rewriting a consuming repository's existing test suite or retroactively
  cataloging every historical test.
- Inferring semantic test quality through filename, assertion count, coverage
  percentage, or large-language-model output inside the deterministic CLI.
- Building a generic test dependency graph or framework-specific test discovery
  engine into nils-cli.
- Changing project-specific test commands or replacing repository-owned
  validation contracts.

## Requirements

1. The runtime-kit skill defines contract delta, impact scan, dispositions,
   primary ownership, meaningful red, scoped implementation, distinct-risk
   expansion, convergence, and risk-based final validation.
2. The skill explicitly distinguishes valid intentional spec updates from
   weakening/skipping/overfitting tests.
3. The skill includes durability guidance for observable assertions, stable
   test boundaries, mocks, snapshots, fixtures, determinism, flaky tests, and
   coverage usage.
4. Evidence v2 serializes the contract and test-impact ledger deterministically
   and redacts all user-entered text/path fields using existing primitives.
5. Evidence v2 supports multiple failing tests and multiple final validations
   without silently overwriting prior entries.
6. Strict verification reports stable, actionable missing-field/error kinds for
   every structural requirement and never treats an unrelated non-zero command
   as sufficient without expected/observed failure declarations.
7. Legacy v1 records remain readable and diagnosable. The strict delivery path
   fails them with an explicit upgrade/re-record message instead of parsing them
   as malformed data.
8. Waivers remain first-class but capture why red is impractical, substitute
   validation, and time-bound follow-up metadata when the waiver represents
   deferred test debt rather than a permanently non-testable change.
9. The forge feature/bug gate consumes strict durable verification while
   preserving existing opt-in config precedence and exempt PR kinds.
10. The testing reviewer checks test-delta completeness, lost invariants,
    duplicate owners, meaningful red, boundary stability, deterministic setup,
    mock/snapshot brittleness, and residual gaps.
11. Runtime-smoke proves a complete v2 path, each important incomplete/error
    path, waiver behavior, legacy-v1 diagnostics, and forge gate consumption.
12. Documentation and generated surfaces describe the same v2 contract without
    maintaining a second independent rule set.

## Acceptance Criteria

- A testable behavior change cannot pass strict v2 verification without a
  contract delta, test-impact declaration, meaningful-red fields or a valid
  waiver, and scoped passing validation.
- Updating an old-spec test to a new contract is represented explicitly and is
  accepted; deleting an obsolete test without a rationale or required owner is
  rejected.
- Repeated failing and final-validation records append deterministically rather
  than replace one another; duplicate entries fail or deduplicate according to
  a documented stable identity rule.
- Legacy v1 show/diagnostic behavior works, while the strict forge delivery gate
  emits a stable re-record/upgrade error for v1 evidence.
- Waiver records distinguish permanently non-testable changes from deferred
  test debt and require follow-up/expiry data for the latter.
- Reviewer guidance rejects evidence whose red state is caused by setup,
  compilation, environment, or unrelated failure.
- Reviewer guidance catches removal of a still-valid invariant, redundant
  behavior cases, implementation-coupled assertions, unjustified broad
  snapshots/mocks, hidden retries, and nondeterministic fixtures.
- Coverage is documented and reviewed as a diagnostic signal; no workflow step
  requires adding a duplicate case solely to increase a percentage.
- nils-cli focused and full validation passes, the release is published, and
  runtime-kit pins the released surface before refreshing generated output.
- Runtime-kit `bash scripts/ci/all.sh` and `bash tests/hooks/run.sh` pass on the
  released pin, followed by mandatory testing and maintainability review.
- Both repositories deliver through reviewed PRs, and the L2 tracker passes
  lifecycle close-ready/audit before closure.

## Validation Plan

### nils-cli focused validation

- Unit tests for v1/v2 parsing, deterministic ordering, redaction, structural
  completeness, duplicate identity behavior, and stable error kinds.
- CLI integration tests for init, impact recording, multiple failing tests,
  meaningful-red fields, waiver variants, multiple validation scopes, show,
  verify, help snapshots, JSON envelopes, and exit codes.
- forge-cli unit/integration tests for feature/bug strict-v2 acceptance,
  legacy-v1 rejection, waiver acceptance, exempt kinds, create/adopt/dry-run,
  and `pr deliver` forwarding.
- The repository-declared complete nils-cli validation, specialist review,
  release automation, artifact read-back, tap update, and installed-version
  verification.

### runtime-kit focused validation

- Render and golden assertions for the skill and reviewer guidance.
- Deterministic evidence-domain runtime-smoke cases for v2 success, structural
  failures, waiver behavior, and legacy diagnostics.
- PR/delivery-domain smoke proving the released forge gate consumes strict v2.
- Skill-governance and product-leak checks for every changed rendered surface.
- Full declared validation: `bash scripts/ci/all.sh` and
  `bash tests/hooks/run.sh`.
- Pre-merge specialist review with at least testing and maintainability lenses;
  add API-contract for v1/v2 compatibility and red-team for gate bypass/error
  paths.

## Risks And Guardrails

- **Process inflation**: a per-test ledger could become ceremony. Permit grouped
  targets and require only materially affected test surfaces.
- **False mechanical confidence**: structural verification cannot judge test
  semantics. Keep qualitative claims in review, never in CLI success wording.
- **Breaking active PRs**: strict v2 rejects old evidence. Ship actionable
  diagnostics, retain v1 read/show support, document re-recording, and announce
  the gate behavior in release notes.
- **Schema churn**: freeze the semantic fields and fixtures before making forge
  consume strict v2; do not expose a temporary ad-hoc note format as the public
  contract.
- **Duplicate policy**: `AGENT_HOME.md`, skill prose, reviewer prompts, and CLI
  help can drift. Keep the full contract in the skill, machine structure in the
  CLI, concise review checks in reviewers, and only pointers elsewhere.
- **Over-testing pressure**: do not translate every contract-delta item into a
  new case when an existing owner already proves it.
- **Flake normalization**: retries and quarantines can hide failures. Require
  explicit debt metadata and keep retry-only green from satisfying evidence.
- **Cross-repo release coupling**: runtime-kit must not render or commit v2
  output against an unreleased/off-pin binary. Implement, release, install, and
  then bump through the existing nils-cli workflow.

## Read First

- `AGENT_HOME.md`
- `core/skills/evidence/test-first-evidence/SKILL.md.tera`
- `core/policies/git-delivery.md`
- `core/agents/code-review/reviewer-testing/AGENT.md.tera`
- `core/skills/code-review/code-review-specialists/references/specialists/testing.md`
- `core/skills/conversation/guided-feature-build/SKILL.md.tera`
- `tests/runtime-smoke/cases/evidence/run.sh`
- `tests/runtime-smoke/acceptance-matrix.yaml`
- nils-cli `crates/agent-workflow-primitives/src/test_first_evidence.rs`
- nils-cli `crates/agent-workflow-primitives/src/test_first_evidence/cli.rs`
- nils-cli `crates/agent-workflow-primitives/tests/integration/test_first_evidence/`
- nils-cli `crates/forge-cli/src/ops/pr_create.rs`
- nils-cli `crates/forge-cli/src/macros/pr_deliver.rs`

## Execution

- Recommended plan: docs/plans/2026-07-11-durable-test-first-discipline/durable-test-first-discipline-plan.md
- Recommended execution state: docs/plans/2026-07-11-durable-test-first-discipline/durable-test-first-discipline-execution-state.md
- Status: ready for tracked implementation
- Next-task source: this document
