# Plan: Add metadata-first agent session coordination

## Overview

Deliver one serial L2 change across `sympoies/nils-cli`,
`graysurf/agent-runtime-kit`, and `serenvia/local-scripts`. Nils-cli first adds
the authoritative work-context claim and private mailbox primitives. After an
explicitly authorized release, runtime-kit consumes the exact version and adds a
catalog-driven `session-coordination` intent plus mutation admission. The private
session skill then exposes the released workflow. Deterministic and bounded live
acceptance prove that disjoint work proceeds, definite overlap blocks, incomplete
metadata never produces a false clear, authenticated claims cover the mutation
they admit, and message content never becomes prompt, coordination summary,
glance, log, or provider content.

The initial enforcement boundary is deliberately narrow: only a deterministic
`conflict` blocks. `potential_conflict`, `unknown`, and `no_known_conflict` are
visible advisories. Existing physical-checkout leases remain authoritative, and
formal delegated implementation continues to use L3 dispatch rather than the
ephemeral mailbox.

## Read First

- Primary source: `docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-discussion-source.md`
- Source type: `discussion-to-implementation-doc`
- Execution state: `docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-execution-state.md`
- Runtime-kit policy: `AGENTS.md`, `DEVELOPMENT.md`,
  `core/policies/work-tier-levels.md`, `core/policies/git-delivery.md`,
  `core/policies/files-hooks-validation.md`,
  `core/policies/evidence-control-plane.md`, and
  `docs/source/docs-placement-retention-policy-v1.md`
- Nils-cli policy: `AGENTS.md`, `DEVELOPMENT.md`,
  `docs/runbooks/new-cli-crate-development-standard.md`,
  `docs/runbooks/cli-completion-development-standard.md`, and
  `docs/specs/crate-docs-placement-policy.md`
- Local-scripts policy: `AGENTS.md`, `README.md`, and `_tools/check.zsh`
- Open questions carried into execution: none; release, installed-surface sync,
  and live-session mutation remain explicit execution-time approval gates

## Scope

- In scope: structured session work context; atomic claim/check/renew/release and
  admit/complete/reconcile operation leases; held-launch broker lifecycle; closed
  scope classification; per-incarnation
  authentication; TTL/heartbeat, fencing, CAS, bound idempotency, quotas, keyed
  checkout fingerprints, privacy-safe coordination summaries; private send/
  inbox/show/ack/reply/wait mailbox; fixed content-free idle notification;
  runtime-kit intent and hook policy; exact nils-cli pin transition; private
  skill update; deterministic and approved live acceptance; governed review,
  delivery, and L2 closeout.
- Out of scope: transcript/log/prompt ingestion; arbitrary prompt forwarding;
  replacing L3 dispatch, provider issues, or execution ledgers; Agent Console UI;
  hard-blocking advisory states; unshared-host consensus; release or runtime
  activation without the later owning-workflow consent.

## Execution Model

- Work tier: L2, one plan-tracking issue in `graysurf/agent-runtime-kit`.
- PR ordering: plan bundle PR -> nils-cli mechanism PR -> explicit nils-cli
  release authorization and release -> runtime-kit policy/pin PR -> local-scripts
  private-skill PR -> acceptance/closeout ledger PR if required.
- Planned implementation branches:
  `feat/agent-session-coordination` in nils-cli,
  `feat/agent-session-coordination-policy` in runtime-kit, and
  `feat/agent-session-coordination-skill` in local-scripts.
- Every implementation lane is serial because the public CLI/schema, released
  version, runtime pin, and downstream skill are hard dependencies. Independent
  reviewer agents may inspect an exact head but must not mutate implementation
  branches.
- Use managed worktrees and preserve unrelated primary-checkout changes. Run
  cross-repository shell mutations from the target repository as CWD.
- Provider-visible records use repository-relative paths, canonical repository
  names, issue/PR links, and redacted evidence summaries. Session IDs,
  incarnations, mailbox bodies, host aliases, users, and machine-local paths stay
  out of provider records.
- Keep the L2 tracker open after the plan PR merges. Close and archive only after
  every implementation and acceptance task is terminal.

## Invariants

1. Work context is explicit structured state, never inferred as authoritative
   from title, cwd, prompt, transcript, log, or assistant output.
2. Standalone check is advisory. Conflict evaluation and claim acquisition are
   one atomic operation, and every admitted mutation target is covered by its
   authenticated claim and operation lease.
3. `clear` means every relevant live session was comparable; incomplete state
   cannot be promoted to clear.
4. Session ID plus incarnation provides fencing, not authority. A private
   per-incarnation capability authenticates every owner/sender/recipient action.
5. Mailbox content remains private at rest and is never copied into list, glance,
   provider evidence, routine logs, hook messages, or notification prompts.
6. Prompt delivery is an at-most-one-attempt optimization only: fixed
   notification text over the structured fenced route when idle and within
   limits; queue-only otherwise.
7. Existing checkout leases, scope locks, work tiers, test-first lifecycle,
   provider review, and delivery gates remain independent requirements.
8. Older clients and unmanaged sessions degrade to unavailable/unknown guidance,
   never a false clear or an unsafe raw-input fallback.
9. Summary and mailbox text is authenticated as peer-supplied data but remains
   untrusted: it cannot authorize actions, approvals, scope changes, or secrets.
10. Numeric size, rate, page, wait, retention, and registry limits make every
    public/read/write path bounded.

