# Plan: Harden macOS desktop surface selection and rerunnable flows

## Overview

Execute one serial L2 change inside `sympoies/agent-runtime-kit`. The
`computer-use.macos-desktop` skill keeps its adapter, backend pin, and mechanics
contract; what changes is *when the skill is allowed to drive a GUI at all*,
*when it must stop*, *where a repeatable flow lives*, and *how many samples an
acceptance claim needs*.

Six deltas land across four sprints: a deterministic-first surface selection
ladder, an accessibility-degeneracy precondition gate with published negative
application classes, a reciprocal `browser-test` handoff, a declarative flow
fixture with a chained-`exec` runner, a stability convergence threshold in the
Acceptance Standard, and an upstream backend freshness audit.

Peekaboo remains pinned at `v4.2.2` and the nils-cli floor remains `>= 1.27.3`.
No adapter, tool-profile, journal, or replay behavior changes.

## Read First

- Primary source: `docs/plans/2026-08-26-macos-desktop-routing-hardening/macos-desktop-routing-hardening-discussion-source.md`
- Source type: `discussion-to-implementation-doc`
- Runtime-kit policy: `DEVELOPMENT.md`, `core/policies/work-tier-levels.md`,
  `core/policies/git-delivery.md`, `core/policies/files-hooks-validation.md`,
  `core/policies/evidence-control-plane.md`,
  `core/policies/browser-test-routing.md`, and
  `docs/source/docs-placement-retention-policy-v1.md`
- Current contract: `core/skills/computer-use/macos-desktop/SKILL.md.tera`,
  `core/skills/computer-use/macos-desktop/references/setup.md`, and
  `docs/source/macos-agent-capability-matrix.md`
- Test owner: `tests/runtime-smoke/cases/computer-use/run.sh`
- Open questions carried into execution: none

## Scope

- In scope: the surface selection ladder; the AX-degeneracy precondition gate;
  negative application-class matrix rows; the reciprocal `browser-test` handoff
  in both the skill and the routing policy; a declarative flow-fixture
  reference plus one tracked example; the stability convergence threshold in
  the Acceptance Standard; an upstream backend freshness drift audit; and the
  smoke assertions that pin all of it for source and every rendered product.
- Out of scope: replacing Peekaboo; adopting `cua-driver` or `lume`; backend
  abstraction; nils-cli pin or floor changes; adapter, tool-profile, journal,
  redaction, or replay behavior; granting the adapter shell access; any DOM or
  CDP capability claim for this skill.

## Execution Model

- Work tier: L2, one plan-tracking issue in `sympoies/agent-runtime-kit`.
- Branch: one managed worktree branch `feat/macos-desktop-routing-hardening`.
- PR ordering: one runtime-kit PR delivered with `--no-merge`, reviewed through
  the full specialist gate, then merged.
- Tasks are serial. The `.tera` source is a single shared surface, so
  concurrent lanes would conflict; sprints are ordered by dependency rather
  than parallelism.
- Provider-visible records use generic runtime roles. Host aliases, users,
  private paths, and raw desktop artifacts stay local.

## Assumptions

1. Peekaboo `v4.2.2` and nils-cli `v1.27.3` remain the pinned surface for the
   duration of this plan. A newer upstream release surfaced by the new audit is
   recorded as a follow-up, not adopted inside this delivery.
2. The canonical gate `bash scripts/ci/all.sh` remains the declared
   `project-dev` validation contract and continues to cover render, golden,
   drift, smoke, and hook layers.
3. No live macOS GUI target is required. Every change is a source, policy,
   reference, matrix, or deterministic-test surface, and the existing smoke
   harness already fakes `macos-agent`.
4. Golden expectations under `tests/golden/` are refreshed mechanically by the
   render step, so meaningful red is captured in the smoke probe rather than by
   hand-editing goldens.

## Sprint 1: Freeze the contract delta and capture red

**Goal**: Make the intended contract machine-checkable and prove the check
fails before any production edit.

**Demo/Validation**:

- `plan-tooling validate` passes for this bundle.
- The extended computer-use smoke probe fails for the intended missing
  behavior, not for setup, environment, or an unrelated assertion.

### Task 1.1: Declare the contract delta and capture meaningful red

- **Location**:
  - `tests/runtime-smoke/cases/computer-use/run.sh`
  - private `agent-out` test-first evidence directory
