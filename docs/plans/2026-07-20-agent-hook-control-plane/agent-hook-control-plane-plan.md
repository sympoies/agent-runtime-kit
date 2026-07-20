# Plan: Deliver and deploy the agent-hook control plane

## Overview

Execute issue #686 as one L3 dispatch plan across nils-cli, runtime-kit, and the
private session operator surface. First ship the new `agent-hook` mechanism and
release the already-merged #676 coordination capability. Then migrate the full
runtime-kit hook inventory into a versioned policy bundle and one provider
dispatcher ingress, extend the private agent-session workflow, integrate and
review the plan branch, deploy both Codex and Claude surfaces, rehearse recovery,
and close #676 and #686 only after live read-back.

## Read First

- Primary source:
  `docs/plans/2026-07-20-agent-hook-control-plane/agent-hook-control-plane-discussion-source.md`
- Source type: discussion-to-implementation-doc
- Execution state:
  `docs/plans/2026-07-20-agent-hook-control-plane/agent-hook-control-plane-execution-state.md`
- Architecture source: <https://github.com/graysurf/agent-runtime-kit/issues/686>
- Coordination dependency: <https://github.com/graysurf/agent-runtime-kit/issues/676>
  and `core/policies/session-coordination.md`
- Runtime-kit policy: `AGENTS.md`, `DEVELOPMENT.md`,
  `core/policies/work-tier-levels.md`, `core/policies/git-delivery.md`,
  `core/policies/files-hooks-validation.md`, and
  `core/policies/evidence-control-plane.md`
- Nils-cli policy: `AGENTS.md`, `DEVELOPMENT.md`,
  `docs/runbooks/new-cli-crate-development-standard.md`,
  `docs/runbooks/cli-completion-development-standard.md`, and
  `docs/specs/cli-service-json-contract-guideline-v1.md`
- Local-scripts policy: `AGENTS.md`, `README.md`, and `_tools/check.zsh`
- Open questions carried into execution: none

## Scope

- In scope: new `agent-hook` crate and binary; strict XDG config and policy
  schemas; provider request/decision adapters; deterministic aggregation;
  shadow, trace, doctor, inventory, and reversible setup; config-independent
  break-glass; agent-session setup compatibility; #676 release and consumption;
  heartbeat-based checkout writer liveness; complete runtime-kit rule inventory
  and migration; Codex/Claude render and cutover; private coordination workflow;
  release, pin, deployment, rollback, live acceptance, and closeout.
- Out of scope: removing provider-native ingress; managing unrelated hooks;
  repository-local config; arbitrary config-defined executables; bypassing
  lower-level transaction/privacy or host authorization; claiming native hook
  enforcement for Hermes or another provider without a compatible runner.

## Dispatch Model

- Shared issue: runtime-kit #686, attached as the single dispatch record.
- Plan branch: `feat/agent-hook-control-plane` in runtime-kit.
- Lane A (`nils-control-plane`): Tasks 1.1 through 1.5 in
  `sympoies/nils-cli`; owns the `agent-hook` mechanism, agent-session setup
  compatibility, liveness integration, validation, and the nils lane PR. The
  orchestrator and independent reviewer own Task 1.6 merge/release evidence.
- Lane B (`runtime-policy-cutover`): Tasks 2.1 through 2.4 in
  `graysurf/agent-runtime-kit`; owns inventory, policy bundle, runtime rules,
  rendered ingress, sync migration, rollback fixtures, and the runtime-kit lane
  PR targeting the plan branch.
- Lane C (`private-session-operations`): Task 3.1 in
  `serenvia/local-scripts`; owns the private skill and operator recovery flow,
  tests, and lane PR. The independent reviewer and orchestrator own Task 3.2.
- Lane D (`deployment-acceptance`): Tasks 4.2 through 4.4; owns post-integration
  installed-surface activation and bounded acceptance evidence, but may not
  change Lane A, B, or C implementation branches.
- The orchestrator alone attaches the tracker, assigns exact worktrees and task
  packets, merges independently approved lane PRs, delivers the final
  integration PR, reconciles #676, closes both records, and performs safe
  terminal cleanup.
- Lane A freezes the public contract first. Lane B may implement fixture-driven
  policy work against that frozen contract in parallel, but cannot cut over or
  pass full pinned validation until Lane A is released. Lane C starts after the
  released coordination and `agent-hook` surfaces are available. Lane D starts
  only after all implementation PRs and the runtime-kit integration PR merge.

## Invariants

1. Provider configs contain lifecycle ingress, never the runtime-kit rule list.
2. One config and one policy digest determine all runtime-kit-owned behavior for
   every supported provider on a host.
