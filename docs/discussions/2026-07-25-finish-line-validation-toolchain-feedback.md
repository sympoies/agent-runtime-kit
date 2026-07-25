# Finish-Line Validation Toolchain And Feedback Implementation Handoff

- **Status**: decided; implementation-ready; no unresolved design questions
- **Date**: 2026-07-25
- **Source**: In-session diagnosis after Agent Console validation passed under
  its required Node.js toolchain but the finish-line Stop hook still reported
  every declared command as outstanding
- **Intended next step**: improve runtime-kit diagnostics and Stop guidance,
  then adopt a toolchain-owning validation entrypoint in Agent Console as a
  separate consumer change
- **Retention**: coordination source; remove after the runtime behavior, tests,
  hook guidance, and consumer validation contract preserve the decisions

## Purpose

Keep the finish-line gate fail-closed while making a common non-credit outcome
immediately understandable and eliminating the conflict between a repository's
required toolchain and the exact command shape the gate can prove.

The incident had two simultaneous truths:

1. refusing to credit a validation embedded in an unrelated shell preamble is
   correct because the aggregate exit status is not safely attributable to the
   declared validation; and
2. the repository's declared bare commands did not select its required Node.js
   major, so the exact command shape that the hook could credit ran under the
   host's wrong default toolchain.

The implementation must resolve the integration and feedback gaps without
teaching the hook to trust arbitrary `eval`, `source`, shell setup, suffixes, or
masked exit statuses.

## Confirmed Facts

- Finish-line matching has two distinct stages. `command_matches_validation`
  finds declared validation invocations by parsed shell segment, while
  `outcome_status_is_provable` decides whether the aggregate shell status can
  safely credit those matches. [F1] [F2]
- A command is provable when it is exactly one declared command or an `&&`
  chain whose every segment is itself declared. Unrelated preambles or
  suffixes, `;`, `||`, pipelines, background execution, and grouping are
  deliberately not credited. [F2]
- When declared invocations are found but the aggregate status is not
  provable, the PreToolUse recorder currently returns without a rewrite or
  visible explanation. The user learns about the non-credit only when the Stop
  gate later lists the commands as outstanding. [F2]
- Successful command outcomes are first stored in session-scoped command
  state. The Stop gate later consolidates a satisfied contract into its
  configured `.ok` marker and removes completed session state. [F3]
- The Stop message currently says that running the displayed chain records the
  configured `.ok` marker. That wording hides the session-state/consolidation
  lifecycle and makes a successful but uncredited invocation look like a
  missing execution rather than an unprovable command shape. [F3]
- Agent Console requires Node.js `>=24 <25` and records `24` in
  `.node-version`, but its `project-dev` validation contract declares five bare
  `pnpm` commands with no toolchain-owning entrypoint. [F4]
- In the triggering run, a Node.js 24 setup preamble followed by the complete
  declared chain passed but was not credited. Running the exact bare chain was
  credited, but it used the host's Node.js 26 default and emitted the expected
  engine warning before passing. [A1]
- Existing hook tests protect the security boundary that unrelated preambles
  must not be authorized and prove that an exact success-preserving validation
  chain can release the gate. [F5]

## Decisions

1. Preserve the existing aggregate-status proof rule. A command that cannot
   prove the declared validation's exit status remains uncredited.
2. Do not allowlist arbitrary environment setup, `eval`, `source`, `cd`,
   suffixes, or shell-control-flow shapes merely because a declared command
   appears later.
3. When declared validation invocations match but aggregate status is
   unprovable, emit one non-blocking, provider-native advisory before execution.
   The command remains allowed and unchanged, but the advisory must state that
   this invocation will not satisfy the finish-line gate.
4. The advisory uses a stable reason class such as
   `validation_outcome_unprovable`; it does not echo the raw submitted command,
   environment assignments, or shell setup.
5. The advisory directs the agent to run the declared command shape exactly or
   move required setup into a repository-owned declared validation wrapper. It
   does not suggest a validation waiver.