## Sprint 1: Establish the durable tracker and test-first contract

**Goal**: Commit the complete bundle, open the L2 control plane, freeze the
versioned runtime contract, and capture meaningful red before nils-cli production
edits.

**PR grouping intent**: `group`

**PR boundary**: one documentation-only runtime-kit plan PR; Task 1.2 supplies
the opening commits of the nils-cli implementation PR grouped with Sprint 2.

**Execution Profile**: serial; Task 1.2 begins only after the committed bundle is
visible in the tracker.

**Demo/Validation**:

- `plan-tooling validate` accepts the three-file bundle.
- The plan-tracking issue and local run state agree on the selected task.
- Nils-cli test-first evidence passes its pre-edit gate with failures caused by
  absent coordination behavior.

### Task 1.1: Commit the plan bundle and initialize the L2 tracker

- **Location**:
  - `docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-discussion-source.md`
  - `docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-plan.md`
  - `docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-execution-state.md`
- **Description**: Validate and commit this source/plan/state bundle on the
  managed documentation branch, open one `graysurf/agent-runtime-kit` L2
  plan-tracking issue through `plan-issue record open --profile tracking`,
  initialize the private run-state record, write the issue and plan PR references
  back to the execution state, and deliver the plan PR without closing the
  tracker. The issue body and comments must contain no local absolute paths or
  live session identifiers.
- **Dependencies**:
  - none
- **Complexity**: 4
- **Acceptance criteria**:
  - The bundle is committed before the provider record snapshots it.
  - `tracking status --expect-visible` resolves one visible issue and one valid
    local run-state record.
  - The execution ledger points to the issue and exact plan commit/PR.
  - The plan PR merges with required checks and independent review; the L2 issue
    remains open with Task 1.2 selected.
- **Validation**:
  - `plan-tooling validate --file docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-plan.md --format text --explain`
  - `git diff --check`
  - `plan-issue tracking status --expect-visible --format json`
  - `bash scripts/ci/all.sh`
  - `bash tests/hooks/run.sh`

### Task 1.2: Freeze the nils-cli coordination specification and meaningful red

- **Location**:
  - `sympoies/nils-cli/crates/agent-session/docs/specs/session-coordination-v1.md`
  - `sympoies/nils-cli/crates/agent-session/tests/integration.rs`
  - `sympoies/nils-cli/crates/agent-session/tests/integration/coordination.rs`
  - `sympoies/nils-cli/crates/agent-session/tests/integration/coordination_server.rs`
  - private nils-cli test-first evidence directory
- **Description**: Translate the source contract into a crate-owned versioned
  specification and initialize test-first v2 evidence, binding the allocated
  private directory as `NILS_COORD_EVIDENCE_DIR`. Add failing tests for
  the closed repository/exact/prefix scope truth table, complete-registry peer
  selection, advisory check versus atomic claim, per-session authorization,
  keyed fingerprint epochs, CAS, long-operation leases, bound idempotency,
  numeric mailbox limits, untrusted-data envelopes, permissions/redaction,
  complete CLI/API selector/exclusion parity, start/run/resume/server held-launch
  boundaries, broker readiness/loss/adoption/cleanup, missed-PostTool
  reconciliation, and notification-attempt crash windows. Declare every affected
  existing start/run/resume/delete/session/list/send/server test as retained,
  changed, replaced, added, or removed before production edits.
- **Dependencies**:
  - Task 1.1
- **Complexity**: 8
- **Acceptance criteria**:
  - The spec freezes schema identifiers; scope grammar/truth table; relevant-peer
    universe; numeric limits/defaults; principal/authorization matrix; capability
    lifecycle; keyed fingerprint/key rotation; claim/operation/message state
    machines; idempotency digest/retention; conflict precedence; error codes;
    CLI/API parity matrix including wait/cancellation; privacy/legacy-list
    compatibility; held-launch/broker entrypoint and failure-boundary matrix;
    execution-token completion/reconcile proof; and at-most-one-attempt
    notification ownership.
  - Meaningful red fails because the coordination contract is absent, not due to
    compilation, setup, timing flake, or unrelated failure.
  - Existing tests have grouped impact dispositions and substitute coverage where
    behavior changes.
  - Negative fixtures prove public identifiers cannot impersonate another
    session, peer text cannot authorize an action, and a narrow claim cannot
    admit an uncovered mutation.
  - The pre-edit readiness check passes against the allocated nils-cli evidence
    directory and repository root before production edits.
- **Validation**:
  - focused failing `cargo nextest run -p nils-agent-session --test integration -E 'test(/coordination/)'`
  - `test-first-evidence show --out "$NILS_COORD_EVIDENCE_DIR" --format json`
  - `test-first-evidence check --out "$NILS_COORD_EVIDENCE_DIR" --project-path . --phase pre-edit --format json`

## Sprint 2: Implement and release the nils-cli mechanism

**Goal**: Ship one authoritative, privacy-preserving coordination engine shared
by CLI and server, then release it through the governed nils-cli workflow.

**PR grouping intent**: `group`

**PR boundary**: one nils-cli feature PR containing Task 1.2 and Tasks 2.1
through 2.4; release occurs only after merge and fresh authorization.

**Execution Profile**: serial within one managed nils-cli worktree; review agents
inspect exact heads without writing.

**Demo/Validation**:

- Isolated registries prove atomic claims and complete mailbox transitions.
- CLI and HTTP routes emit the same schemas and error semantics.
- Privacy scans find no content/path/identity leaks in public projections.