3. Config rejects unknown or unsupported data and cannot execute arbitrary
   commands or disable `locked` invariants.
4. Provider payloads are bounded and normalized before rule evaluation;
   provider-specific rendering occurs only after one aggregate decision.
5. Rule order, transformation composition, failure posture, and recovery are
   deterministic and explicit.
6. Shadow mode cannot block, transform input, mutate rule state, or consume a
   break-glass capability.
7. Setup preserves unrelated hooks, detects drift, applies atomically, and
   removes only exact owned representations.
8. Break-glass is authorized, exact, bounded, single-use or short-lived,
   config-independent, replay-safe, redacted, and never persisted in config.
9. Coordination/mailbox content and capability bearers never enter provider,
   logs, trace, list, glance, or public evidence.
10. Active physical writers and definite semantic conflicts remain blocking;
    stale/unknown evidence uses the documented reclaim or advisory path.
11. Every stateful migration has a compatible rollback before cutover.
12. A release, pin, provider mutation, sync, merge, or closeout claim requires
    exact provider or installed-surface read-back.

## Sprint 1: Ship the nils-cli control-plane mechanism

**PR grouping intent**: `group`

**Execution Profile**: `serial`

Lane A runs serially; contract/red precede production edits.

**Goal**: add one reusable `agent-hook` binary, converge provider-registration
ownership, integrate #676 liveness, and publish the exact nils-cli release that
runtime-kit can consume.

**Demo/Validation**:

- Isolated XDG fixtures prove strict config/policy/request/decision schemas,
  provider parity, deterministic aggregation, setup rollback, and break-glass.
- The nils local-fast contract and publish dry run pass on the reviewed head.
- The released binary reports the exact new version and exposes coordination.

### Task 1.1: Freeze contracts, inventory inputs, and meaningful red

- **Location**:
  - `sympoies/nils-cli/crates/agent-hook/docs/specs/agent-hook-v1.md`
  - `sympoies/nils-cli/crates/agent-hook/tests`
  - private nils-cli test-first evidence directory
- **Description**: Define config, policy bundle, normalized request, normalized
  decision, trace, setup plan, doctor, rule inventory, challenge, capability,
  and owner-liveness schemas. Freeze size/rate/TTL limits, XDG resolution,
  provider event matrices, aggregation precedence, transformation conflicts,
  override classes, failure posture, privacy fields, capability principals,
  replay rules, and exit/output contracts. Capture meaningful failing tests for
  missing behavior and declare affected agent-session setup tests before any
  production edit.
- **Dependencies**:
  - none
- **Complexity**: 9
- **Acceptance criteria**:
  - Every schema has an identifier/version and strict unknown-field behavior.
  - Codex and Claude fixtures cover every supported lifecycle event and malformed
    or oversized input.
  - The spec defines deterministic rule ordering, multi-decision aggregation,
    input-transformation conflict behavior, shadow semantics, and failure modes.
  - Break-glass includes challenge binding, authorization boundary, one-shot and
    repair-window scope, expiry, replay, drift, mismatch, revocation, and
    redaction behavior before ordinary config loading.
  - Meaningful red fails because the new contracts are absent, not because of
    test setup, compilation, or unrelated drift.
- **Validation**:
  - focused failing `cargo nextest run -p nils-agent-hook`
  - `test-first-evidence check --phase pre-edit` against the allocated evidence
  - `git diff --check`

### Task 1.2: Implement config, policy, dispatch, adapters, and aggregation

- **Location**:
  - `sympoies/nils-cli/crates/agent-hook/src`
  - `sympoies/nils-cli/crates/agent-hook/tests`
  - `sympoies/nils-cli/Cargo.toml`
  - `sympoies/nils-cli/Cargo.lock`
- **Description**: Create the publishable crate and `agent-hook` binary with
  strict XDG config/policy loading, normalized provider adapters, stable
  built-in capability bindings, deterministic pure rule evaluation and
  aggregation, typed text/JSON envelopes, side-effect-free shadow mode, bounded
  redacted trace, policy validation, and inventory. Reuse owning nils-cli
  libraries for Git/provider/session classifications; do not recreate command
  parsing with shell strings or execute arbitrary config rules.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 10
- **Acceptance criteria**:
  - The crate follows workspace versioning, docs placement, licensing,
    dependency, release-order, `-V/--version`, and JSON contract standards.
  - Config resolves the documented XDG path and validates `locked`,
    `downgrade-only`, and `free` overrides against the selected policy bundle.
  - One request produces one deterministic decision for both providers; rule
    order is stable and incompatible transformations fail explicitly.
  - Shadow evaluation cannot block, rewrite, mutate state, or consume recovery.
  - Diagnostics expose versions/digests and bounded reason metadata without raw
    payloads, local paths, session IDs, secrets, mailbox bodies, or bearers.
