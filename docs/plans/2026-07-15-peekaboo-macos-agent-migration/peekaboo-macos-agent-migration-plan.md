# Plan: Replace the macOS automation engine with pinned Peekaboo

## Overview

Execute one serial L2 migration across `sympoies/nils-cli` and
`graysurf/agent-runtime-kit`. First freeze and prove the third-party candidate
and replacement contract. Then replace the native engine with a thin
`macos-agent` adapter, including supply-chain verification, local/SSH transport,
stdio MCP, and a privacy-preserving execution journal. Prove the implementation
on a private macOS target before releasing nils-cli. Finally update the
runtime-kit skill and exact nils-cli pin in one cutover, synchronize installed
surfaces, and run fresh-agent acceptance.

The installed old agent remains untouched during branch development, but the
new release contains only the Peekaboo adapter. Rollback is the previous
released package/backend receipt, not an in-process legacy switch.

## Read First

- Primary source: `docs/plans/2026-07-15-peekaboo-macos-agent-migration/peekaboo-macos-agent-migration-discussion-source.md`
- Source type: `discussion-to-implementation-doc`
- Runtime-kit policy: `DEVELOPMENT.md`, `core/policies/work-tier-levels.md`,
  `core/policies/git-delivery.md`, `core/policies/files-hooks-validation.md`,
  `core/policies/evidence-control-plane.md`, and
  `docs/source/docs-placement-retention-policy-v1.md`
- nils-cli policy: `AGENTS.md`, `DEVELOPMENT.md`,
  `docs/runbooks/cli-completion-development-standard.md`,
  `docs/runbooks/new-cli-crate-development-standard.md`, and
  `docs/specs/crate-docs-placement-policy.md`
- Upstream candidate: <https://github.com/openclaw/Peekaboo/releases/tag/v3.9.3>
- Open questions carried into execution: none; the actual nils-cli release tag
  is the tag produced by Task 3.3 and is consumed mechanically afterward

## Scope

- In scope: exact Peekaboo lock and provenance; user-scope backend lifecycle;
  new adapter CLI/JSON/exit contracts; local and SSH execution; scenario file
  staging; artifact transfer/cleanup; stdio MCP proxy and tool profiles;
  always-on structural journals; redaction, replay, failure review/routing;
  removal of custom native backends; docs/completions/licenses; deterministic
  and private live acceptance; nils-cli release; runtime-kit skill/matrix/pin
  cutover; installed-surface and fresh-session acceptance.
- Out of scope: forking/vendoring Peekaboo; translating its entire CLI grammar;
  AI agent/analysis, browser MCP, shell, audio, permission mutation, HTTP/SSE
  MCP, macOS before 15, locked-session automation, TCC bypass, or retaining the
  old native engine in the new release.

## Execution Model

- Work tier: L2, one plan-tracking issue in `graysurf/agent-runtime-kit`.
- Branches: one managed nils-cli worktree branch
  `feat/peekaboo-macos-agent-adapter`, then one runtime-kit branch
  `feat/peekaboo-macos-agent-cutover`.
- PR ordering: nils-cli implementation PR -> explicit release authorization and
  released tag -> one runtime-kit skill/pin cutover PR -> private deployment.
- All tasks are serial because the command contract, release tag, and runtime
  pin are hard dependencies. Review may use independent specialist reviewers,
  but no implementation lane mutates shared surfaces concurrently.
- The existing dirty primary nils-cli checkout is not reused. Create the agent
  branch with `git-cli worktree`; preserve unrelated user changes.
- Provider-visible records use generic runtime roles. Host aliases, users,
  private paths, credentials, and raw desktop artifacts remain local.

## Assumptions

1. The private macOS role continues to provide an active, unlocked GUI session
   during live tests; tests do not attempt to create that session.
2. Peekaboo `v3.9.3` remains the candidate unless Task 1.1 finds a newer release
   or security fact that justifies an explicit reviewed lock change.
3. Runtime-kit's existing `meta:nils-cli-bump` workflow remains the owner of the
   exact nils-cli pin transition.
4. Nils-cli release dispatch waits for the later explicit consent required by
   `project-release-nils-cli`; the plan does not interpret authoring this bundle
   as release-time consent.
5. Live acceptance uses synthetic/public data and read-only authenticated-page
   inspection. It does not generate, rotate, revoke, paste, or expose a real
   credential merely to prove the automation path.