### Task 2.1: Implement structured work context and atomic claims

- **Location**:
  - `sympoies/nils-cli/crates/agent-session/src/coordination/mod.rs`
  - `sympoies/nils-cli/crates/agent-session/src/coordination/context.rs`
  - `sympoies/nils-cli/crates/agent-session/src/coordination/claims.rs`
  - `sympoies/nils-cli/crates/agent-session/src/coordination/broker.rs`
  - `sympoies/nils-cli/crates/agent-session/src/activity.rs`
  - `sympoies/nils-cli/crates/agent-session/src/cli.rs`
  - `sympoies/nils-cli/crates/agent-session/src/lib.rs`
  - `sympoies/nils-cli/crates/agent-session/src/serve.rs`
  - `sympoies/nils-cli/crates/agent-session/tests/integration/coordination.rs`
- **Description**: Implement validated work-context records and
  `work-context claim|show|check|renew|release|admit|complete|reconcile` plus
  `broker status|adopt|reconcile`. Treat check as an advisory snapshot with
  exact self/session/candidate subject exclusion; use one atomic lock/transaction
  for authoritative conflict evaluation plus claim acquisition. Implement the
  closed scope grammar/truth table and complete-registry peer universe, stable
  ordering, broker-issued
  per-incarnation capabilities, registry-keyed checkout fingerprints, revision
  CAS, and a persistent per-session coordination broker sidecar. Route `start`,
  `run`, `resume`, and HTTP create through the reserved-record, held-pane,
  persisted-identity, broker-readiness, then agent-exec transaction; make delete
  revoke/cleanup. Make the broker own credential projection and 30-minute claims.
  Bind operation leases to execution tokens, product activity, and observed
  descendant processes; persist completion retries and reconcile missed PostTool
  without using general pane liveness as operation proof. Define 2-second startup
  readiness, every launch-boundary rollback, older/no-broker unavailable
  behavior, broker-loss fail-closed state, explicit validated adoption, target
  exit cleanup, and replacement fencing. Implement principal/operation/digest-
  bound 24-hour idempotency receipts and stale/released state. The optional HTTP
  server is not required for heartbeat.
- **Dependencies**:
  - Task 1.2
- **Complexity**: 10
- **Acceptance criteria**:
  - Concurrent contenders for a definite scope produce exactly one admitted
    active claim and one deterministic conflict.
  - Same checkout, provider item, plan, and intersecting path scopes classify as
    conflict with stable reasons; same-repository omitted scopes classify as
    potential; unsupported/missing peer context prevents clear.
  - Complete disjoint records return clear; legacy, unsupported, or incomplete
    records return unknown/no-known-conflict according to the requested mode.
  - Wrong principal/incarnation/revision cannot claim, renew, release, admit, or
    complete; same-digest retry returns the original result and mismatched key
    reuse returns a content-free error.
  - A long mutation stays protected across normal TTL. A missing PostTool retries
    durable completion or reconciles only after token/activity/descendant proof;
    live pane alone cannot keep a finished operation active.
  - Start/run/HTTP creation do not exec the agent until a broker is bound to the
    persisted held-pane identity; resume creates a replacement incarnation;
    launcher exit does not stop heartbeat; broker loss blocks new operations;
    adopt validates the unchanged identity; delete/target exit revokes credentials
    and releases terminal state.
  - Every edit/provider target is a subset of the active claim; multi-target,
    symlink, opaque shell, and uncovered-scope fixtures fail according to the
    frozen admission contract.
- **Validation**:
  - `cargo nextest run -p nils-agent-session --test integration -E 'test(/coordination/)'`
  - repeated concurrent-process claim race test
  - property/table tests for canonicalization, scope overlap, peer selection,
    fingerprint epochs, idempotency binding, and precedence
  - fake-clock/process tests for long operations, heartbeat failure, crash,
    replacement, and terminal release
  - start/run/resume/HTTP/delete without-server command tests and crash injection
    after record, held pane, identity, credential, broker spawn/readiness, and exec
  - launcher-exit, broker loss/adoption, missed-PostTool completion/reconcile,
    target-exit cleanup, and older-session unavailable process tests
  - `cargo clippy -p nils-agent-session --all-targets --all-features -- -D warnings`

### Task 2.2: Add privacy-safe CLI and server projections

- **Location**:
  - `sympoies/nils-cli/crates/agent-session/src/lib.rs`
  - `sympoies/nils-cli/crates/agent-session/src/serve.rs`
  - `sympoies/nils-cli/crates/agent-session/src/cli.rs`
  - `sympoies/nils-cli/crates/agent-session/tests/integration/coordination_server.rs`
  - `sympoies/nils-cli/crates/agent-session/README.md`
- **Description**: Expose the versioned work-context CLI JSON envelopes and HTTP
  routes and complete operation parity matrix from the source contract through
  the same library implementation. Authenticate owner routes with the
  per-incarnation capability and keep server operator authority separate. Add
  bounded coordination fields to list/glance containing only claim state,
  expiry, unread count, and conflict severity. Preserve the existing list schema,
  including its legacy `cwd` field, by making only new fields additive; apply
  raw-path privacy assertions to new coordination fields/routes. Define stable
  typed failures for unauthorized principal, unsupported schema, stale
  incarnation, revision/idempotency conflict, invalid/uncovered scope, incomplete
  view, quota/rate/cursor/lock timeout, and unavailable coordination.