- **Validation**:
  - `cargo nextest run -p nils-agent-hook`
  - `cargo clippy -p nils-agent-hook --all-targets -- -D warnings`
  - `cargo run -p nils-agent-hook -- --help`
  - `cargo run -p nils-agent-hook -- --version`

### Task 1.3: Implement setup ownership, doctor, and compatibility migration

- **Location**:
  - `sympoies/nils-cli/crates/agent-hook/src/setup`
  - `sympoies/nils-cli/crates/agent-hook/src/doctor.rs`
  - `sympoies/nils-cli/crates/agent-session/src/activity.rs`
  - `sympoies/nils-cli/crates/agent-session/tests`
  - `sympoies/nils-cli/completions`
- **Description**: Move reusable provider config planning, drift detection,
  atomic apply/rollback, and owned-marker logic under `agent-hook setup`.
  Install one owned dispatcher representation for every required event while
  preserving unrelated provider hooks and metadata. Make `agent-session
  activity setup` an explicit compatibility forwarder or read-only surface;
  it may not install a second representation. Add doctor, preview/apply/remove,
  digest confirmation, rollback, concurrency, symlink, permission, malformed
  config, trust-review, and completion coverage.
- **Dependencies**:
  - Task 1.2
- **Complexity**: 10
- **Acceptance criteria**:
  - Setup preview/apply/remove is idempotent, drift-safe, byte-safe, and removes
    only exact owned handlers.
  - Codex and Claude each have at most one owned dispatcher command per required
    event/matcher group after apply.
  - Unrelated hooks, comments, formatting, metadata, and unsupported provider
    capability truth are preserved.
  - Legacy agent-session registrations have a reversible one-owner migration
    and cannot coexist as active managed duplicates after cutover.
  - Doctor distinguishes missing, legacy, dual, drifted, converged, unsupported,
    and unrelated representations without printing hook argv content.
- **Validation**:
  - focused `cargo nextest run -p nils-agent-hook -p nils-agent-session`
  - shell syntax checks for changed completions
  - setup fault-injection and round-trip fixtures

### Task 1.4: Implement break-glass and writer-liveness integration

- **Location**:
  - `sympoies/nils-cli/crates/agent-hook/src/recovery`
  - `sympoies/nils-cli/crates/agent-hook/src/state`
  - `sympoies/nils-cli/crates/agent-session/src/coordination`
  - `sympoies/nils-cli/crates/agent-hook/tests`
- **Description**: Add the minimal config-independent recovery bootstrap,
  challenge/capability lifecycle, atomic consumption, revocation, replay and
  drift rejection, one-shot and bounded repair-window scopes, and provider-safe
  recovery rendering. Consume #676 session/broker heartbeat and semantic claim
  evidence to classify physical writer ownership as active, stale, orphaned, or
  unknown. Preserve hard active-writer and definite semantic-conflict blocks,
  clean atomic reclaim, governed dirty adoption, conservative legacy TTL, and
  read-only inspection.
- **Dependencies**:
  - Task 1.2
  - Task 1.3
- **Complexity**: 10
- **Acceptance criteria**:
  - An authorized exact capability works when ordinary config is malformed or
    the required policy bundle cannot load.
  - Absent or ambiguous authorization, replay, expiry, session/target/event/
    command/snapshot drift, and revoked capabilities fail closed.
  - Repair windows bind one session, explicit target set, permitted rule set,
    maximum duration, and audit record; they are not enabled by environment or
    persistent config.
  - Active foreign writers and definite semantic conflicts block; stale clean
    owners reclaim atomically; dirty owners require governed adoption or
    break-glass; unknown evidence remains visible and conservative.
  - Crash, missing Stop, restart, child exit, stale heartbeat, key rotation,
    target recreation, concurrent contenders, and state-permission tests pass.
- **Validation**:
  - focused recovery, coordination, concurrency, and crash tests
  - privacy scan over text/JSON/trace/state fixtures
  - `cargo nextest run -p nils-agent-hook -p nils-agent-session`

### Task 1.5: Validate and deliver the nils-cli lane PR

- **Location**:
  - `sympoies/nils-cli/DEVELOPMENT.md`
  - `sympoies/nils-cli/scripts/publish-crates.sh`
  - nils-cli release and Homebrew tap workflows