## Sprint 1: Freeze provenance, contract, and red baseline

**Goal**: Make the upstream candidate, behavior delta, affected tests, evidence
layout, and public capability claim machine-reviewable before production edits.

**Demo/Validation**:

- `plan-tooling validate` passes for this bundle.
- Candidate tag/commit/assets/checksums are read back from GitHub and recorded.
- Test-first v2 records pass `check --phase pre-edit` in every repo before its
  production files are changed.

### Task 1.1: Review and freeze the Peekaboo candidate

- **Location**:
  - `sympoies/nils-cli/crates/macos-agent/peekaboo-lock.json` (new)
  - `sympoies/nils-cli/crates/macos-agent/docs/reports/peekaboo-candidate-review.md` (new, transient until promoted or removed at closeout)
  - private `agent-out` provenance directory
- **Description**: Recheck the latest official release, security advisories,
  tag verification, immutable commit, release notes, license, macOS floor,
  universal CLI/app asset names and SHA256, and upstream command/security docs.
  Download into the evidence directory, verify archive contents against path
  traversal/symlink surprises, inspect executable architectures, record
  `codesign` identity and entitlements, and run `spctl`/notary verification on
  the macOS target. Freeze the reviewed candidate in the lock. A candidate
  newer than `v3.9.3` is allowed only through an explicit lock diff plus the
  same review; never resolve `latest` at runtime.
- **Dependencies**:
  - none
- **Complexity**: 6
- **Acceptance criteria**:
  - Lock contains repository, tag, commit, asset URLs/names/SHA256, minimum
    macOS, architecture, executable/app identity, signing identity, and required
    capability probes.
  - Tag commit is verified and every downloaded digest matches both the lock and
    official checksum asset.
  - CLI and app pass architecture, code-signature, Gatekeeper/notary, and
    version probes; failures are retained as blockers, not waived.
  - MIT license/notice obligations and redistribution/install model are
    reflected in nils-cli third-party docs.
  - No archive content can escape the staging root or replace an unowned path.
- **Validation**:
  - GitHub API read-back for release/tag/commit verification
  - `shasum -a 256` or `sha256sum` for both assets
  - `file`, `lipo -info`, `codesign --verify --deep --strict --verbose=2`,
    `codesign -dv --verbose=4`, and `spctl -a -vv`
  - JSON-schema/serde test for `peekaboo-lock.json`

### Task 1.2: Declare test impacts and capture meaningful red

- **Location**:
  - nils-cli `crates/macos-agent/tests/`, `completions/`, and test-first evidence
  - runtime-kit `tests/runtime-smoke/cases/computer-use/`,
    `tests/runtime-smoke/acceptance-matrix.yaml`, and test-first evidence
- **Description**: Initialize separate v2 test-first records. Group every
  materially affected existing test by protected behavior and disposition.
  Keep/update the binary/version/JSON/error/completion invariants; replace the
  old AX/input/screenshot/preflight/scenario tests only after new
  adapter/backend/transport/journal tests protect the retained outcome; remove
  old engine-private tests as superseded only when their public behavior is
  covered. Add failing contract tests for the new CLI, exact lock, transport,
  journal, replay, redaction, MCP, skill, and capability-matrix expectations.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 7
- **Acceptance criteria**:
  - Both records list retained/changed/added/removed behavior and grouped test
    dispositions with rationale and validation scope.
  - Meaningful failing tests fail because the new contract is absent, not from
    compilation, setup, network, target availability, or unrelated failures.
  - Existing real-app tests are classified as reusable live assertions,
    replace-with-Peekaboo assertions, or retired engine-private tests.
  - `test-first-evidence check --phase pre-edit` passes before production edits.
- **Validation**:
  - Focused failing cargo integration/contract tests
  - Failing runtime-kit computer-use smoke/contract fixture
  - `test-first-evidence show` and `check --phase pre-edit --format json`

## Sprint 2: Implement the thin nils-cli adapter

**Goal**: Replace custom native automation with a small, testable Peekaboo
control plane while preserving outcome behavior and adding the journal.

**Demo/Validation**:

- Fake backend and fake SSH tests pass on Linux without a GUI.
- macOS-only provenance/Bridge/TCC tests are explicitly separated.
- `tokei`/line inventory and source review show no new native AX/input/capture
  engine in `macos-agent`.

### Task 2.1: Implement backend install, verification, doctor, and rollback