- **Dependencies**:
  - Task 2.1
- **Complexity**: 8
- **Acceptance criteria**:
  - CLI and API success/error fixtures are schema-equivalent and versioned.
  - Existing list fixtures and clients, including legacy `cwd`, remain unchanged
    and can ignore additive coordination fields without behavior change.
  - New coordination fields/routes never contain raw cwd, host, username, home
    path, capability, prompt, transcript, mailbox body, or private store location.
  - CLI/API fixtures cover identity, fence, revision, idempotency, timeout,
    cancellation, success, and error behavior for every operation including wait.
  - Check parity covers authenticated self, operator-selected existing session,
    explicit candidate JSON, deterministic subject exclusion/no self-conflict,
    candidate non-suppression, and missing/conflicting-selector rejection across
    the session and registry-level routes.
  - Read operations are bounded and deterministic under corrupt, oversize, and
    partially upgraded registry fixtures.
  - README/spec/completions describe every new flag and compatibility state.
- **Validation**:
  - `cargo nextest run -p nils-agent-session --test integration -E 'test(/coordination_server/)'`
  - unchanged legacy agent-session list/send/server regression suites
  - complete CLI/API parity fixtures and coordination-only privacy-canary scan
  - nils-cli completion and documentation audits

### Task 2.3: Implement the private mailbox lifecycle

- **Location**:
  - `sympoies/nils-cli/crates/agent-session/src/coordination/mailbox.rs`
  - `sympoies/nils-cli/crates/agent-session/src/coordination/mod.rs`
  - `sympoies/nils-cli/crates/agent-session/src/cli.rs`
  - `sympoies/nils-cli/crates/agent-session/src/serve.rs`
  - `sympoies/nils-cli/crates/agent-session/tests/integration/coordination.rs`
- **Description**: Implement `message send|inbox|show|ack|reply|wait` and
  equivalent versioned server routes. Store bounded UTF-8 bodies only in a
  user-private 0700/0600 state root. Authenticate sender and recipient with their
  per-incarnation capabilities; public IDs are selectors only. Bind revisions
  and idempotency receipts to principal/incarnation/operation/request digest.
  Enforce the frozen 16 KiB body, 24-hour default/7-day maximum expiry, 256
  messages and 4 MiB per session, 64 MiB per registry, 30-pair/minute send,
  50/100 page, 60-second wait, and depth-16 reply limits with stable cleanup.
  Return body only in a structured recipient `body` field with authenticated
  sender provenance and an explicit untrusted-data classification. Keep content
  out of summaries, errors, tracing, provider evidence, and routine diagnostics.
- **Dependencies**:
  - Task 2.2
- **Complexity**: 10
- **Acceptance criteria**:
  - Send, list, show, ack, reply, wait, expiry, and cleanup transitions match the
    frozen state machine under success, retry, concurrent access, and crash-tail
    fixtures.
  - Wrong/replaced incarnation and unauthorized session access fail closed.
  - A peer knowing all public identifiers/revisions cannot send as, show, ack,
    reply, wait, renew, or release as another session without its capability.
  - Oversize/invalid input, recursive chains, unbounded waits, permission drift,
    corrupt state, and lock timeout have distinct content-free errors.
  - Store permissions are repaired only when ownership is trusted; an unowned or
    escaping path fails before mutation.
  - Privacy canaries occur only in the explicit recipient `show` result and never
    in list/glance/log/error/API summary output.
  - Concurrent flood/restart fixtures stay within message, byte, rate, page,
    wait, retention, and registry limits without evicting live unread mail.
  - Same-key/different-request, cross-principal/incarnation/operation, concurrent
    retry, and post-expiry cases match the frozen idempotency contract.
- **Validation**:
  - focused mailbox integration and concurrent-process tests
  - filesystem ownership, mode, symlink-escape, corruption, and interruption tests
  - principal authorization and credential-nondisclosure negative tests
  - idempotency, quota/rate, pagination, cleanup, and expiration fake-clock tests
  - untrusted-body authority/scope/secret-exfiltration policy fixtures
  - stdout/stderr/tracing/list/glance privacy-canary scan

### Task 2.4: Add fixed idle notifications without prompt forwarding

- **Location**:
  - `sympoies/nils-cli/crates/agent-session/src/coordination/notification.rs`
  - `sympoies/nils-cli/crates/agent-session/src/serve.rs`
  - `sympoies/nils-cli/crates/agent-session/tests/integration/coordination_server.rs`
  - `sympoies/nils-cli/crates/agent-session/docs/specs/session-coordination-v1.md`
- **Description**: After a successful send, optionally notify an idle managed
  target through the existing structured prompt-v2 route. Generate notification
  text solely from trusted templates and the message ID/read command; never
  interpolate the body. Fence the target incarnation and lifecycle under the
  existing server lock. Before the external call, durably mark one
  `notification_attempting` receipt; never retry after that point, including an
  unknown crash outcome. Enforce one notification attempt per target per minute.
  Queue only when busy, rate-limited, replaced, unmanaged, unsupported, or
  delivery fails. Do not use raw terminal input and do not recursively notify for
  ack, reply receipt, forwarding, or notification-triggered behavior.
- **Dependencies**:
  - Task 2.3