- **Description**: Run the required local-fast and publish dry-run gates, bind
  test-first/docs-impact delivery evidence, create one feature PR targeting
  nils-cli `main`, post the lane-scoped state/session/validation checkpoint, and
  stop at the reviewed exact head. The lane executor may not review, merge,
  release, or install its own PR.
- **Dependencies**:
  - Task 1.4
- **Complexity**: 9
- **Acceptance criteria**:
  - `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast` passes.
  - `scripts/publish-crates.sh --dry-run --crate agent-hook` passes and the
    crate is publish-ready.
  - The PR is open at the validated head with green provider checks or an exact
    named pending check; lane checkpoints link the PR and private evidence.
  - No review, merge, tag, release, tap, install, or #676 closeout mutation is
    performed by the lane executor.
- **Validation**:
  - `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`
  - `scripts/publish-crates.sh --dry-run --crate agent-hook`
  - provider checks and exact delivered-head read-back

### Task 1.6: Independently review, merge, release, and verify nils-cli

- **Location**:
  - `sympoies/nils-cli/DEVELOPMENT.md`
  - nils-cli feature PR
  - nils-cli release and Homebrew tap workflows
- **Description**: Route the exact Task 1.5 head to an independent specialist,
  repair through Lane A if needed, and let the orchestrator merge only an
  approved, green, thread-clean head. Choose the exact next version through the
  repository release workflow, publish/tag it, update the Homebrew tap, install
  it locally, and read back both `agent-hook` and the #676 `agent-session`
  coordination commands. Reconcile #676 Task 2.5 without closing that tracker.
- **Dependencies**:
  - Task 1.5
- **Complexity**: 8
- **Acceptance criteria**:
  - The nils PR is independently approved, checks are green, threads/tasks are
    resolved, and the merged revision contains the reviewed head.
  - The governed release workflow publishes the exact merged workspace version.
  - Homebrew tap and installed binaries report that exact version.
  - Installed `agent-session` exposes the #676 coordination/mailbox surface and
    installed `agent-hook` passes a clean isolated doctor fixture.
- **Validation**:
  - native review/check/thread/task/merge read-back
  - tag/release/tap read-back and installed `--version` checks

### Task 1.7: Close the single-ingress coordination sequencing gap

- **Location**:
  - `sympoies/nils-cli/crates/agent-hook/src`
  - `sympoies/nils-cli/crates/agent-hook/tests`
  - `sympoies/nils-cli/crates/agent-session/src`
  - `sympoies/nils-cli/completions`
- **Description**: Repair the integration gap discovered when consuming the
  released v1.25.4 surface: plain policy evaluation cannot transactionally run
  #676 admission only after the aggregate hook decision allows, and a separate
  Claude sibling hook would race. Add one built-in, setup-owned ingress that
  preserves deterministic policy-before-admission ordering and PostTool
  completion/reconciliation without arbitrary config commands, a second
  registration writer, or an advisory-only downgrade. Deliver the bounded nils
  PR, independently review it, release the next exact patch version, and verify
  registry, tap, setup, and installed binaries before runtime cutover resumes.
- **Dependencies**:
  - Task 1.6
- **Complexity**: 9
- **Acceptance criteria**:
  - Codex and Claude retain at most one runtime-kit-owned command per required
    matcher group, with setup preview/apply/remove and rollback owned by
    `agent-hook setup`.
  - A pre-policy block cannot admit coordination, an allowed PreTool request
    admits exactly once, and matching PostTool success/failure completes or
    reconciles the transaction.
  - No arbitrary executable surface or parallel coordination sibling is added;
    advisory/enforce/off and locked-invariant behavior remains explicit.
  - The bounded PR passes focused and affected validation, independent review,
    exact-head provider gates, merge read-back, and exact patch-release
    tag/registry/tap/install verification.
- **Validation**:
  - focused agent-hook and agent-session sequencing/setup regressions
  - affected nils-cli suite and required provider checks
  - exact release, crates.io, tap, setup doctor, and installed-version read-back

## Sprint 2: Migrate runtime-kit policy and provider wiring

**PR grouping intent**: `group`

**Execution Profile**: `parallel-x2`

Lane B contract work may overlap late Lane A work; exact pin/cutover waits for
Task 1.7.

**Goal**: express every runtime-kit-owned hook as a versioned policy rule,
replace rule-specific provider registrations with one dispatcher ingress, and
prove parity, rollback, liveness, and coordination admission.

**Demo/Validation**:

- The inventory maps every legacy handler to a stable rule and disposition.
- Rendered Codex and Claude fixtures contain only dispatcher ingress for
  runtime-kit-owned rules.
- Full runtime-kit CI and hook tests pass against the exact released nils pin.