- **Location**:
  - `sympoies/nils-cli/crates/macos-agent/src/backend/mod.rs`
  - `sympoies/nils-cli/crates/macos-agent/src/cli.rs`
  - `sympoies/nils-cli/crates/macos-agent/src/model.rs`
  - `sympoies/nils-cli/crates/macos-agent/tests/integration/backend.rs`
- **Description**: Implement the lock reader and `backend
  install|status|verify|rollback`, plus the backend portion of `doctor` and
  `capabilities`. Use a user-scoped versioned install, stable app path, atomic
  receipts/current switch, one previous version, strict ownership checks, and
  dry-run. Verify before activation and on every operation at the appropriate
  fast/strict level. Never mutate TCC or overwrite an unowned Peekaboo install.
- **Dependencies**:
  - Task 1.2
- **Complexity**: 9
- **Acceptance criteria**:
  - Install is idempotent for the locked version and atomic under interruption.
  - Digest, version, architecture, signing, notary, app/CLI mismatch, truncated
    download, archive traversal, symlink escape, and conflicting install fail
    closed with typed JSON errors.
  - Dry-run performs no filesystem/network-visible mutation beyond approved
    evidence output.
  - Rollback only selects the verified previous receipt and itself supports
    dry-run; an invalid previous version cannot become current.
  - Status/doctor never expose user paths and identify effective runtime,
    permissions, Bridge state, and capability gaps separately.
- **Validation**:
  - `cargo test -p nils-macos-agent backend`
  - failure-injection tests for each acceptance path
  - live isolated install/verify/rollback rehearsal on the macOS role

### Task 2.2: Implement local/SSH exec, scenario transport, and artifacts

- **Location**:
  - `sympoies/nils-cli/crates/macos-agent/src/transport/mod.rs`
  - `sympoies/nils-cli/crates/macos-agent/src/commands/exec.rs`
  - `sympoies/nils-cli/crates/macos-agent/src/commands/scenario.rs`
  - `sympoies/nils-cli/crates/macos-agent/tests/integration/transport.rs`
- **Description**: Implement `exec` and `scenario`. For SSH, call an internal
  versioned remote endpoint of the same `macos-agent` binary and send a JSON
  request over stdin; do not interpolate user arguments into a remote shell
  string. Validate host syntax, require batch authentication, bound connection
  and action timeouts, stage scenario/artifacts with 0700 directories and 0600
  files, verify hashes, pull only manifest-declared artifacts, and audit cleanup.
  Preserve upstream JSON and exit meaning inside the adapter envelope. A
  mutating timeout is `unknown`, never a blind retry.
- **Dependencies**:
  - Task 2.1
- **Complexity**: 9
- **Acceptance criteria**:
  - Local and SSH paths accept identical passthrough argv, including Unicode and
    whitespace, without command injection or option confusion.
  - SSH alias/address, username, home paths, config/key paths, raw remote
    request, and private error text never appear in stdout or retained records.
  - Protocol stdout is exactly one JSON envelope; logs/progress use stderr.
  - Remote artifacts are allowlisted, hash-verified, path-confined, and removed
    after success, failure, timeout, signal, and transfer error.
  - Scenario partial output is retained on upstream failure and the local source
    file is not modified.
  - Unsupported/missing backend, version mismatch, malformed upstream JSON,
    timeout, signal, SSH failure, and cleanup failure have distinct results.
- **Validation**:
  - `cargo test -p nils-macos-agent transport`
  - fake SSH/backend tests with malicious host/argv/path/output fixtures
  - local-vs-SSH golden envelope comparison and secret/path leak scan

### Task 2.3: Implement journal, redaction, guarded replay, and review

- **Location**:
  - `sympoies/nils-cli/crates/macos-agent/src/journal/mod.rs`
  - `sympoies/nils-cli/crates/macos-agent/docs/specs/macos-agent-journal-v2.md`
  - `sympoies/nils-cli/crates/macos-agent/tests/integration/journal.rs`
- **Description**: Implement `manifest.json`, atomic `steps.jsonl`, artifact
  index, summary, review, and redaction records from the source contract. Add
  deterministic command/tool risk classification, failure normalization,
  snapshot lineage, significant-defect detection, and `safe|conditional|never`
  replay. `replay-plan` is read-only; `replay-step` reruns doctor/state guards
  and writes a child record. Redaction occurs before persistence and failure to
  redact blocks artifact publication.