- **Complexity**: 9
- **Acceptance criteria**:
  - Each idempotent send causes at most one fixed content-free notification
    attempt; notification delivery is explicitly best-effort and mailbox read is
    authoritative.
  - Busy, unmanaged, replaced, and unsupported targets keep readable queued mail
    without terminal input or message loss.
  - Body canaries, control characters, and prompt-like text never affect the
    notification bytes.
  - Incarnation changes between send and notify prevent delivery to the new
    runtime while preserving the correct queued message state.
  - Crashes before submit, after prompt acceptance, and before result persistence
    never cause retry/prompt storms; the message remains readable even when the
    optional notification is omitted or its result is unknown.
  - No automatic notification loop or hop chain can be constructed.
- **Validation**:
  - structured prompt-v2 notification contract tests
  - busy/rate-limited/replaced/unsupported/failure and crash-window fixtures
  - exact notification golden and body-noninterference property test
  - raw-input invocation audit

### Task 2.5: Review, merge, release, and verify nils-cli

- **Location**:
  - `sympoies/nils-cli/crates/agent-session`
  - `sympoies/nils-cli/completions`
  - `sympoies/nils-cli/docs`
  - private nils-cli delivery evidence directory
- **Description**: Complete focused and repository-wide validation, bind
  test-first/docs-impact evidence to the exact signed delivery head, binding the
  docs record as `NILS_COORD_DOCS_IMPACT_DIR`, obtain
  independent API, security/privacy, concurrency, testing, and maintainability
  reviews, resolve all actionable threads, and merge the nils-cli PR. Pause for
  fresh explicit authorization before using `private-release-nils-cli`. Verify
  the resulting tag, package, and fixed-fleet installed version before runtime-kit
  consumes it.
- **Dependencies**:
  - Task 2.4
- **Complexity**: 9
- **Acceptance criteria**:
  - Exact-head focused/full gates, provider checks, and required specialist
    reviews pass with zero unresolved actionable threads.
  - Test-first final record binds meaningful red, green, affected tests,
    validation, delivery commit, and no undeclared gaps.
  - Release occurs only after a later exact-version consent and points at the
    approved merged source.
  - Published CLI reports the expected coordination schema/capabilities and the
    fixed fleet reports the exact version.
  - The execution ledger records PR, merge, tag, deployment verification, and
    residuals without private runtime identifiers.
- **Validation**:
  - nils-cli focused agent-session test and clippy suites
  - `bash scripts/ci/nils-cli-checks-entrypoint.sh --local-fast`
  - `test-first-evidence check --out "$NILS_COORD_EVIDENCE_DIR" --project-path . --phase delivery --format json`
  - `docs-impact verify --out "$NILS_COORD_DOCS_IMPACT_DIR" --repo . --format json`
  - provider required checks and zero unresolved review threads
  - released `agent-session --version` and capability/schema smoke

## Sprint 3: Integrate the runtime-kit intent and admission policy

**Goal**: Teach all rendered agents to coordinate before mutable work and enforce
only high-confidence definite conflicts on the exact released nils-cli surface.

**PR grouping intent**: `per-sprint`

**PR boundary**: one runtime-kit feature PR containing the intent, policy, hook,
product surfaces, tests, and exact pin bump.

**Execution Profile**: serial after Task 2.5; use the released pin, never a
floating or locally rebuilt CLI in final validation.

**Demo/Validation**:

- `agent-docs` independently resolves the new intent.
- Hook fixtures block missing own context/definite overlap and advise incomplete
  state without false enforcement claims.
- Codex, Claude, and Hermes rendered surfaces remain converged.

### Task 3.1: Add the session-coordination intent, policy, and meaningful red

- **Location**:
  - `AGENT_DOCS.toml`
  - `AGENT_HOME.md`
  - `core/policies/intent-cards.md`
  - `core/policies/session-coordination.md`
  - `tests/hooks/test_shared_hooks.py`
  - `tests/runtime-smoke/product/routing-contract-cases.json`
  - private runtime-kit test-first evidence directory
- **Description**: Add a home-scoped `session-coordination` intent and durable
  policy containing trigger/must/never/next-action rules from the source, binding
  the allocated private evidence directory as
  `RUNTIME_COORD_EVIDENCE_DIR`. Update
  the concise home prompt and intent cards so mutable workflows classify and
  activate it independently of `project-dev`. First add failing hook/routing
  tests for managed/unmanaged sessions, absent context, definite conflict,
  advisory states, stale/replaced claims, unavailable CLI, and privacy-safe
  recovery. Do not use English keyword matching for intent discovery.
- **Dependencies**:
  - Task 2.5
- **Complexity**: 8
- **Acceptance criteria**:
  - A source-bound strict `agent-docs` preflight requires the declared
    `session-coordination` intent, resolves the expected policy/validation
    entries, and can coexist with project-dev phases.
  - Policy requires metadata-first inspection and forbids automatic log,
    transcript, prompt, or mailbox-body projection.
  - Meaningful red is captured before hook/product production edits.
  - Home prompt stays concise and points detail to the policy/intent card.
  - Formal L3/provider dispatch and existing checkout lease ownership are
    explicitly preserved.
- **Validation**:
  - failing focused `python3 -m unittest tests.hooks.test_shared_hooks`
  - failing product routing contract case
  - `agent-docs preflight --docs-home . --project-path . --intent session-coordination --strict --require-declared-intent --format json`
  - focused positive source-checkout and negative undeclared-intent fixtures
  - `test-first-evidence check --out "$RUNTIME_COORD_EVIDENCE_DIR" --project-path . --phase pre-edit --format json`