### Task 2.1: Freeze the complete rule inventory, policy schema, and red baseline

- **Location**:
  - `manifests/hook-rules.yaml`
  - `core/policies/agent-hook`
  - `tests/agent-hook`
  - private runtime-kit test-first evidence directory
- **Description**: Inventory every current shared/product handler with stable
  ID, provider event/matcher, capability binding, mode, priority, failure
  posture, override class, state owner, transformation, recovery, docs, test
  owner, product coverage, and migration/retirement disposition. Add the
  versioned runtime-kit policy bundle source and meaningful failing parity,
  rendering, privacy, rollback, and coordination-admission tests before
  production migration edits.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 9
- **Acceptance criteria**:
  - Every active runtime-kit handler has exactly one inventory disposition; no
    registered behavior silently disappears.
  - Locked writer/privacy/transaction/recovery rules and permitted override
    classes are explicit and schema-validated.
  - Multi-event and input-transforming rules have explicit aggregation and
    rollback behavior.
  - Expected legacy decisions are frozen from representative Codex and Claude
    fixtures, including allow, warn, block, context, transform, and failure.
  - Meaningful red proves the missing dispatcher/policy behavior.
- **Validation**:
  - focused failing `bash tests/agent-hook/run.sh`
  - `test-first-evidence check --phase pre-edit` against allocated evidence
  - inventory coverage and duplicate-ID audits

### Task 2.2: Implement the policy bundle and typed rule capabilities

- **Location**:
  - `manifests/hook-rules.yaml`
  - `core/policies/agent-hook`
  - `core/hooks/shared/`
  - `tests/agent-hook`
  - `tests/hooks/`
- **Description**: Implement the policy source and move each legacy rule behind
  its typed `agent-hook` capability binding. Preserve rule semantics, state
  ownership, failure posture, privacy, and lower-level CLI invariants. Integrate
  #676 coordination intent/admission and heartbeat evidence. Keep legacy
  handlers available only as explicit rollback fixtures until cutover; do not
  let shadow evaluation duplicate their state transitions.
- **Dependencies**:
  - Task 2.1
  - Task 1.2
- **Complexity**: 10
- **Acceptance criteria**:
  - Every inventory row resolves to one installed policy rule or documented
    unrelated/retired disposition.
  - Fixture parity passes for all supported provider events and decision forms.
  - #676 definite conflicts block, incomplete/potential states advise, and
    public output never includes coordination or mailbox private data.
  - Checkout writer rules use agent-session liveness where available and retain
    conservative compatibility behavior without an eight-hour primary decision.
  - Shadow runs are side-effect-free and latency measurements meet the declared
    budget or record a reviewed optimization before cutover.
- **Validation**:
  - `bash tests/agent-hook/run.sh`
  - `bash tests/hooks/run.sh`
  - focused coordination, checkout lease, privacy, and latency tests

### Task 2.3: Replace rendered registrations and add reversible sync migration

- **Location**:
  - `core/hooks/codex`
  - `core/hooks/claude/`
  - `targets/codex/`
  - `targets/claude/`
  - `manifests/surfaces.yaml`
  - `scripts/sync-runtime-surfaces.sh`
  - `tests/golden/`
  - `tests/sandbox/`
  - `tests/runtime-smoke/`
- **Description**: Render versioned policy bundles and thin `agent-hook dispatch
  --product <provider>` ingress. Make sync install/update the policy bundle and
  call reviewed `agent-hook setup` preview/apply rather than render one handler
  per rule. Add legacy detection, shadow then enforce transitions, exact owned
  cleanup, concurrent drift protection, rollback bundle/state preservation,
  doctor read-back, and truthful Hermes capability diagnostics.
- **Dependencies**:
  - Task 2.2
  - Task 1.7
- **Complexity**: 10
- **Acceptance criteria**:
  - Codex and Claude goldens have one owned dispatcher representation per
    required provider group and zero active rule-specific owned registrations.
  - Unrelated hooks survive install, upgrade, rollback, remove, and prune.
  - Dry-run names exact policy/setup/cleanup actions and apply requires the
    reviewed plan/digest where the existing workflow requires it.
  - Rollback restores legacy authority without discarding newer ownership,
    coordination, break-glass, or dirty-checkout state.
  - Hermes and unsupported providers report shared-policy availability without
    claiming native enforcement.
- **Validation**:
  - `bash tests/agent-hook/run.sh`
  - `bash scripts/ci/sandbox-install-rehearsal.sh`
  - Codex/Claude dry-run, render, golden, upgrade, prune, rollback, and doctor
    runtime-smoke fixtures