- **Dependencies**:
  - Task 2.2
- **Complexity**: 10
- **Acceptance criteria**:
  - One interrupted/partial append does not corrupt earlier records; recovery
    reports and quarantines the incomplete tail.
  - Sequence/correlation/parent IDs, backend digest, runtime, sanitized command
    shape, pre/postcondition refs, duration/retry/status/failure/replay class,
    and artifact refs validate against a versioned schema.
  - Seeded secrets, typed text, clipboard values, AX values, titles, host/user
    paths, SSH config/key material, and private error strings do not survive in
    minimal/debug/sensitive records contrary to their mode.
  - Safe replay succeeds only after state validation; conditional replay needs
    explicit confirmation; stale snapshot, state mismatch, changed backend,
    secret, external, destructive, and unknown mutation are refused.
  - Review clusters repeated signatures and flags every mandatory significant
    defect with the correct proposed owner, without creating an issue itself.
  - Raw upstream data and screenshots are never promoted automatically.
- **Validation**:
  - `cargo test -p nils-macos-agent journal`
  - property/fuzz-style redaction and malformed/partial JSONL cases
  - crash/signal/file-permission/concurrency/replay-policy fault injection
  - repository/evidence leak scan with seeded canary values

### Task 2.4: Implement stdio MCP/tool profiles and retire the old engine

- **Location**:
  - `sympoies/nils-cli/crates/macos-agent/src/commands/mcp.rs`
  - `sympoies/nils-cli/crates/macos-agent/src/lib.rs`
  - `sympoies/nils-cli/crates/macos-agent/src/run.rs`
  - `sympoies/nils-cli/crates/macos-agent/tests/integration.rs`
  - `sympoies/nils-cli/crates/macos-agent/README.md`
  - `sympoies/nils-cli/crates/macos-agent/docs/README.md`
  - `sympoies/nils-cli/completions/bash/macos-agent`
  - `sympoies/nils-cli/completions/zsh/_macos-agent`
  - `sympoies/nils-cli/BINARY_DEPENDENCIES.md`
  - `sympoies/nils-cli/THIRD_PARTY_LICENSES.md`
  - `sympoies/nils-cli/THIRD_PARTY_NOTICES.md`
- **Description**: Add an stdio JSON-RPC proxy for local/SSH Peekaboo MCP,
  enforce `observe|interact|extended` tool profiles and hard denials, and journal
  sanitized call metadata. Then remove the old native backend/AX/input/capture/
  profile implementation and its private tests, update docs/help/completions and
  third-party notices, and retain only tests protecting the new public adapter.
  Keep no compatibility engine or hidden legacy flag; removed commands receive
  a concise migration error only if needed for operator clarity.
- **Dependencies**:
  - Task 2.3
- **Complexity**: 9
- **Acceptance criteria**:
  - MCP initialization/tools/list/call/cancel/shutdown work locally and through
    SSH without non-protocol stdout or payload leakage.
  - Tool profiles expose exactly their declared set; AI/browser/shell/audio/
    config/permission-mutation/`mcp_agent` are unavailable even if upstream
    config or API keys exist.
  - Sensitive MCP arguments/results are represented only by safe metadata.
  - No active source calls Hammerspoon, cliclick, custom AppleScript AX/input,
    or the old screen-record adapter for UI behavior.
  - Help, README, JSON docs, exits, completions, license/notices, and examples
    match the new stable surface and use no floating install instruction.
- **Validation**:
  - MCP frame/stdio cleanliness and allow/deny integration tests
  - `cargo test -p nils-macos-agent`
  - completion generation, zsh/bash syntax, and freshness audits
  - source grep/inventory proving the legacy engine is absent

## Sprint 3: Prove live behavior and release nils-cli

**Goal**: Demonstrate that the replacement is complete, private, recoverable,
and better debuggable before any runtime-kit consumer pin changes.

**Demo/Validation**:

- Full nils-cli local and provider gates pass.
- A private evidence bundle contains one row per capability assertion and one
  complete journal/review/rollback example.
- The nils-cli PR is reviewed/merged and its release assets are verified before
  runtime-kit consumes the new tag.

### Task 3.1: Run deterministic, security, and release-readiness validation

- **Location**:
  - nils-cli repo-wide validation and private `agent-out` evidence