6. Reword the Stop guidance to distinguish:
   - the full declared validation contract;
   - the commands still outstanding for this edit generation;
   - session-scoped successful outcome recording; and
   - final `.ok` marker consolidation performed by Stop.
7. Repositories with a required runtime/toolchain must make that selection part
   of the declared validation entrypoint. The preferred consumer pattern is one
   repository-owned wrapper whose exit status represents the entire contract.
8. Agent Console should adopt a single declared wrapper that selects and
   verifies Node.js 24 before invoking its existing frozen install, typecheck,
   test, version-drift, and build commands. This is a follow-up change in the
   Agent Console repository, not runtime-kit source.
9. Runtime-kit tests must use deterministic fake wrappers and temporary
   repositories. They must not depend on `fnm`, a particular host Node.js
   installation, or network access.

## Scope

- PreToolUse feedback when validation invocations match but their aggregate
  outcome cannot be credited.
- Stop-hook wording and marker-lifecycle accuracy.
- Codex and Claude parity for the shared hook behavior.
- Focused contract tests for exact, chained, unprovable, masked, and
  sensitive-preamble command shapes.
- Documentation of the toolchain-owning validation-wrapper pattern.
- A separate Agent Console consumer follow-up that applies the wrapper pattern
  to Node.js 24.

## Non-Scope

- Crediting arbitrary shell preambles, shell initialization, or environment
  mutation.
- Inferring validation success from console output, transcript text, elapsed
  time, or a later agent claim.
- Weakening command parsing, marker freshness, edit-generation tracking,
  failure recording, or waiver policy.
- Making the finish-line hook install or switch language runtimes.
- Changing `agent-docs` validation schema or moving the runtime contract into
  `sympoies/nils-cli` unless implementation proves a reusable schema primitive
  is necessary.
- Implementing the runtime-kit or Agent Console changes in this documentation
  capture.

## Findings

| Priority | Issue | Evidence | Fix location | Acceptance |
| --- | --- | --- | --- | --- |
| P0 | The creditable command shape can bypass the repository's required toolchain. | Agent Console declares bare `pnpm` commands while requiring Node.js 24; the host default was Node.js 26. [F4] [A1] | Agent Console validation wrapper and `AGENT_DOCS.toml` | The one declared entrypoint selects and verifies Node.js 24, runs the full existing contract, and is creditable as an exact invocation. |
| P1 | A matched-but-unprovable validation attempt is silent until Stop. | `validation_matches` can be non-empty while `outcome_status_is_provable` is false; the current PreToolUse path emits nothing. [F2] | `core/hooks/shared/finish-line-record.py` and focused hook tests | One safe advisory appears before execution, the command is unchanged, and no validation outcome is credited. |
| P1 | Stop describes the configured `.ok` marker as if the validation command writes it directly. | Command outcomes are session-scoped; Stop creates `.ok` only after all current outcomes are satisfied. [F3] | `core/hooks/shared/stop-finish-line-gate.py` and message assertions | The prompt accurately names contract, outstanding work, session outcome recording, and Stop consolidation. |
| P2 | Consumer guidance does not make toolchain ownership explicit. | A correct interactive toolchain preamble conflicts with the intentionally strict proof rule. [F2] [F4] | Runtime-kit validation guidance near the finish-line policy | Maintainers are directed to put runtime selection inside a declared wrapper, not around declared commands. |

## Implementation Boundaries

### Runtime-kit

- `core/hooks/shared/finish-line-record.py`
  - Detect the `matches != [] && !outcome_status_is_provable(...)` state.
  - Emit one non-blocking advisory without registering pending outcome files,
    rewriting the command, or changing its permission decision.
  - Keep generated-wrapper detection and exact provable rewrites unchanged.
- `core/hooks/shared/stop-finish-line-gate.py`
  - Replace the ambiguous marker sentence with lifecycle-accurate guidance.
  - Preserve existing failure routing, waiver guidance, and outstanding-command
    detail.