### Task 2.4: Validate and deliver the runtime-kit lane PR

- **Location**:
  - complete Lane B diff
  - `docs/plans/2026-07-20-agent-hook-control-plane/agent-hook-control-plane-execution-state.md`
- **Description**: Update the execution ledger, run the complete pinned runtime
  checks, deliver the lane PR to `feat/agent-hook-control-plane`, obtain an
  independent specialist review, resolve every current-head finding, and let
  the orchestrator merge only the approved exact head into the plan branch.
- **Dependencies**:
  - Task 2.3
- **Complexity**: 8
- **Acceptance criteria**:
  - `bash scripts/ci/all.sh` and `bash tests/hooks/run.sh` pass on the exact
    released nils-cli pin.
  - Product leak, policy bundle, render, setup, rollback, coordination, and
    legacy-residue checks pass.
  - The lane PR has independent approval, zero unresolved actionable threads or
    tasks, green provider checks, and exact-head merge read-back.
- **Validation**:
  - `bash scripts/ci/all.sh`
  - `bash tests/hooks/run.sh`
  - provider checks and merged-revision read-back

## Sprint 3: Extend private session operations and integrate

**PR grouping intent**: `group`

**Execution Profile**: `parallel-x2`

Lane C starts after Task 1.6; Task 3.3 is orchestrator-serial after Tasks 2.4
and 3.2.

**Goal**: expose coordination and recovery through the private operator
workflow, merge all independently reviewed implementation, and prepare one
deployment-ready runtime-kit revision.

**Demo/Validation**:

- The private skill uses released coordination and mailbox primitives without
  prompt forwarding or weak title/cwd inference.
- The runtime-kit integration PR contains the reviewed Lane B ancestry and exact
  nils pin with a clean full-suite result.

### Task 3.1: Update private-agent-session coordination and recovery behavior

- **Location**:
  - `serenvia/local-scripts/agent-runtime/.agents/skills/private-agent-session`
  - `serenvia/local-scripts/_tools`
- **Description**: Extend the private operator skill to declare and inspect
  structured work context, claim before mutation, handle definite/potential/
  unknown results, use the private mailbox for necessary clarification, and
  recover broker/claim state. Add `agent-hook doctor`, inventory, one-shot
  challenge/authorization/consume, bounded repair-window, disable/remove, and
  unavailable-binary manual fallback guidance. Preserve mobile handoff and do
  not expose private message content, session IDs, hosts, paths, or capabilities
  in public artifacts.
- **Dependencies**:
  - Task 1.6
- **Complexity**: 8
- **Acceptance criteria**:
  - The workflow checks/claims structured scope before mutable session work and
    never treats title/cwd inference as authoritative.
  - Mailbox notifications are content-free; message bodies are read only through
    the private recipient surface and cannot authorize actions.
  - Recovery distinguishes safe release/reclaim, dirty adoption, exact
    break-glass, short repair window, provider-native manual operation, and
    complete dispatcher removal/restore.
  - Existing create/send/glance/log/delete/mobile behavior remains operational.
- **Validation**:
  - focused private skill portfolio fixtures
  - `./_tools/check.zsh`

### Task 3.2: Independently review, merge, and synchronize the private skill lane

- **Location**:
  - complete Lane C diff
  - private repository sync workflow
- **Description**: Route the Task 3.1 PR to an independent reviewer, return any
  repair to Lane C, and let the orchestrator merge only the approved, green,
  thread-clean exact head. Then synchronize the private environment repositories
  through their ownership-safe workflow. Keep machine-specific evidence private
  and report only capability/result classes to #686.
- **Dependencies**:
  - Task 3.1
- **Complexity**: 6
- **Acceptance criteria**:
  - The PR is approved, green, thread-clean, and merged at the reviewed head.
  - Private repository synchronization preserves unrelated user work and reads
    back the merged skill revision on required roles.
  - No secret, host alias, raw session ID, local absolute path, mailbox content,
    or break-glass bearer appears in provider-visible evidence.
- **Validation**:
  - `./_tools/check.zsh`
  - provider checks, merged-revision read-back, and private sync diagnostics

### Task 3.3: Deliver the runtime-kit integration PR

- **Location**:
  - `feat/agent-hook-control-plane`
  - `docs/plans/2026-07-20-agent-hook-control-plane/agent-hook-control-plane-execution-state.md`
- **Description**: Reconcile the plan branch with merged Lane B and the exact
  released nils dependency, update the ledger, run full validation, open the
  final PR to `main`, obtain independent multi-lens review, resolve all
  current-head findings, and merge through the governed workflow. Do not deploy
  from an unmerged or locally modified revision.