- **Description**: Run focused, affected-suite, workspace local-fast,
  docs/license/completion audits, coverage, leak scans, installer/replay fault
  injection, and release dry-runs. Exercise Linux-compatible fake tests and
  macOS-only gates without conflating host-capability skips with passes. Finalize
  the nils-cli test-first record with no unclassified residual gap.
- **Dependencies**:
  - Task 2.4
- **Complexity**: 7
- **Acceptance criteria**:
  - Focused and affected tests pass; workspace required checks and coverage
    threshold pass in provider CI.
  - Every seeded supply-chain, injection, traversal, redaction, cleanup,
    protocol, journal, and replay failure is caught.
  - Supported macOS-only cases are clearly pending live Task 3.2, not reported
    green from mocks.
  - Final test-first evidence records focused, affected-suite, workspace, and
    residual-gap outcomes and verifies.
- **Validation**:
  - `cargo test -p nils-macos-agent`
  - `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`
  - `bash scripts/ci/completion-freshness-audit.sh --strict`
  - `bash scripts/ci/docs-placement-audit.sh --strict`
  - nils-cli publish/release dry-run for the affected crate/workspace

### Task 3.2: Run the private macOS capability and journal canary

- **Location**:
  - private macOS runtime role
  - private `agent-out` live-acceptance directory
- **Description**: Install the candidate into an isolated backend path with the
  branch binary and exercise both local and SSH transport. Use Calculator and a
  disposable text fixture for action-first and synthetic input; app/window/menu
  operations; background and foreground delivery; inspect UI, snapshots,
  screenshots, set-value/action, gestures, waits, scenario partial failure,
  MCP stdio, tool denials, and journal/replay/review. Inspect one authenticated
  browser settings journey read-only and stop before any credential creation or
  external submission. Compare local/SSH envelopes, run repeated stability
  loops, and execute an isolated install/rollback/reinstall drill.
- **Dependencies**:
  - Task 3.1
- **Complexity**: 10
- **Acceptance criteria**:
  - `doctor --strict` proves locked version/digest/signature/notary, app runtime,
    Bridge health, TCC readiness, and exact tool profile.
  - Action-first click and direct AX action independently pass; synthetic input
    independently passes; every mutation has an observed postcondition.
  - Local/SSH inspect, capture, scenario, artifact transfer, MCP, journal, and
    review results are semantically equivalent and privacy-clean.
  - Sensitive-mode typing uses synthetic non-secret text, retains no value or
    screenshot, and is classified `never` for replay.
  - Scenario fail-fast/continue modes preserve per-step timing and partial
    results; safe replay resumes at a failed observation without repeating
    protected mutations.
  - Observe/interact/extended profiles have positive cases; all hard-denied
    tools and unsupported HTTP/SSE/browser/locked-session claims have negative
    evidence.
  - Repeated read-only and bounded action loops complete within explicit
    timeouts with zero hang/crash; p50/p95 and retry counts are recorded.
  - Rollback selects the previous verified receipt, doctor passes, and the
    candidate can be reinstalled without new drift or losing the stable app
    identity.
  - No real private key/token/account mutation is created solely for testing.
- **Validation**:
  - machine-readable live capability matrix with pass/fail/unsupported rows
  - local and SSH journal/redaction/leak audits
  - `journal summarize`, `journal review`, and guarded replay read-back
  - install -> verify -> rollback -> verify -> reinstall -> verify drill

### Task 3.3: Review, merge, release, and verify nils-cli

- **Location**:
  - `sympoies/nils-cli` implementation PR and release workflow
- **Description**: Run testing, security, and maintainability specialist review
  with particular attention to installer trust, shell/SSH boundaries,
  redaction, replay, MCP framing, and removal completeness. Resolve all findings
  and threads, pass provider checks, deliver the nils-cli PR, then pause for the
  explicit release consent required by `project-release-nils-cli`. After
  consent, release exactly the merged revision, verify GitHub/Homebrew assets,
  install it in an isolated path, and record the actual tag/digests for Sprint 4.
- **Dependencies**:
  - Task 3.2
- **Complexity**: 8
- **Acceptance criteria**:
  - All specialist findings and provider threads are resolved; required checks
    and test-first delivery gate pass.
  - Merged source equals the live-tested revision except reviewed integration
    changes that reran all affected acceptance.
  - No release dispatch occurs before the later explicit consent.
  - Released `macos-agent --version`, help, lock, binary artifacts, Homebrew
    formula, and checksums agree with the merged revision.
  - Clean install plus `backend status/verify` works from the released package.