- `tests/hooks/test_shared_hooks.py`
  - Add focused assertions for the advisory, privacy boundary, lack of credit,
    exact-chain credit, and Stop wording/lifecycle.
  - Retain the existing sensitive-preamble and status-masking regressions.
- Shared render/golden or agent-hook parity fixtures
  - Update only if the provider-native advisory changes rendered contract
    output.
- Finish-line policy documentation
  - Document the repository-owned wrapper pattern and the reason arbitrary
    setup preambles remain uncredited.

### Agent Console Follow-Up

- Add one repository-owned `project-dev` validation wrapper.
- Make the wrapper select and verify Node.js 24 before running the existing five
  validation phases in their current order with failure-preserving semantics.
- Replace the five bare `AGENT_DOCS.toml` commands with the one wrapper command.
- Update `DEVELOPMENT.md` so humans and agents use the same entrypoint.
- Do not encode host-specific absolute paths or assume an already-activated
  interactive shell.

## Requirements

- **R1**: Exact declared validation and an `&&` chain composed exclusively of
  declared commands retain their current credit behavior.
- **R2**: A command containing declared validation but with an unprovable
  aggregate status remains uncredited and unmodified.
- **R3**: The R2 path emits exactly one non-blocking advisory per tool
  invocation with a stable reason class and actionable recovery.
- **R4**: Advisory output must not reproduce the raw command, shell preamble,
  environment values, paths not already present in the declared contract, or
  other potentially sensitive submitted content.
- **R5**: The advisory must not claim the validation failed; it states only
  that the hook cannot prove and record its aggregate outcome.
- **R6**: Stop guidance must accurately distinguish session outcome evidence
  from the configured consolidated marker.
- **R7**: Failed validation outcomes, current-edit freshness, marker safety,
  waiver handling, and discovered-defect routing remain unchanged.
- **R8**: Codex and Claude expose equivalent semantics through the shared hook
  source.
- **R9**: The Agent Console wrapper must run every existing project-dev phase,
  fail on the first failing phase, and prove Node.js major 24 before package
  execution.
- **R10**: The Agent Console declared command must be usable from a clean
  non-interactive shell without a caller-provided toolchain preamble.

## Acceptance Criteria

- **A1**: An exact declared command is wrapped for outcome recording; a
  successful run releases Stop as it does today.
- **A2**: An `&&` chain whose every segment is declared is wrapped once and
  records each matched command outcome.
- **A3**: A toolchain preamble followed by the declared validation chain runs
  unchanged, emits `validation_outcome_unprovable`, creates no pending/ran
  outcome evidence, and leaves Stop outstanding.
- **A4**: `validation; true`, `validation || true`, a pipeline, background
  execution, grouping, and a non-validation prefix remain uncredited and
  receive the same bounded advisory when a declared invocation is detected.
- **A5**: A sensitive preamble such as a destructive command is neither
  authorized nor echoed by finish-line feedback; other policy hooks retain
  authority to block it.
- **A6**: A command that merely prints, quotes, or embeds validation as inert
  here-document data receives neither credit nor the matched-validation
  advisory.
- **A7**: Already generated validation wrappers are not nested or warned.
- **A8**: A failed exact validation records its failure and Stop retains the
  existing exit-code-aware guidance.
- **A9**: After every current command outcome succeeds, Stop creates the
  configured `.ok` marker, cleans completed session state, and returns allow.
- **A10**: Stop text no longer claims the validation command directly writes
  `.ok`; message tests cover both outstanding and satisfied lifecycles.
- **A11**: Codex and Claude parity fixtures pass with no product-specific
  behavior drift.
- **A12**: In the Agent Console follow-up, invoking the one declared wrapper
  from the host's default Node.js 26 environment runs all package phases under
  Node.js 24 and is credited without an external setup preamble.