- **Dependencies**:
  - Task 2.4
  - Task 3.2
- **Complexity**: 9
- **Acceptance criteria**:
  - The final PR preserves reviewed lane ancestry and contains no unreviewed
    implementation changes.
  - Full runtime-kit CI, hook, render, sandbox, privacy, coordination, rollback,
    and doctor checks pass on the exact head.
  - Testing, maintainability, API/schema, data-migration, security, and red-team
    review converge with zero unresolved actionable items.
  - `main` read-back equals the provider-reported merged revision.
- **Validation**:
  - `bash scripts/ci/all.sh`
  - `bash tests/hooks/run.sh`
  - provider checks, native reviews, thread/task audit, and merge read-back

## Sprint 4: Deploy, prove recovery, and close both trackers

**PR grouping intent**: `group`

**Execution Profile**: `serial`

Lane D runs serially after Task 3.3.

**Goal**: deploy the merged policy and provider wiring, prove both normal and
recovery paths in fresh disposable sessions, leave a privacy-safe operational
report, and strictly close #676 and #686.

**Demo/Validation**:

- Installed `agent-hook doctor` proves both provider representations, one
  config/policy digest, rule inventory, coordination support, and no managed
  legacy residue.
- Fresh Codex and Claude sessions exercise allow/warn/block, semantic conflict,
  writer liveness, one-shot bypass, repair-window disable, full remove/restore,
  and unavailable-binary guidance without touching user work.

### Task 4.1: Reconcile #676 dependency state before activation

- **Location**:
  - `core/policies/session-coordination.md`
  - `docs/plans/2026-07-20-agent-hook-control-plane/agent-hook-control-plane-execution-state.md`
- **Description**: Update #676 from its reviewed merged mechanism state through
  the released version, runtime intent/admission, private skill, and deterministic
  acceptance evidence now delivered by this plan. Use canonical tracking
  checkpoints and preserve #676's serial ledger; do not close it until live
  activation and acceptance in Tasks 4.2 and 4.3 pass.
- **Dependencies**:
  - Task 3.3
- **Complexity**: 5
- **Acceptance criteria**:
  - Tracking status is visible/lint-clean and names the released nils version,
    merged runtime revision, private skill revision, and remaining live gate.
  - No stale Task 2.5 or early-sprint dashboard wording remains.
  - #676 stays open until coordination live acceptance passes.
- **Validation**:
  - `plan-issue tracking status --profile tracking --expect-visible --format json`
  - provider read-back and execution-ledger reconciliation

### Task 4.2: Preview, apply, and verify installed runtime surfaces

- **Location**:
  - `scripts/sync-runtime-surfaces.sh`
  - installed Codex and Claude runtime homes
  - private deployment evidence directory
- **Description**: Use the repository-owned sync workflow to preview and apply
  the merged `main` policy bundle and provider setup for Codex and Claude. Run
  ownership-safe private environment synchronization where required. Verify
  installed versions, config/policy digests, exact owned events, unrelated hook
  preservation, permissions, migration state, legacy absence, and rollback
  availability. Provider-visible evidence must be generic and redacted.
- **Dependencies**:
  - Task 4.1
- **Complexity**: 8
- **Acceptance criteria**:
  - Both products use the merged runtime revision and released nils version.
  - Doctor reports one owned dispatcher representation per required event,
    zero rule-specific managed registrations, and preserved unrelated hooks.
  - The installed policy/config digest matches the previewed apply plan.
  - Rollback artifacts and manual unavailable-binary fallback are present and
    readable without revealing private paths or hook argv.
- **Validation**:
  - Codex and Claude sync dry-run/apply read-back
  - `agent-hook doctor --all --format json`
  - installed version, ownership, permissions, digest, and legacy-residue checks

### Task 4.3: Run deterministic and live disposable-session acceptance

- **Location**:
  - `tests/agent-hook`
  - `tests/runtime-smoke/`
  - private acceptance evidence directory
- **Description**: First run deterministic isolated acceptance, then start
  bounded fresh Codex and Claude sessions in disposable clean repositories.
  Exercise allow/warn/block/context behavior, definite and incomplete semantic
  overlap, active/stale/orphaned/unknown writer states, missing Stop/crash
  recovery, clean reclaim, dirty adoption denial, exact one-shot break-glass,
  replay/drift rejection, repair-window expiry/revocation, full dispatcher
  remove/restore, unrelated-hook preservation, and fixed mailbox notification.
  Use synthetic content and clean up every disposable session/repository.
- **Dependencies**:
  - Task 4.2