- **Description**: State the contract delta: what stays true (adapter
  mechanics, backend pin, profiles, journal, replay ceiling), what is added
  (surface ladder, AX gate, reciprocal browser handoff, flow fixture,
  stability threshold, freshness audit), and what invariants must hold (no
  adapter shell, no DOM claim, no pin change). Add a new probe asserting every
  added marker across the source `.tera`, the capability matrix, the routing
  policy, the new reference, and each rendered product. Run the case and record
  the failure.
- **Dependencies**:
  - none
- **Complexity**: 3
- **Acceptance criteria**:
  - New assertions cover source, matrix, policy, reference, and all three
    rendered products.
  - The probe fails on the intended missing markers before any `.tera` edit.
  - Test-first evidence records the classification, contract delta, affected
    test decision, and the observed red.
- **Validation**:
  - `bash tests/runtime-smoke/run.sh --mode deterministic`
  - `test-first-evidence check --phase pre-edit`

## Sprint 2: Publish surface selection and the browser boundary

**Goal**: Stop the skill from defaulting to GUI driving, and make the existing
`browser-test` route reachable from the desktop side.

**Demo/Validation**:

- The rendered skill for all three products publishes the ladder and the
  handoff.
- The matrix names the browser route instead of only denying DOM access.

### Task 2.1: Add the deterministic-first surface selection ladder

- **Location**:
  - `core/skills/computer-use/macos-desktop/SKILL.md.tera`
- **Description**: Add a selection section ahead of `## Outcome Routing` that
  orders candidate surfaces by determinism: App Intents / Shortcuts, a
  first-party app CLI or API, a scripting dictionary through `osascript`, then
  adapter-driven AX interaction, then the already-governed bounded coordinate
  fallback. State explicitly that the higher rungs run outside the adapter, are
  not adapter capabilities, and do not relax the adapter `shell` hard-deny.
  Require the chosen rung and the reason to be stated before the first
  mutation.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 4
- **Acceptance criteria**:
  - The ladder is ordered, each rung names its surface and its determinism
    rationale, and GUI driving is not the first rung.
  - The section states the adapter boundary so no reader infers shell access.
  - `## Outcome Routing` still owns local-versus-SSH, evidence mode, runtime,
    and journal-root selection without duplication.
- **Validation**:
  - `bash tests/runtime-smoke/run.sh --mode deterministic`
  - `agent-runtime render --product claude`

### Task 2.2: Make the browser-test handoff reciprocal

- **Location**:
  - `core/skills/computer-use/macos-desktop/SKILL.md.tera`
  - `core/policies/browser-test-routing.md`
  - `docs/source/macos-agent-capability-matrix.md`
- **Description**: Add a desktop-side handoff naming `browser-test` for
  DOM-level, selector, and rendered-page claims, and keep native chrome,
  cross-application behavior, permission dialogs, and AX interaction on the
  desktop route. Record who owns signed-in session state, which artifact
  directory holds the evidence, and how the two evidence sets link. Add the
  reciprocal pointer to the routing policy and replace the unnamed
  "separately governed browser route" in the matrix with the actual route.
- **Dependencies**:
  - Task 2.1
- **Complexity**: 3
- **Acceptance criteria**:
  - Both documents route in both directions and neither claims DOM capability
    for this skill.
  - The matrix `Browser DOM/CDP` row stays `disabled` and now names the route.
  - The handoff states session-state, artifact, and evidence-link ownership.
- **Validation**:
  - `bash tests/runtime-smoke/run.sh --mode deterministic`
  - `agent-runtime render --product codex`

## Sprint 3: Refuse degenerate targets and make flows rerunnable

**Goal**: Convert two silent failure modes — false success on an unusable
accessibility tree, and untracked one-off flows — into published contract.

**Demo/Validation**:

- The rendered skill publishes the degeneracy gate and its stop condition.
- A tracked example fixture exists and renders into every product.

### Task 3.1: Add the AX-degeneracy gate and negative application classes

- **Location**:
  - `core/skills/computer-use/macos-desktop/SKILL.md.tera`
  - `docs/source/macos-agent-capability-matrix.md`