### Task 3.2: Implement managed-session admission and render all products

- **Location**:
  - `core/hooks/shared/session-coordination-guard.py`
  - `core/hooks/README.md`
  - `core/hooks/claude/settings.hooks.jsonc`
  - `targets/codex/hooks/config.block.toml`
  - `targets/codex/link-map.yaml`
  - `tests/hooks/test_shared_hooks.py`
  - `tests/runtime-smoke/acceptance-matrix.yaml`
- **Description**: Add a bounded hook guard that capability-detects the released
  CLI, authenticates through the trusted current capability file, and treats
  public ID/incarnation as fencing only. Before each recognized production
  mutation, derive every edit/shell/provider target, prove it is a subset of the
  active claim, atomically re-evaluate peers, and acquire an operation lease.
  Bind the lease to the product turn/tool-call token and observable descendant
  process when available. Persist/retry post-tool completion and support the
  frozen reconcile proof for missing PostTool; pane liveness renews the claim but
  not a finished operation. Block definite peer conflict and all uncovered or
  uncertain own mutation scopes; advisory peer states remain visible.
  Advisory/unavailable/unmanaged paths emit accurate guidance without claiming
  coordination is enforced. Register the guard for Codex and Claude at the
  correct pre/post-mutation and stop audit points, update hook documentation,
  render all products, and retain the physical checkout lease independently.
- **Dependencies**:
  - Task 3.1
- **Complexity**: 10
- **Acceptance criteria**:
  - Managed production mutation without a current own claim is blocked before the
    tool executes and includes bounded claim/recovery commands.
  - A claim for one path cannot authorize a sibling edit, multi-target patch,
    symlink escape, opaque shell write, or unmatched provider mutation; explicit
    repository scope is required for truly opaque repository effects.
  - Definite overlap blocks across separate worktrees; complete disjoint scopes
    proceed; potential/unknown/no-known-conflict remain visible advisories in v1.
  - Read-only tools, agent-docs preparation, claim/release recovery, and governed
    abort paths remain usable without deadlock.
  - Long tools and approval waits retain their operation lease; uncertain
    heartbeat blocks further owner operations and competing admission until the
    frozen recovery proof succeeds.
  - Dropped successful/failed PostTool events replay or reconcile once the exact
    execution token is idle/superseded and no bound descendant remains, without
    terminating the live session or allowing an active tool to overlap.
  - Missing/older CLI and unmanaged sessions degrade accurately without unsafe
    enforcement or breaking core editing.
  - Hook output exposes no mailbox body, raw cwd, session incarnation, host/user,
    capability, or private registry path; peer text remains delimited untrusted
    data and Codex/Claude/Hermes goldens stay converged.
- **Validation**:
  - focused session-coordination hook unit/fixture tests
  - target-subset, multi-target, relative/symlink, opaque-shell, provider, and
    operation-lease fake-clock/process fixtures
  - dropped-PostTool, durable completion retry, activity supersession, descendant
    liveness, owner reconcile, and operator-attested recovery fixtures
  - `bash tests/hooks/run.sh`
  - product render, golden, sandbox, and runtime-smoke suites
  - privacy-canary and hook-timeout/failure-mode tests

### Task 3.3: Apply the exact pin, review, merge, and authorize activation

- **Location**:
  - `docs/source/nils-cli-pin.yaml`
  - `docs/source/nils-cli-surface.md`
  - `docs/source/harness-shape-codex.md`
  - `docs/source/harness-shape-claude.md`
  - `README.md`
  - `manifests/surfaces.yaml`
  - `SUPPORT_MATRIX.md`
  - `docs/source/nils-cli-version-workflows.md`
  - private runtime-kit delivery evidence directory
- **Description**: Use `meta:nils-cli-bump` to consume the exact Task 2.5 release
  and refresh every managed consumer. Run full runtime-kit validation on the
  committed exact head, bind the docs-impact record as
  `RUNTIME_COORD_DOCS_IMPACT_DIR`, complete testing/security/maintainability
  review, resolve threads, and merge the policy/pin PR. Do not sync installed
  Codex/Claude/Hermes homes in this task unless the maintainer gives fresh
  activation approval after reviewing the merged behavior and rollback.
- **Dependencies**:
  - Task 3.2
- **Complexity**: 9
- **Acceptance criteria**:
  - All nils-cli pins/digests/fixtures/rendered consumers name the same released
    version and no development override participates in final validation.
  - `scripts/ci/all.sh` and hook tests pass from a clean committed exact head.
  - Required provider checks and independent reviews pass with no actionable
    thread outstanding.
  - Merge/read-back evidence is recorded in the ledger.
  - Installed-surface sync is either explicitly approved and verified or remains
    a named pending activation gate, not silently inferred from plan approval.
- **Validation**:
  - nils-cli version alignment and baseline tests
  - `bash scripts/ci/all.sh`
  - `bash tests/hooks/run.sh`
  - `test-first-evidence check --out "$RUNTIME_COORD_EVIDENCE_DIR" --project-path . --phase delivery --format json`
  - `docs-impact verify --out "$RUNTIME_COORD_DOCS_IMPACT_DIR" --repo . --format json`
  - provider checks, review-thread audit, and merged-revision read-back

## Sprint 4: Update the private session operator skill

**Goal**: Make the private session workflow use metadata-first discovery and the
released mailbox primitives while preserving mobile handoff and safe fallbacks.