- **Complexity**: 10
- **Acceptance criteria**:
  - Codex and Claude produce equivalent normalized decisions where provider
    capabilities overlap and exact provider output/exit behavior passes.
  - Active foreign writers and definite semantic conflicts block; incomplete
    semantic evidence does not falsely report clear.
  - Break-glass works only for authorized exact scope, survives broken ordinary
    config/policy loading, rejects replay/drift, and leaves redacted audit state.
  - Repair-window disable and full owned-handler removal are visibly bounded and
    reversible; unrelated hooks still run after remove/restore.
  - Latency and privacy budgets pass; all disposable state is cleaned up.
- **Validation**:
  - deterministic agent-hook/provider/coordination acceptance suite
  - fresh Codex and Claude session probes with postconditions
  - privacy scan, latency report, rollback/remove/restore read-back, and cleanup

### Task 4.4: Close #676 and #686 and archive the completed plan

- **Location**:
  - runtime-kit issues #676 and #686
  - both execution-state ledgers
  - agent-plan archive
- **Description**: Record the deployed revisions and acceptance result, produce
  the operator-facing inventory of remaining hooks and recovery/disable paths,
  close #676 through its tracking gate, close #686 through strict dispatch
  close-ready/audit, close or disposition superseded implementation issues,
  archive the plan, migrate durable evidence if warranted, and remove only safe
  clean managed worktrees after provider read-back.
- **Dependencies**:
  - Task 4.3
- **Complexity**: 7
- **Acceptance criteria**:
  - The final report distinguishes provider-native dispatcher ingress,
    unrelated preserved hooks, unsupported-provider surfaces, and removed
    runtime-kit legacy handlers.
  - It documents read-only inspect/doctor, per-rule permitted config overrides,
    exact one-shot break-glass, bounded repair window, full owned-handler remove,
    restore/apply, and unavailable-binary manual fallback, including what each
    path does not bypass.
  - #676 and #686 have complete visible lifecycle roles, terminal ledgers,
    merged linked PRs, approvals, validation, deployment evidence, and clean
    post-close audits.
  - Archive and cleanup retain every dirty, locked, ambiguous, or unverifiable
    checkout and report it instead of forcing removal.
- **Validation**:
  - #676 `tracking close-ready` and `record close --profile tracking`
  - #686 `tracking close-ready --profile dispatch --expect-visible`
  - #686 `record close --profile dispatch` and post-close `record audit`
  - archive read-back and managed-worktree cleanup diagnostics

## Integration And Review Strategy

- Lane A owns all nils-cli production code and one nils PR; no other lane edits
  that worktree or reviews its own PR.
- Lane B owns runtime-kit policy/render/cutover code and targets the plan branch.
  The orchestrator may merge only an independently approved exact head.
- Lane C owns the private skill and one local-scripts PR. Public checkpoints use
  generic capability/revision evidence only.
- Lane D performs post-merge deployment and acceptance from exact merged
  revisions; it does not introduce implementation changes. Any discovered code
  defect returns to the owning lane with a new reviewed head.
- The final integration PR targets runtime-kit `main` and receives testing,
  maintainability, API/schema, data-migration, security, and red-team lenses.
- Every feature/bug lane allocates v2 test-first evidence before production
  edits and threads it through PR delivery. Docs-impact evidence is required in
  each repository according to its active policy.
- Lane PRs stop after implementation, validation, provider delivery, and lane
  state/session/validation checkpoints. Independent reviewers own review
  outcomes. Only the orchestrator merges.

## Deployment And Rollback Strategy

- Release nils-cli before runtime-kit exact-pin validation and provider cutover.
- Deploy only merged runtime-kit `main`; preview setup and sync before apply.
- Preserve a compatible legacy registration bundle until fresh-session
  acceptance passes. Rollback restores legacy authority but does not erase newer
  coordination, writer, dirty-adoption, challenge, capability, or trace state.
- `agent-hook setup --remove` removes only owned ingress and leaves unrelated
  hooks. `agent-hook setup --apply` restores owned ingress from the reviewed
  policy/config plan.
- One-shot break-glass and repair windows are recovery tools, not rollout
  toggles. The unavailable-binary fallback is provider-native/manual operation
  with an explicit statement that the dispatcher did not recover itself.

## Completion Criteria

The plan is complete only when all task rows are terminal, all implementation
and integration PRs are independently approved and merged, nils-cli is released
and installed, runtime surfaces are applied from merged `main`, both provider
acceptance paths pass or have a user-approved named capability waiver, #676 is
closed, #686 passes dispatch close-ready and post-close audit, and the user has
the final remaining-hook and escape-hatch/disable report.