- **Validation**:
  - `pr:deliver-pr` review/check/thread/task gates
  - `project-release-nils-cli` prepare, approved dispatch, and workflow monitor
  - release/API/checksum/Homebrew clean-install read-back

## Sprint 4: Cut over runtime-kit skill and exact nils-cli pin

**Goal**: Make the released adapter the only active computer-use route across
Codex, Claude, and Hermes in one reviewed runtime-kit PR.

**Demo/Validation**:

- Rendered skills use released `macos-agent` directly and document the journal.
- Runtime-kit's exact pin and required CLI floor match the new release.
- Full CI/hooks pass on-pin and stale helper files disappear from clean installs.

### Task 4.1: Replace the computer-use skill and publish the capability matrix

- **Location**:
  - `core/skills/computer-use/macos-desktop/SKILL.md.tera`
  - `core/skills/computer-use/macos-desktop/references/setup.md`
  - `core/skills/computer-use/macos-desktop/bin/macos_desktop.py`
  - `core/skills/computer-use/macos-desktop/scripts/macos-desktop.sh`
  - `docs/source/macos-agent-capability-matrix.md` (new)
  - `tests/runtime-smoke/cases/computer-use/run.sh`
  - `tests/runtime-smoke/acceptance-matrix.yaml`
- **Description**: Capture runtime-kit meaningful red, then rewrite the skill to
  call released `macos-agent` directly. Teach AX/visual selection, tool profiles,
  evidence modes, approvals, postconditions, journal/replay rules, significant
  defect review, and outcome routing without copying the full Peekaboo manual.
  Remove the Python transport/session implementation. Promote the tested matrix
  to canonical docs and ensure unsupported/disabled rows are visible choices,
  not hidden caveats.
- **Dependencies**:
  - Task 3.3
- **Complexity**: 8
- **Acceptance criteria**:
  - The skill allocates one `agent-out` root, runs doctor through the real
    transport, uses `exec|scenario|mcp`, validates postconditions, summarizes and
    reviews journals, and routes significant defects without automatic issue
    mutation.
  - `minimal|debug|sensitive`, `app|daemon|auto|process`,
    `observe|interact|extended`, CLI/scenario/MCP, and replay choices are clear.
  - Helper-owned SSH, transfer, redaction, and session code is absent; nils-cli
    is the single deterministic owner.
  - Canonical matrix names every supported/adapter/optional/disabled/unsupported
    capability and the evidence proving it.
  - Setup pins the nils-cli-provided backend path and contains no floating
    Peekaboo/Homebrew/npx production install instruction.
  - Smoke tests cover routing, journal files, sensitive redaction, significant
    defect review, local/SSH parity, and negative tool profiles.
- **Validation**:
  - focused runtime-kit computer-use smoke tests via released nils-cli
  - canonical matrix link/status/coverage audit
  - `test-first-evidence check --phase delivery` for runtime-kit

### Task 4.2: Apply the governed nils-cli pin and deliver the cutover PR

- **Location**:
  - `docs/source/nils-cli-pin.yaml`
  - `docs/source/nils-cli-surface.md`
  - `manifests/skills.yaml`
  - `build/codex/`
  - `build/claude/`
  - `build/hermes/`
  - `tests/golden/codex/`
  - `tests/golden/claude/`
  - `tests/golden/hermes/`
  - runtime smoke/product/sandbox expectations
- **Description**: Use `meta:nils-cli-bump` to pin the exact tag from Task 3.3,
  refresh release digests/surface docs, set the `macos-agent` minimum to the
  release that introduced the adapter, render all products, refresh goldens,
  and prove install/prune behavior removes the old helper. Run full on-pin
  validation and specialist review, then deliver the single cutover PR.
- **Dependencies**:
  - Task 4.1
- **Complexity**: 8
- **Acceptance criteria**:
  - Exact pin, human surface snapshot, required CLI floors, rendered skills, and
    goldens agree with the released tag.
  - Codex/Claude/Hermes expose one equivalent macOS desktop outcome with their
    declared capability ceilings; Hermes does not claim hooks it lacks.
  - Clean and upgrade installs contain no stale Python helper/old examples and
    `agent-runtime doctor` reports no version drift.
  - Full CI, hooks, docs impact, provider checks, specialist review, review
    threads, and task list are green/empty before merge.