**PR grouping intent**: `per-sprint`

**PR boundary**: one local-scripts feature PR after the runtime-kit pin is
merged; private-skill sync remains separately approval-gated.

**Execution Profile**: serial; no live private-skill overlay mutation during
branch development.

**Demo/Validation**:

- The skill tells an agent to inspect/claim context before mutable start/send.
- Mailbox clarification is explicit and content-safe.
- The local-scripts full shell/skill portfolio gate passes.

### Task 4.1: Extend private-agent-session with coordination and recovery

- **Location**:
  - `serenvia/local-scripts/agent-runtime/.agents/skills/private-agent-session/SKILL.md`
  - `serenvia/local-scripts/tests/private-skill-portfolio-hardening.test`
  - private local-scripts test-first evidence directory
- **Description**: Before editing `SKILL.md`, initialize local-scripts
  test-first evidence at the repository root, bind the allocated private
  directory as `LOCAL_SCRIPTS_COORD_EVIDENCE_DIR`, record the clean baseline
  and affected-test impact, add the focused portfolio assertions, execute and
  record their meaningful coordination-contract failure, and pass the pre-edit
  evidence check. Then update the private skill to require privacy-safe existing-session/
  context inspection before
  starting or sending mutable work, declare/update/release work context, use the
  mailbox only when metadata cannot resolve a material uncertainty, and reply
  through explicit CLI operations. Document fixed notification, queue-only busy
  behavior, stale incarnation recovery, advisory vs blocking states, and the
  prohibition on automatic logs/glance/transcript/raw-prompt coordination. Mark
  summaries and bodies as untrusted peer data that cannot authorize commands,
  approval, scope changes, or secrets. Preserve existing mobile handoff and Agent
  Console usage.
- **Dependencies**:
  - Task 3.3
- **Complexity**: 7
- **Acceptance criteria**:
  - The skill provides exact context and mailbox command shapes without embedding
    secrets, host-local paths, or message content in examples.
  - Definite conflict stops mutable work and gives release/narrow/contact
    recovery; advisory state calls for the smallest necessary inspection/message.
  - Older/unmanaged sessions have an accurate unavailable/unknown fallback and
    are never told to use unsafe raw terminal input.
  - The skill states that L3/provider dispatch remains required for delegated
    implementation.
  - Initialized evidence binds baseline, impact, meaningful failing output, and a
    passing pre-edit check before `SKILL.md` changes; final portfolio tests
    protect every new instruction.
- **Validation**:
  - focused `zsh tests/private-skill-portfolio-hardening.test`
  - `test-first-evidence show --out "$LOCAL_SCRIPTS_COORD_EVIDENCE_DIR" --format json`
  - `test-first-evidence check --out "$LOCAL_SCRIPTS_COORD_EVIDENCE_DIR" --project-path . --phase pre-edit --format json`
  - private skill metadata validator
  - skill content privacy/forbidden-command assertions

### Task 4.2: Review, merge, and optionally synchronize private skills

- **Location**:
  - `serenvia/local-scripts/agent-runtime/.agents/skills/private-agent-session/SKILL.md`
  - `serenvia/local-scripts/tests/private-skill-portfolio-hardening.test`
  - `serenvia/local-scripts/_tools/check.zsh`
  - private local-scripts delivery evidence directory
- **Description**: Run the complete local-scripts gate, bind evidence, obtain
  independent skill-policy/testing review, bind the docs-impact record as
  `LOCAL_SCRIPTS_COORD_DOCS_IMPACT_DIR`, and merge the local-scripts PR. Preview
  the private-skill overlay sync. Apply it only with fresh maintainer approval
  because it changes installed agent behavior; afterward verify both Codex and
  Claude projections and preserve a rollback receipt.
- **Dependencies**:
  - Task 4.1
- **Complexity**: 6
- **Acceptance criteria**:
  - `_tools/check.zsh` passes on the exact committed delivery head.
  - Required checks/reviews pass and all actionable threads are resolved.
  - Merge/read-back and sync dry-run evidence are recorded.
  - Live overlay remains unchanged without fresh approval; when approved, both
    products show the expected skill and a previous receipt supports rollback.
- **Validation**:
  - `./_tools/check.zsh`
  - `test-first-evidence check --out "$LOCAL_SCRIPTS_COORD_EVIDENCE_DIR" --project-path . --phase delivery --format json`
  - `docs-impact verify --out "$LOCAL_SCRIPTS_COORD_DOCS_IMPACT_DIR" --repo . --format json`
  - provider checks and review-thread audit
  - private-skill sync dry-run, and apply/doctor only when approved

## Sprint 5: Prove the cross-session outcome and close the L2 tracker

**Goal**: Validate the released end-to-end contract without private leakage, then
close and archive only after all residuals have owners.

**PR grouping intent**: `group`

**PR boundary**: no production PR by default; use a scoped follow-up PR only for
acceptance-discovered defects or a final execution-ledger update.

**Execution Profile**: serial; deterministic isolated acceptance precedes any
approval-gated live disposable-session canary.

**Demo/Validation**:

- Isolated sessions demonstrate clear, conflict, advisory, stale, and mailbox
  outcomes.
- If approved, disposable managed sessions prove the same behavior through the
  installed surface with synthetic content.
- `tracking close-ready --expect-visible` reports no unresolved tasks, reviews,
  validation gaps, or unowned residuals.

### Task 5.1: Run deterministic multi-session acceptance