- **Description**: After the first `see` observation, require an explicit
  accessibility-health judgement before any mutation: whether the tree exposes
  the declared target and actionable elements at all. On a degenerate tree,
  route to the already-governed bounded coordinate fallback inside the declared
  application when a fresh observation proves geometry, and otherwise stop with
  a blocker rather than continuing to probe. Publish the negative application
  classes — Chromium-family web content, Qt, OpenGL and canvas-drawn surfaces,
  and non-native toolkits that expose no usable tree — as an `unsupported`
  matrix row.
- **Dependencies**:
  - Task 2.2
- **Complexity**: 4
- **Acceptance criteria**:
  - The gate runs before mutation and names both outcomes explicitly.
  - Continuing to probe a degenerate tree is named as a false-success risk and
    a functional blocker, consistent with the existing Acceptance Standard.
  - The matrix carries the negative classes with `unsupported` status.
  - The existing displayless coordinate-fallback contract is reused, not
    duplicated or widened.
- **Validation**:
  - `bash tests/runtime-smoke/run.sh --mode deterministic`
  - `agent-runtime render --product claude`

### Task 3.2: Define the declarative flow fixture and its runner

- **Location**:
  - `core/skills/computer-use/macos-desktop/references/flow-fixtures.md` (new)
  - `core/skills/computer-use/macos-desktop/SKILL.md.tera`
- **Description**: Define a tracked fixture shape covering fixture identity,
  target application, setup and reset steps, ordered steps with an observable
  `--expected` postcondition per mutation, and declared stopping conditions.
  Document the runner as exactly the chained `exec` shape the skill already
  publishes, executed in one homogeneous journal directory, checking each
  postcondition before continuing. State that `journal replay-plan` is not the
  rerun mechanism, because its `never` classification and SSH
  `eligible=false` rows are deliberate ceilings. Include one complete example
  and link the reference from `## Multi-step Flows`.
- **Dependencies**:
  - Task 3.1
- **Complexity**: 5
- **Acceptance criteria**:
  - Every mutating step in the fixture shape carries an observable
    postcondition; a step without one is invalid.
  - The runner introduces no new mechanics, no scenario runner, and no shell
    fallback.
  - The reference renders identically into Codex, Claude, and Hermes.
  - The replay-ceiling exclusion is stated explicitly.
- **Validation**:
  - `bash tests/runtime-smoke/run.sh --mode deterministic`
  - `agent-runtime render --product codex`
  - `agent-runtime render --product claude`

## Sprint 4: Sample stability, audit freshness, and deliver

**Goal**: Make an acceptance claim survive flakiness, make upstream drift
visible, and land the change through the full review gate.

**Demo/Validation**:

- The Acceptance Standard requires repeated independent runs.
- The freshness audit reports the pinned backend against the declared upstream.
- `bash scripts/ci/all.sh` passes once against the final change.

### Task 4.1: Add the stability convergence threshold

- **Location**:
  - `core/skills/computer-use/macos-desktop/SKILL.md.tera`
- **Description**: Replace the single-sample independence check in
  `## Acceptance Standard` with a repeated-run threshold: run the same fixture
  independently a declared number of times, record the observed postcondition
  success rate from the journals, and classify the flow. A flow that does not
  converge is reported as not unattended-safe with its observed rate, rather
  than passing on one lucky run. Keep the existing no-blind-retry rule intact.
- **Dependencies**:
  - Task 3.2
- **Complexity**: 3
- **Acceptance criteria**:
  - The threshold names the sample count, the recorded rate, and the
    classification outcome.
  - Blind mutation retry remains forbidden and is not confused with repeated
    independent runs.
  - Existing acceptance items keep their meaning and numbering stays coherent.
- **Validation**:
  - `bash tests/runtime-smoke/run.sh --mode deterministic`

### Task 4.2: Add the upstream backend freshness audit

- **Location**:
  - `docs/source/macos-agent-capability-matrix.md`
  - `tests/runtime-smoke/cases/computer-use/run.sh`
- **Description**: Publish the pinned backend release, its pin source, and the
  audit expectation in the matrix so a newer upstream Peekaboo release is a
  reviewable diff rather than an unnoticed gap. Assert in the deterministic
  probe that the matrix backend version agrees with `docs/source/nils-cli-pin.yaml`
  and `docs/source/nils-cli-surface.md`, so the three mirrors cannot drift
  apart silently. The audit is deterministic and network-free; adopting a new
  release stays a separate reviewed decision.