- **Validation**:
  - `bash scripts/ci/all.sh`
  - `bash tests/hooks/run.sh`
  - focused computer-use runtime smoke and sandbox clean/upgrade install
  - Codex/Claude/Hermes render, golden, list-skills, and doctor read-back

## Sprint 5: Activate, prove future sessions, and close the feedback loop

**Goal**: Deploy only merged/pinned source, prove actual future-agent behavior,
and retain sanitized improvement evidence with a tested rollback.

**Demo/Validation**:

- Both runtime roles report the merged runtime-kit revision and released
  nils/Peekaboo versions.
- Fresh sessions use the new skill, produce a valid journal, and surface the
  correct significant-defect review result.

### Task 5.1: Synchronize the runtime and run fresh-agent acceptance

- **Location**:
  - merged runtime-kit `main`
  - private controller and macOS runtime roles
  - private `agent-out` acceptance directory
- **Description**: Sync managed Codex/Claude/Hermes surfaces from merged main,
  install the released nils-cli and locked Peekaboo backend, run strict doctor,
  and verify revision/skill/pin provenance. Start fresh agent sessions and issue
  natural-language bounded computer-use requests for observation, one AX action,
  one synthetic action, one sensitive-mode fixture, scenario failure/resume,
  and journal review. Confirm no agent invokes the removed helper or disabled
  Peekaboo tools.
- **Dependencies**:
  - Task 4.2
- **Complexity**: 9
- **Acceptance criteria**:
  - Installed receipt/revision and active skill ID match merged runtime-kit and
    released nils-cli; old managed files are absent.
  - Fresh supported product sessions discover and use the skill without naming
    transport/evidence substeps.
  - Every run yields valid manifest/steps/index/summary/redaction; the seeded
    significant failure yields a review candidate with correct owner and no
    provider mutation.
  - Sensitive fixture contains no value/screenshot/replay material.
  - A final `backend rollback --dry-run` plus previous-release runtime dry-run
    proves the operational rollback path without changing the accepted live
    state.
- **Validation**:
  - runtime sync/doctor/list-skills/read-back for all products
  - fresh-session result and private journal schema/leak audits
  - rollback dry-run and prior-release compatibility read-back

### Task 5.2: Review retained evidence and close the L2 tracker

- **Location**:
  - execution-state ledger and L2 tracking issue
  - local evidence archive / `heuristic-inbox` only when warranted
- **Description**: Review all candidate, deterministic, live, release, cutover,
  fresh-session, and rollback evidence. Run `journal review` across acceptance
  sessions, resolve or route every significant defect, migrate only warranted
  sanitized workflow evidence, record residual capability ceilings, and close
  only when both PRs are merged and the installed replacement is proven.
  Ongoing skill behavior keeps reviewing significant future journals; plan
  closeout does not disable the improvement loop.
- **Dependencies**:
  - Task 5.1
- **Complexity**: 5
- **Acceptance criteria**:
  - No significant defect remains unreviewed; project/upstream/adapter/skill/
    environment ownership is explicit for every retained finding.
  - Raw desktop evidence is neither committed nor posted; promoted records are
    sanitized, minimal, verified, and linked to their owner.
  - Test-first, docs-impact, skill-usage (when warranted), provider, live, and
    rollback records verify and are linked from execution state.
  - Tracking issue audit/close-ready passes, both implementation PRs are merged,
    and no task/validation gap is hidden behind a false pass.
- **Validation**:
  - `macos-agent journal review` over all live session roots
  - evidence verification/migration and privacy scan
  - L2 tracking issue audit, PR checks, unresolved-thread/task sweeps, closeout

## Testing Strategy

### Deterministic layers

- Unit/property: lock parsing, SemVer/version comparison, digest/path/signature
  decision logic, tool/risk/replay classification, failure normalization,
  redaction, JSON schemas, atomic records, artifact manifests.
- CLI contract: help/version/completion, text/JSON/error envelopes, exits,
  unknown/removed commands, stdout/stderr boundaries, dry-run.
- Installer integration: HTTP fixtures, truncated/wrong/malicious archives,
  ownership conflicts, atomic activation/crash recovery, current/previous
  receipts, fake codesign/spctl outcomes.
- Transport integration: local/fake SSH parity, stdin request framing, hostile
  host/argv/path/output, timeout/signal/disconnect, remote permissions, transfer
  hashes, cleanup on every exit path.