- **A13**: If Node.js 24 cannot be selected or verified, the Agent Console
  wrapper fails before package validation and Stop remains outstanding.

## Validation Plan

### Runtime-kit

Run focused hook tests while iterating, then the declared repository validation:

```bash
python3 -m unittest tests.hooks.test_shared_hooks.SharedHookTests
bash tests/hooks/run.sh
bash scripts/ci/all.sh
```

Use the repository's accepted test runner form if the focused unittest class
name changes. The final two commands are authoritative.

### Agent Console Follow-Up

Capture test-first evidence for the toolchain contract before editing the
wrapper or catalog. Validate:

```bash
bash scripts/validate-project-dev.sh
```

The test fixture must start from a non-Node.js-24 caller environment, assert
that package phases observe Node.js 24, and cover missing-toolchain failure.
Then run any dedicated Android/macOS checks required by the actual consumer
diff; the wrapper change alone must not be treated as an app artifact release.

## Risks And Guardrails

- **False credit**: broader shell recognition could let a successful suffix
  mask failed validation. Guardrail: diagnostics do not alter the existing
  proof predicate or register outcome state.
- **Sensitive command disclosure**: a helpful message could echo setup values
  or destructive input. Guardrail: emit a fixed reason class and contract-level
  remediation only.
- **Warning fatigue**: one invocation can match multiple declared commands.
  Guardrail: aggregate into one advisory per tool call.
- **Toolchain drift**: a wrapper that merely checks the caller's runtime would
  still fail on ordinary hosts. Guardrail: the consumer wrapper owns selection
  and verification and remains portable across supported non-interactive
  shells.
- **Contract duplication**: maintaining both a wrapper and five catalog
  commands would create two sources of truth. Guardrail: declare only the
  wrapper and keep phase sequencing inside it.
- **Misleading success**: an unprovable command may genuinely pass. Guardrail:
  describe it as uncredited, not failed, and require a creditable rerun.

## Retention Intent

This is coordination material. After both implementation phases ship:

1. retain the settled proof and wrapper guidance in the owning finish-line
   policy/documentation;
2. retain behavior in hook and consumer tests;
3. retain the Agent Console command in its catalog and development guide; and
4. remove this discussion capture rather than preserving duplicate canon.

If implementation is promoted to an L2 tracked plan, move this file into the
plan bundle as its discussion source; do not copy it.

## Read-First References

- `[U1]` User request and observed Stop prompt from the Agent Console completion
  run: preserve the diagnosis for later direct implementation in
  `agent-runtime-kit`, with no GitHub PR during the current provider outage.
- `[F1]` `core/hooks/shared/hook_common.py` —
  `command_matches_validation` and its parsed-invocation boundary.
- `[F2]` `core/hooks/shared/finish-line-record.py` — validation matching,
  aggregate-status proof, pending outcome registration, and PreToolUse rewrite.
- `[F3]` `core/hooks/shared/stop-finish-line-gate.py` — outstanding-command
  prompt construction, `.ok` consolidation, and completed-session cleanup.
- `[F4]` `serenvia/agent-console/AGENT_DOCS.toml`,
  `serenvia/agent-console/package.json`, and
  `serenvia/agent-console/.node-version` — bare validation commands and the
  Node.js 24 contract.
- `[F5]` `tests/hooks/test_shared_hooks.py` — exact-chain credit,
  non-validation preamble refusal, status-masking, and marker lifecycle tests.
- `[A1]` In-session command and Stop evidence: the Node.js 24 preamble run
  passed without credit; the exact bare chain passed under Node.js 26 with an
  engine warning and was credited.

## Recommended Next Artifact

The next artifact should be the runtime-kit implementation change set using
this document as read-first context, followed by a separate Agent Console
consumer change. Re-triage before implementation; if the work remains one
coherent hook change plus tests, keep it at the lowest eligible tier. If it
expands into independently sequenced runtime, schema, or cross-repository
lanes, move this source into an L2 plan bundle before execution.