- **Location**:
  - `sympoies/nils-cli/crates/agent-session/tests/integration/coordination.rs`
  - `tests/hooks/test_shared_hooks.py`
  - `tests/runtime-smoke/acceptance-matrix.yaml`
  - private cross-session acceptance evidence directory
- **Description**: Run isolated registries and disposable fake runtimes through
  the complete integrated contract: disjoint complete claims, definite overlap
  across worktrees, broad potential overlap, missing legacy context, atomic
  contenders after advisory checks, authenticated narrow-scope admission,
  start/run/resume/HTTP held-launch broker boundaries, launcher exit/loss/
  adoption/delete cleanup, missed-PostTool reconcile, long-operation heartbeat/
  recovery, keyed-fingerprint migration, replaced incarnation, bound-idempotency
  mismatch, mailbox quota/rate/page/wait cleanup, untrusted peer text, busy
  queueing, and at-most-one-attempt notification crash windows. Scan every
  coordination output and retained record for
  body/credential/identity/path canaries while preserving the legacy list fixture.
- **Dependencies**:
  - Task 4.2
- **Complexity**: 8
- **Acceptance criteria**:
  - Every classification and admission outcome matches the source contract.
  - Exactly one concurrent definite claimant is admitted.
  - Public IDs cannot impersonate a session; narrow claims cannot admit uncovered
    edit/shell/provider targets; live operations cannot overlap after normal TTL.
  - Coordination works without the optional HTTP server because every managed
    launch path creates exactly one identity-bound broker before agent exec; it
    survives launcher exit, adopts only by validation, reconciles finished
    operations, and revokes/releases state on delete/target exit.
  - Mailbox content appears only in the explicit recipient read result.
  - Notification bytes are independent of body bytes; busy/rate-limited/replaced
    targets queue without raw input or loss, and unknown outcomes are not retried.
  - Flood and restart cases respect every numeric quota/retention/page/wait bound;
    peer instruction/approval/secret canaries remain data, never authority.
  - All processes, registry roots, claims, and messages are terminally cleaned or
    retained only as privacy-minimized evidence.
- **Validation**:
  - isolated nils-cli coordination integration suite
  - runtime-kit focused hook and runtime-smoke suites
  - repeated claim/check/operation-lease/idempotency concurrency and fake-clock run
  - authorization, quota/flood/restart, and untrusted-data policy matrix
  - coordination-output privacy-canary plus unchanged legacy-list scan

### Task 5.2: Run approval-gated live disposable-session acceptance

- **Location**:
  - private live session-coordination evidence directory
  - `docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-execution-state.md`
- **Description**: After explicit approval to mutate live session state, create
  bounded disposable managed sessions with synthetic/public prompts. Prove one
  disjoint admission, one definite collision and recovery, one idle fixed
  notification attempt/read/ack/reply, one cross-session authorization denial,
  and one busy queue-only delivery. Inspect only
  privacy-safe projections, never arbitrary logs/transcripts. Close disposable
  sessions, release claims, and verify no body appears in list/glance/routine
  logs/provider evidence. If approval is not granted, record a precise live-only
  validation waiver and leave the L2 tracker open unless the maintainer accepts
  that residual.
- **Dependencies**:
  - Task 5.1
- **Complexity**: 7
- **Acceptance criteria**:
  - Live actions occur only after explicit authorization naming the scope.
  - Installed versions/surfaces match the merged receipts before testing.
  - Synthetic content is delivered only through explicit mailbox read, and all
    public projections pass the privacy scan.
  - Collision recovery does not steal/release another session's claim.
  - Disposable sessions and claims are closed/released with read-back evidence.
- **Validation**:
  - installed-surface version and capability read-back
  - privacy-minimized `agent-session list` and work-context checks
  - mailbox send/read/ack/reply and busy queue acceptance
  - terminal session/claim cleanup audit

### Task 5.3: Audit evidence, close the tracker, and archive the plan

- **Location**:
  - `docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-execution-state.md`
  - runtime-kit plan archive
  - private L2 run-state and closeout evidence directories
- **Description**: Reconcile the execution ledger, provider issue, PRs, reviews,
  releases, validation markers, activation receipts, and residual risks. Route any
  reproducible deferred product defect to its owner issue and any agent-workflow
  primitive gap to the heuristic inbox. Run strict close-ready and provider
  read-back, close the L2 issue only when every required task is terminal, then
  preview and apply plan archive migration under its confirmation boundary.
  Remove only session-owned managed worktrees after archive/read-back succeeds.
- **Dependencies**:
  - Task 5.2
- **Complexity**: 6
- **Acceptance criteria**:
  - Execution state contains exact PR/merge/release/validation/activation evidence
    and names every accepted residual with an owner.
  - No required validation, review thread, task, approval, or cleanup remains
    unresolved at close.
  - `tracking close-ready --expect-visible` reports ready and provider close/read
    back confirms the terminal state.
  - Archive migration preserves source, plan, and final state according to the
    repository retention policy.
  - Only session-owned worktrees are removed; unrelated user work remains intact.
- **Validation**:
  - `plan-tooling validate --file docs/plans/2026-07-19-agent-session-coordination/agent-session-coordination-plan.md --format text --explain`
  - `plan-issue tracking close-ready --expect-visible --format json`
  - provider issue/PR/review/release read-back
  - `plan-archive` migration dry-run and post-apply catalog query
  - final managed-worktree and dirty-checkout audit