- Journal integration: partial/concurrent writes, recovery, all evidence modes,
  seeded secrets, replay states, significant-defect clustering, changed backend
  and stale-snapshot rejection.
- MCP integration: initialize/tools/call/cancel/shutdown, stdio cleanliness,
  local/SSH parity, exact profile sets and hard denials, sensitive payload
  suppression.
- Runtime-kit: natural-language routing, direct released CLI usage, generated
  products/goldens, clean/upgrade install, stale helper pruning, capability
  matrix coverage, journal review routing.

### Live macOS layers

- Supply chain and TCC: real downloaded assets, architecture, codesign/notary,
  app Bridge, permission status, effective runtime.
- Observation/action: inspect UI, snapshot, screenshot, action-only AX,
  set-value/action, synth-only pointer/keyboard, gestures, background/foreground,
  window/menu and optional extended surfaces.
- Workflow: `.peekaboo.json` success and partial failure, safe resume,
  conditional/never negative replay, debug/sensitive evidence.
- Transport/MCP: repeat the same assertions over SSH and stdio MCP.
- Stability: repeated bounded read/action loops with explicit timeout, zero
  hang/crash target, and recorded latency/retry distributions.
- Safety ceiling: hard-denied tools, HTTP/SSE, browser MCP, locked session,
  permission mutation, shell/AI/audio, and credential retention are negative
  claims, not skipped positive tests.

## Evidence Layout And Retention

Allocate workflow roots with `agent-out project --topic
peekaboo-macos-agent-<phase> --mkdir`. Each phase retains commands, versions,
digests, validation summaries, schema-verified journal examples, capability
rows, and redaction/leak results. Live raw artifacts remain private and local.

- `candidate`: release/tag/commit/assets/checksums/signing/notary/license.
- `test-first`: one v2 record per edited repository.
- `deterministic`: focused/affected/workspace/fault-injection logs.
- `live-canary`: generic role metadata, capability results, private artifacts,
  journal/review/rollback results.
- `release`: merged revision, tag, workflow, package/formula checksums/read-back.
- `cutover`: pin/render/golden/CI/review/install-prune evidence.
- `fresh-session`: installed provenance and privacy-minimized journals.

Routine raw successful artifacts are cleanup-eligible after closeout according
to local retention policy. Sanitized evidence is promoted only when it proves a
durable decision, defect, or workflow outcome. Security/privacy evidence is
quarantined and reviewed; it is never auto-uploaded.

## Risks And Controls

- **Upstream release churn**: immutable lock plus explicit freshness review; no
  runtime `latest`.
- **Supply-chain compromise**: official assets, Git verification, SHA256,
  codesign/notary, architecture/version/capability probes, atomic ownership.
- **TCC identity drift**: stable signed app default, effective-runtime journal,
  strict doctor and live local/SSH test through the real transport.
- **Breaking old CLI consumers**: inventory callers before removal; runtime-kit
  is cut over immediately after release; no deploy occurs until pin/skill merge.
- **SSH injection or leakage**: versioned stdin request, strict host/path
  validation, no user shell interpolation, redaction-before-persistence.
- **False UI success**: observed precondition, one bounded action, explicit
  postcondition, unknown mutation state after timeout.
- **Replay causes duplicate side effects**: safe/conditional/never policy,
  current-state/backend checks, explicit confirmation, no secret reconstruction.
- **Journal becomes surveillance**: structural minimal default, narrow captures,
  sensitive suppression, local-only raw evidence, reviewed promotion.
- **Upstream powerful tools escape policy**: hard allow/deny profile enforcement
  in both CLI and MCP plus negative tests with hostile upstream config.
- **Release/cutover gap**: release is verified first; runtime deployment waits
  for the single skill/pin cutover PR; previous package remains rollback.

## Rollback Plan

1. Before nils release, delete the managed worktree/backend staging only; leave
   installed production untouched.
2. After a bad nils release but before runtime-kit merge, keep runtime-kit's pin
   and installed surfaces unchanged; supersede the release.
3. After cutover, use the governed runtime-kit pin rollback and
   `macos-agent backend rollback`, resync surfaces, then run strict doctor and a
   read-only smoke test.
4. Never automatically replay mutations during rollback. Quarantine evidence
   for any privacy/security failure and require reviewed remediation.