- **Dependencies**:
  - Task 4.1
- **Complexity**: 3
- **Acceptance criteria**:
  - The matrix states the pinned backend release and its pin source.
  - The probe fails when the matrix and pin mirrors disagree.
  - No network access is introduced into the gate.
- **Validation**:
  - `bash tests/runtime-smoke/run.sh --mode deterministic`

### Task 4.3: Validate, review, and merge the delivery

- **Location**:
  - the managed worktree branch and its provider PR
- **Description**: Run the canonical gate once against the final change, refresh
  the render goldens through the gate, deliver the PR with `--no-merge`, run the
  full specialist review gate with at least the testing and maintainability
  lenses, post per-lens comments and the combined outcome, record the issue-side
  review checkpoint, and merge after every gate passes.
- **Dependencies**:
  - Task 4.2
- **Complexity**: 4
- **Acceptance criteria**:
  - `bash scripts/ci/all.sh` passes once against the final change.
  - Goldens are refreshed and `git diff --exit-code -- tests/golden/` is clean.
  - Specialist review findings are repaired or dispositioned, with zero
    unresolved threads and zero unchecked tasks at merge.
- **Validation**:
  - `bash scripts/ci/all.sh`
  - provider current-head checks and the review-loop ledger

### Task 4.4: Close the tracker and route archive maintenance

- **Location**:
  - the plan bundle and the tracking issue
- **Description**: Update the ledger and validation log, run strict
  `tracking close-ready --expect-visible`, close the record with linked PR and
  approval evidence, read back the closed issue, run the closeout audit, then
  run `plan-archive discover` and the dry-run migration. Apply only with
  explicit confirmation. Report the maintainer-facing test instructions.
- **Dependencies**:
  - Task 4.3
- **Complexity**: 2
- **Acceptance criteria**:
  - `close-ready` returns `ready: true` with no blockers.
  - The closeout role is visible and lint-clean in the read-back audit.
  - Archive migration is prepared as a dry run and applied only on
    confirmation.
- **Validation**:
  - `plan-issue tracking close-ready --expect-visible`
  - `plan-issue record audit --expect-visible`

## Testing Strategy

### Deterministic layers

- `tests/runtime-smoke/cases/computer-use/run.sh` is the behavioral owner. It
  already asserts the direct-adapter routing contract and the source-plus-
  rendered capability contract; this plan extends the second probe with the six
  new markers and the pin-mirror agreement check.
- Render and golden layers prove that every added marker reaches Codex, Claude,
  and Hermes identically, and that the new reference file ships with the skill.
- `scripts/ci/all.sh` is the single declared `project-dev` validation contract
  and is run once against the final change.

### Live macOS layers

None. Every change is a source, policy, reference, matrix, or deterministic
test surface. The smoke harness fakes `macos-agent`, so no unlocked GUI target,
TCC grant, or SSH host is required. This is recorded as an explicit residual:
the new contract text is proven to be published and consistent, not exercised
against a live desktop.

## Evidence Layout And Retention

- Test-first evidence and gate logs live in one `agent-out` run directory
  outside the repository and are never committed.
- Provider-visible records carry generic runtime roles only.
- The plan bundle is the durable in-repo record and is routed to
  `plan-archive` at closeout.

## Risks And Controls

1. **The ladder is read as adapter shell access.** Control: every rung states
   that it runs outside the adapter, and the smoke probe asserts the adapter
   `shell` hard-deny language is unchanged.
2. **The AX gate becomes an excuse to skip work.** Control: the gate requires a
   fresh observation and names the bounded coordinate fallback as the first
   response; stopping is the second, not the default.
3. **The fixture shape drifts into a scenario runner.** Control: the runner is
   defined as the existing chained `exec` calls, and the probe asserts that
   `macos-agent scenario` does not reappear.
4. **The stability threshold is confused with retry.** Control: the text keeps
   the no-blind-retry rule and defines repeated runs as independent, each with
   its own setup and fresh observation.
5. **Golden churn hides a real diff.** Control: goldens are refreshed only
   through the gate, and `git diff --exit-code -- tests/golden/` must be clean.

## Rollback Plan

Every change is additive documentation, policy, reference, and test content in
one repository with no runtime or pin dependency. Rollback is reverting the
single squashed merge commit; no backend, adapter, install, or provider state
is touched.
