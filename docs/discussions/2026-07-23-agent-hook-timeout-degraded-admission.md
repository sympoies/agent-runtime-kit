# Agent-Hook Timeout Degraded Admission Implementation Handoff

- **Status**: decided; implementation-ready; no unresolved design questions
- **Date**: 2026-07-23
- **Source**: In-session diagnosis and policy discussion after governed
  `semantic-commit` attempts failed with
  `agent-hook:dispatch-deadline-exceeded`
- **Intended next step**: implement and locally validate the coupled
  `sympoies/nils-cli` and `agent-runtime-kit` changes without using GitHub
  issues, pull requests, or Actions
- **Related source**:
  `docs/discussions/2026-07-23-local-default-commit-mode.md`
- **Retention**: coordination source; remove after the implementation ships and
  its durable behavior has been promoted into the owning policy and CLI docs

## Purpose

Change hook timeout handling from a dispatcher-wide implicit denial into an
explicit degraded-decision contract. A hook execution deadline is a liveness
boundary for the hook runner, not a deadline for the user's task and not proof
that the requested operation violates policy.

When a rule times out, the dispatcher must preserve completed rule outcomes,
classify the requested operation from trusted local evidence, and either:

- allow an eligible local, reversible operation with a visible warning and a
  durable redacted incident record; or
- retain a closed posture for an external, destructive, secret-sensitive,
  transaction-sensitive, or unresolved operation.

The agent continues eligible work autonomously and reports the anomaly after
the task. This turns timeout events into continuous-improvement input without
making raw hook bypasses part of the normal workflow.

## Confirmed Facts

- `agent-hook 1.25.9` gives all enforced executable capabilities in one
  dispatch a shared two-second child deadline. `reserve_child()` returns
  `dispatch-deadline-exceeded` when the shared budget is exhausted. [F1]
- The evaluator treats every error whose code starts with `dispatch-` as a
  fatal dispatch error. It returns before applying the selected rule's
  `failure_posture`; other capability failures do use `open`, `warn`, or
  `closed`. [F1]
- The Codex `Bash` `PreToolUse` policy selects fourteen ordered runtime-kit
  handlers before the typed coordination lifecycle. A slow handler can consume
  the shared budget and prevent later rules from producing any outcome. [F2]
- `block-unsafe-default-delivery.py` owns a four-second `GitProbe` budget and
  resolves a remote's default branch with live
  `git ls-remote --symref <push-url> HEAD`. [F3]
- A local reproduction of the failed `semantic-commit` shape measured the live
  `block-unsafe-default-delivery` handler at approximately 3.60 seconds; the
  other selected handlers measured approximately 0.05 to 0.13 seconds each.
  The slow handler alone exceeded the dispatch-wide deadline. [A1]
- The repository source, the installed deployment snapshot, and the live
  Codex hook copy had identical SHA-256 digests during the reproduction.
  `agent-hook doctor --all` reported the Codex and Claude installations as
  converged. The defect is present in current source; it is not an undeployed
  source fix. [A2]
- Commit `372d3f0` fixed slow-SSH behavior for exact feature-branch push
  refspecs by allowing a cached default-branch fallback after timeout. It did
  not remove live network access from the hook, did not cover ordinary
  `semantic-commit` default-branch resolution, and predates the shared
  dispatcher deadline integration. [F4]
- The existing error-inbox record already documents 2.5 to 3.6 second SSH
  default-branch probes and the resulting delivery lockout. [F5]
- Current evidence-control-plane policy says timeout, crash, malformed-version,
  and required-capability failures block supported-host repository mutations.
  That statement conflicts with the degraded-admission policy decided here and
  must change with the implementation. [F6]
- Session coordination already establishes the intended precedent: missing or
  incomplete advisory coordination evidence produces degraded guidance and
  must not become a mutation blocker. [F7]
- The provider registration gives the `agent-hook dispatch` process a
  60-second provider timeout. The internal child deadline is therefore a
  runner resource-control choice, not a provider requirement that the user's
  task finish within two seconds. [F8]

## Problem Statement

The current implementation conflates three different states:

1. a rule completed and proved a policy violation;
2. a rule's capability failed or returned malformed output; and
3. the dispatcher stopped waiting for a capability.

Only the first state is a policy decision. The second and third are
infrastructure or availability states that require an explicit failure or
timeout posture. Returning one fatal `dispatch-deadline-exceeded` result loses
the rule identity, skips remaining guards, hides the actionable cause, and
prevents a safe local task even when no rule proved a violation.

Repeatedly increasing the timeout cannot solve this contract error. It only
moves the failure threshold while retaining the same coupling between one slow
capability and the entire task.

## Policy Decisions

1. A hook deadline is a hook-runner liveness boundary. It is not a task
   deadline and is not evidence of a policy violation.
2. `dispatch-deadline-exceeded` must no longer be the provider-visible result
   for an individual runtime handler timeout.
3. Each selected rule receives an independent outcome. One timed-out rule must
   not erase completed outcomes or prevent mandatory later rules from being
   evaluated or explicitly dispositioned.
4. Add a rule-level `timeout_posture` distinct from `failure_posture`.
   Supported values are `closed`, `warn`, and `effect_gated`.
5. Missing `timeout_posture` defaults to `closed` for policy-file backward
   compatibility. Runtime-kit explicitly assigns a posture to every executable
   rule; it does not rely on that compatibility default.
6. `warn` converts a timeout into an aggregate warning and allows the operation
   unless another completed rule blocks it.
7. `closed` converts a timeout into a rule-scoped block with the timed-out rule
   identity. It does not abort evaluation as a dispatcher error.
8. `effect_gated` admits only operations classified as `local_reversible` by
   trusted in-process evidence. Every other effect class receives a rule-scoped
   block.
9. A completed blocking rule always dominates timeout warnings. Degraded
   admission cannot override a proven privacy, ownership, transaction,
   destructive-operation, delivery, or authorization violation.
10. Degraded admission is automatic. The normal recovery path does not use
    shell `!`, disable hooks, modify hook configuration, downgrade locked
    policy, or ask the user to mint a generic bypass.
11. Every allowed timeout produces a redacted local incident record outside the
    repository and a provider-visible context warning containing its incident
    ID.
12. The agent continues the task, then reports the anomaly and incident ID in
    its final response. Reporting does not retroactively change the tool
    outcome and does not require transcript inspection.
13. Pre-tool policy handlers must not perform live network or provider probes.
    Remote truth, compare-and-swap, signature verification, and provider
    read-back belong to the governed delivery CLI that performs the external
    mutation.
14. GitHub's current spammy/unusable state remains a user-provided operating
    constraint. This implementation is completed and committed locally; it
    opens no issue or PR and invokes no GitHub Actions. [U1]

## Decision Model

The aggregate decision uses the following precedence:

| Rule result | Operation effect | Rule outcome | Aggregate consequence |
| --- | --- | --- | --- |
| Completed `block` | Any | Block | Blocks regardless of timeout warnings |
| Timeout, `closed` | Any | Block | Names the timed-out rule and safe recovery |
| Timeout, `warn` | Any | Warn | Allows unless another rule blocks |
| Timeout, `effect_gated` | `local_reversible` | Warn | Allows and records degraded admission |
| Timeout, `effect_gated` | Any other class | Block | No blind bypass |
| Crash or malformed result | Any | Existing `failure_posture` | Remains separate from timeout handling |
| Completed `allow`, `warn`, `context`, or `transform` | Any | Existing behavior | Aggregates normally |

The dispatcher may retain a hard whole-process deadline below the provider's
60-second timeout for resource containment. Exhausting that outer deadline must
explicitly disposition every rule that did not finish through its
`timeout_posture`; it must not return one anonymous fatal child-budget error.

## Operation Effect Contract

Add an in-process operation-effect classifier owned by `agent-hook`. It uses
the normalized provider payload, exact trusted executable resolution, resolved
working repository, and statically resolvable arguments. It never invokes a
child process or contacts a remote.

The classifier returns exactly one value:

- `read_only`: a proven local inspection with no write or external effect;
- `local_reversible`: a bounded mutation within one canonical local checkout
  that can be recovered from Git or an atomic local receipt;
- `local_destructive`: deletion, reset, cleanup, branch/ref destruction, or
  another local mutation whose recovery cannot be assumed;
- `external_mutation`: push, provider mutation, deployment, release, message,
  or other network-visible state change;
- `sensitive_configuration`: secrets, MCP configuration, agent memory,
  credentials, hook configuration, or runtime control-plane state;
- `unknown`: dynamic shell shape, unresolved target, untrusted executable,
  cross-repository effect, or any shape not proven to be narrower.

Only `local_reversible` is eligible for `effect_gated` degraded admission.
`read_only` should normally bypass mutation rules before this point and does
not need a degraded mutation receipt.

### Local-reversible admission requirements

All of the following must be true:

1. The tool or executable is supported by an exact in-process classifier.
2. Every target resolves within one canonical local checkout.
3. The invocation has no provider, remote, network, deploy, release, or
   notification effect.
4. The invocation has no raw destructive, force, reset, cleanup, or unresolved
   redirection shape.
5. The invocation does not target sensitive configuration or protected memory
   paths.
6. No completed rule has proved a checkout conflict, unowned dirty state,
   forbidden direct Git operation, or another policy violation.
7. A generic `semantic-commit commit`, `fixup`, or `squash` invocation is
   eligible only when local repository evidence proves it is on an allowed
   non-default branch.
8. The future `semantic-commit local-default` invocation is eligible only when
   its exact local-only command shape, expected branch, expected head, and
   receipt destination satisfy the separate local-default contract. [F9]

The classifier fails closed to `unknown`. Agent reasoning alone cannot relabel
an unknown effect as local and reversible.

## Timeout Posture Matrix

Runtime-kit applies the following initial posture to the Codex rules and the
equivalent Claude rules. Typed rules retain their existing stronger semantics
where noted.

| Handler or capability | Timeout posture | Rationale |
| --- | --- | --- |
| `pre-edit-intent-gate` | `effect_gated` | Docs capability availability must not stop a proven local-reversible task |
| `checkout-lease-guard` | `closed` | Writer ownership and dirty-checkout integrity are mandatory |
| `block-direct-git-commit` | `closed` | Direct Git commit is a static policy boundary; migrate it in-process later |
| `block-unsafe-default-delivery` | `effect_gated` | Local governed authoring may continue; external or unresolved delivery may not |
| `block-direct-git-worktree` | `closed` | Raw worktree mutation can strand or overlap checkouts |
| `semantic-commit-body-gate` | `effect_gated` | A local governed commit may continue with a reported message-gate outage |
| `block-direct-python` | `warn` | Interpreter convention is not a state-integrity boundary |
| `mcp-secret-scan` | `closed` | Secret exposure is sensitive configuration |
| `block-project-memory-write` | `closed` | Project memory is an explicit privacy boundary |
| `memory-write-principle-reminder` | `warn` | This rule is advisory by design |
| `portable-paths-scan` | `warn` | Portability feedback must not strand the local task |
| `block-direct-pr-create` | `closed` | Provider mutation requires a governed external path |
| `forge-label-reminder` | `warn` | Label guidance is advisory |
| `finish-line-record` | `effect_gated` | Local work may continue, but missing validation evidence must be reported |
| `agent-scope-lock-guard` | `closed` | Managed worker path ownership is mandatory when selected |
| `session-coordination` in `advisory` mode | `warn` | Preserve the existing advisory availability contract |
| `session-coordination` in `enforce` mode | `closed` | Explicit claim and operation proof are mandatory |
| Transaction and recovery capabilities | `closed` | Ambiguous transaction state cannot be admitted |

This matrix is mirrored in `manifests/hook-rules.yaml` so policy source,
inventory, rendered products, and contract tests cannot drift.

## Dispatcher Implementation Contract

### Model and policy schema

In `sympoies/nils-cli/crates/agent-hook`:

1. Add `TimeoutPosture::{Closed, Warn, EffectGated}` with `snake_case` policy
   serialization.
2. Add `timeout_posture` to `PolicyRule` with a default of `Closed`.
3. Validate that `effect_gated` is used only by executable or typed
   capabilities whose selected event has an operation-effect projection.
4. Keep `failure_posture` unchanged for spawn failure, non-timeout I/O failure,
   malformed output, and other capability errors.
5. Replace the `error.code.starts_with("dispatch-")` early return for child
   deadlines with a rule-scoped timeout outcome.
6. Reserve `dispatch-*` fatal errors for failures where the dispatcher cannot
   normalize input, load trusted policy, construct any safe decision, or render
   provider output.

### Execution isolation

1. Track child deadline and completion per selected rule.
2. Preserve completed rule outcomes when another rule times out.
3. Continue evaluating later mandatory rules after an earlier timeout.
4. If the hard outer deadline prevents a child from starting, synthesize a
   timeout outcome for that rule and every remaining unstarted rule rather than
   omitting them.
5. Aggregate results in declared policy priority order even if independent
   executable work is scheduled or collected out of order.
6. Keep transform conflict detection, reason limits, output limits, handler
   trust validation, process-group cleanup, and coordination transaction
   ordering unchanged.
7. A timed-out child and all of its descendants must be terminated and its
   stdout/stderr discarded except for bounded diagnostic metadata.

The exact scheduling implementation may use independent sequential budgets or
bounded concurrency. Observable ordering, isolation, cancellation, and posture
behavior above are mandatory and fully testable.

### Rule-scoped reason codes

Use stable reason codes:

- `<rule-id>:capability-timeout-warn`
- `<rule-id>:capability-timeout-effect-gated`
- `<rule-id>:capability-timeout-closed`
- `<rule-id>:capability-timeout-effect-unknown`

An allowed degraded result uses `DecisionAction::Warn` and includes concise
provider context:

```text
agent-hook degraded admission: <rule-id> timed out while evaluating a
local-reversible operation. The operation was allowed. Continue the task and
report incident <incident-id> in the final response.
```

Do not include raw commands, paths, prompts, handler output, environment
values, credentials, or provider payload text.

## Degraded Incident Contract

Create one private record for each rule timeout at:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/agent-hook/degraded/<incident-digest>.json
```

Use directory mode `0700`, file mode `0600`, no symlinks, atomic no-clobber
creation, and bounded retention. The schema is
`agent-hook.degraded-incident.v1`:

```json
{
  "schema_version": "agent-hook.degraded-incident.v1",
  "incident_id": "incident:sha256:<digest>",
  "recorded_at": "<RFC3339>",
  "product": "codex",
  "event": "PreToolUse",
  "request_id": "request:<digest>",
  "correlation_digest": "sha256:<digest>",
  "rule_id": "runtime.codex.pre-tool-use.bash.block-unsafe-default-delivery",
  "capability": "runtime-kit.handler.v1",
  "handler_id": "block-unsafe-default-delivery",
  "error_code": "capability-timeout",
  "deadline_ms": 2000,
  "elapsed_ms": 2000,
  "effect_class": "local_reversible",
  "disposition": "allow_with_warning",
  "policy_digest": "sha256:<digest>",
  "config_digest": "sha256:<digest>",
  "completion": "pending"
}
```

The correlation digest is derived from validated product/session/tool-use
identity without storing raw provider identifiers. `PostToolUse` changes
`completion` to `succeeded`; `PostToolUseFailure` changes it to `failed`.
Missing terminal correlation remains `pending` and does not change the original
admission.

The record must not contain command text, command output, repository paths,
filenames, prompt or transcript text, environment values, capability bearer
material, credentials, or secrets.

### Aggregation and continuous improvement

Maintain a bounded summary keyed by:

```text
sha256(policy_digest + rule_id + error_code + effect_class + product + platform)
```

The summary stores first seen, last seen, count, most recent incident ID, and
the latest completion status. A repeated timeout updates the same summary; it
does not create a provider issue or a new repository document automatically.

At task closeout:

- the provider context reminds the agent that reporting is required;
- the agent names the affected rule, whether the task completed, and the
  incident ID in its final response;
- an unresolved or recurring workflow defect is routed through the existing
  Heuristic System after the task, not instead of completing eligible work;
- no transcript, terminal log, or prompt content is inspected to verify the
  report.

## Default-Delivery Hook Refactor

`core/hooks/shared/block-unsafe-default-delivery.py` must become a local-only
pre-tool guard.

1. Remove `git ls-remote` and every live network dependency from the hook.
2. Do not replace the probe with another network client, provider CLI, DNS
   check, or connectivity test.
3. Resolve cached default-branch evidence from local refs and configuration.
4. Block a generic `semantic-commit commit`, `fixup`, or `squash` immediately
   when local evidence proves the checked-out branch is the protected default.
5. Admit the future `semantic-commit local-default` shape only through the
   explicit contract in the related local-default handoff. [F9]
6. For raw `git push`, allow only a locally provable non-default exact refspec
   or `--dry-run`. Block default, implicit, wildcard, delete, all, mirror,
   matching, force, and locally ambiguous external shapes with guidance to use
   the governed `forge-cli` route.
7. Treat absence or staleness of cached remote truth as ambiguity for raw
   external delivery, not as a reason to contact the remote inside PreTool.
8. Keep `forge-cli repo push-default` available because the governed CLI owns
   live remote base, signature, compare-and-swap, and read-back verification.
9. Ensure a locally classified `semantic-commit` path completes well below its
   handler deadline without depending on provider availability.

This refactor fixes the observed timeout at its source while the dispatcher
change prevents the same class of availability failure from becoming an
anonymous task denial elsewhere.

## Runtime-Kit Policy And Documentation Changes

Update the following owners together:

- `core/policies/agent-hook/runtime-kit-v1.toml`: add explicit timeout posture
  to every executable rule for Codex and Claude.
- `manifests/hook-rules.yaml`: mirror timeout posture and its behavior owner.
- `core/policies/agent-hook/README.md`: document degraded admission, timeout
  isolation, no-network PreTool behavior, and incident privacy.
- `core/policies/evidence-control-plane.md`: replace the blanket statement that
  every timeout blocks supported-host mutation with the effect-gated contract.
- `core/policies/session-coordination.md`: retain its existing advisory
  availability semantics and reference the shared incident behavior where
  applicable.
- `core/policies/git-delivery.md` and `core/hooks/README.md`: state that live
  remote truth belongs to governed delivery CLIs, not PreTool guards.
- `core/policies/heuristic-system/error-inbox/managed-worktree-lockout-pushguard-ssh/ENTRY.md`:
  mark the slow-probe portion resolved after live acceptance passes; preserve
  unrelated unresolved findings.
- Codex and Claude rendered/golden policy surfaces and hook manifests.

Do not add a user-facing skill for degraded admission. It is dispatcher policy,
not an outcome the user must invoke.

## Nils-CLI Implementation Boundaries

The `sympoies/nils-cli` implementation owns:

- policy deserialization and validation for `timeout_posture`;
- in-process operation-effect classification;
- rule-scoped deadline isolation and aggregation;
- provider rendering of degraded warnings;
- private incident creation, completion correlation, aggregation, retention,
  and doctor diagnostics;
- process-group termination and output bounds;
- unit, contract, privacy, and performance tests;
- CLI/spec documentation for `agent-hook`.

Runtime-kit does not reimplement the dispatcher or incident store. It consumes
the source-built CLI during coupled validation and advances the released pin
only after a later nils-cli release is available.

## Scope

- Introduce rule-scoped timeout posture and degraded admission.
- Add trusted local operation-effect classification.
- Preserve completed rule results across capability timeouts.
- Record redacted timeout incidents and terminal tool outcomes.
- Require user-visible final reporting by agent policy and provider context.
- Remove live remote probing from the default-delivery PreTool hook.
- Update runtime-kit policy, manifests, docs, fixtures, and tests.
- Validate Codex and Claude parity against a source-built nils-cli.
- Commit completed changes locally while GitHub provider workflows are
  unavailable.

## Non-Scope

- Unconditional fail-open behavior for all hook failures.
- Allowing external, destructive, secret-sensitive, or unknown operations after
  a timeout.
- Raw shell bypasses, hook disabling, or user-config policy downgrades.
- Weakening a completed blocking rule or an enforce-mode transaction proof.
- Treating timeout warnings as permission for work outside the user's request.
- Reading transcripts, terminal logs, prompts, or command contents into
  incident records.
- Automatically opening provider issues or PRs from timeout incidents.
- Releasing nils-cli, updating Homebrew, advancing the runtime pin, deploying
  live runtime surfaces, or pushing local commits during the provider outage.
- Implementing the separate `semantic-commit local-default` and receipt
  adoption contract unless the subsequent implementation explicitly combines
  both handoffs.

## Requirements

1. A timed-out eligible local-reversible rule produces an allow-with-warning
   decision, not `agent-hook:dispatch-deadline-exceeded`.
2. A timed-out closed rule produces a rule-scoped block naming that rule.
3. A timed-out effect-gated external, destructive, sensitive, or unknown
   operation blocks.
4. A completed block always dominates degraded warnings.
5. Later mandatory rules still run or receive explicit timeout dispositions
   after an earlier capability timeout.
6. Runtime-kit assigns an explicit timeout posture to every executable rule in
   Codex and Claude policy.
7. The operation-effect classifier is in-process, deterministic, local-only,
   and fail-closed to `unknown`.
8. No PreTool default-delivery path executes `git ls-remote` or another network
   probe.
9. Degraded admission creates one privacy-safe incident record and injects one
   concise provider warning.
10. PostTool success or failure updates the matching incident without raw
    provider identifiers.
11. The agent final response reports a degraded incident after completing the
    task; the hook does not inspect response or transcript text.
12. Repeated incidents aggregate locally by stable fingerprint.
13. Existing recovery, override, signature, checkout lease, transaction,
    process cleanup, and provider delivery invariants remain intact.
14. Missing `timeout_posture` remains closed for older policy bundles.
15. Source-built coupled validation passes before either repository is locally
    committed.

## Acceptance Criteria

1. A fixture with one sleeping `warn` handler and a later blocking handler
   returns the later block, not a dispatcher error.
2. A fixture with one sleeping `effect_gated` handler and a
   `local_reversible` operation returns allow-with-warning and an incident ID.
3. The same sleeping handler returns block for `external_mutation`,
   `local_destructive`, `sensitive_configuration`, and `unknown`.
4. A sleeping `closed` handler returns a rule-scoped timeout block.
5. A completed blocking rule cannot be overridden by any timeout warning.
6. An unstarted rule at outer-deadline exhaustion receives its configured
   timeout disposition and appears in the normalized reasons.
7. Timed-out process descendants are terminated and cannot retain output pipes
   or state locks.
8. Incident permissions, no-symlink handling, atomic writes, size bounds, and
   retention limits pass security tests.
9. Privacy canaries prove incident and trace records contain no command, path,
   prompt, transcript, environment, credential, or handler-output content.
10. PostTool success and failure correlate to the correct incident; mismatched
    or replayed correlation cannot update another incident.
11. A remote-present feature-branch `semantic-commit` is admitted with the
    remote unavailable and no network call from PreTool.
12. A generic `semantic-commit` on a locally proven default branch is blocked
    promptly with the governed-route message.
13. The future exact `semantic-commit local-default` shape remains available
    for its separate policy integration.
14. Raw default, force, implicit, wildcard, delete, all, mirror, matching, and
    ambiguous pushes remain blocked without live remote lookup.
15. Exact locally provable feature-branch push refspecs and push dry-runs retain
    their documented behavior.
16. `forge-cli repo push-default` remains available and retains live
    compare-and-swap and read-back authority.
17. Codex and Claude policy inventory, rendering, setup, doctor, and hook
    contract tests pass with identical timeout semantics.
18. The original `semantic-commit` reproduction no longer returns
    `dispatch-deadline-exceeded`; it either receives the intended completed
    policy decision or an allowed degraded warning according to its exact
    command shape.

## Test-First Contract

This is a testable cross-repository behavior change. Before production edits:

1. Initialize `test-first-evidence` in each edited repository.
2. Record the contract delta: child timeout becomes rule-scoped degraded or
   closed behavior; completed policy blocks and privacy invariants are retained.
3. Capture a meaningful red in `sympoies/nils-cli` showing a timed-out eligible
   handler currently returns `dispatch-deadline-exceeded` and skips a later
   rule.
4. Capture a meaningful red in `agent-runtime-kit` showing the default-delivery
   hook invokes a live remote probe or exceeds the dispatcher contract for the
   semantic-commit fixture.
5. Implement production changes only after both pre-edit checks pass.

Test impact must cover:

- `crates/agent-hook/tests/performance_contract.rs`;
- `crates/agent-hook/tests/contracts.rs` and API/contract freeze coverage;
- incident privacy, correlation, replay, process cleanup, and doctor tests;
- `tests/hooks/test_shared_hooks.py` default-delivery and timeout cases;
- `tests/agent-hook/test_policy_contract.py` and policy fixtures;
- Codex and Claude rendered/golden acceptance;
- source-built coupled runtime validation.

## Validation Plan

### Nils-cli focused validation

Run the focused `agent-hook` crate tests, including contract, API, performance,
privacy, incident, and recovery coverage. Use the repository's declared Rust
format, lint, and test commands rather than inventing replacements.

### Runtime-kit focused validation

```bash
bash tests/hooks/run.sh
bash tests/agent-hook/run.sh
```

Run targeted Python hook cases before the broader scripts when iterating.

### Coupled source-built validation

Use `scripts/dev/with-nils-version.sh` with the exact local nils-cli build to
validate policy parsing, dispatcher decisions, rendering, setup, doctor, and
Codex/Claude parity before a released pin exists.

Do not run the full runtime-kit gate against an unreleased binary in a way that
claims the pinned release already contains the change. Record source-built and
released-pin evidence separately.

### Documentation and repository validation

```bash
agent-docs --docs-home "$PWD" --project-path "$PWD" \
  audit --target project --strict --format json
git diff --check
```

After the full implementation exists, record and verify the appropriate
`docs-impact` disposition and run the declared project validation scopes.

### Live acceptance

Installed-home sync and live disposable-session acceptance require a separate
explicit deployment action. When authorized later, prove:

- an eligible local-reversible timeout allows the tool call and reports an
  incident;
- a closed or external timeout still blocks;
- no default-delivery PreTool path contacts a remote;
- `agent-hook doctor` reports converged policy and incident-store health.

Live acceptance is not required for the provider-outage local implementation
commit and must not be represented as completed before installation occurs.

## Risks And Guardrails

- **Timeout becomes an accidental policy bypass**: only a trusted
  `local_reversible` classification is admitted; completed blocks dominate.
- **A slow early handler suppresses a critical later guard**: rule isolation
  and explicit disposition of unstarted rules are acceptance requirements.
- **Effect classifier drifts from shell reality**: unsupported or dynamic
  shapes classify as `unknown`; no agent override relabels them.
- **Incident records become a privacy side channel**: store only bounded
  identifiers, digests, enums, timings, and completion state.
- **Warning spam obscures real failures**: aggregate stable fingerprints and
  report one concise incident summary per task.
- **Removing live probes weakens raw push safety**: ambiguous raw external
  delivery remains blocked and routes to the governed CLI, which owns live
  verification.
- **Backward compatibility silently opens old policy**: missing
  `timeout_posture` defaults to `closed`.
- **Local implementation is mistaken for deployed behavior**: source-built,
  released-pin, installed-home, and provider-delivered states remain distinct.

## Implementation Completion Boundary

The local implementation is complete when:

- nils-cli and runtime-kit source changes satisfy the requirements and
  acceptance criteria;
- both repositories contain verified test-first and final validation evidence;
- source-built coupled validation passes;
- durable policy and CLI docs describe the resulting behavior;
- signed local commits exist on the user-authorized local branches;
- no provider issue, PR, push, workflow, release, deployment, or pin promotion
  is claimed.

Provider release, runtime pin advancement, installed-home sync, and live
acceptance remain later, separately authorized actions.

## Read-First References

- [F1] `sympoies/nils-cli/crates/agent-hook/src/evaluator.rs` — execution
  budgets, fatal `dispatch-*` propagation, failure posture, and child cleanup.
- [F2] `core/policies/agent-hook/runtime-kit-v1.toml` and
  `manifests/hook-rules.yaml` — ordered Codex/Claude executable rules.
- [F3] `core/hooks/shared/block-unsafe-default-delivery.py` — four-second
  `GitProbe`, live default-branch resolution, and semantic-commit classification.
- [F4] Runtime-kit commit `372d3f0` — cached fallback for timed-out exact
  feature-branch push refspecs.
- [F5]
  `core/policies/heuristic-system/error-inbox/managed-worktree-lockout-pushguard-ssh/ENTRY.md`
  — prior slow-SSH evidence and impact.
- [F6] `core/policies/evidence-control-plane.md` — current blanket supported-host
  timeout blocking statement.
- [F7] `core/policies/session-coordination.md` — advisory degraded-availability
  precedent.
- [F8] `sympoies/nils-cli/crates/agent-hook/src/setup.rs` and its setup contract
  tests — generated provider ingress and the 60-second dispatcher process
  timeout boundary.
- [F9] `docs/discussions/2026-07-23-local-default-commit-mode.md` — explicit
  local-default authoring and receipt contract.
- [A1] 2026-07-23 local per-handler reproduction: default-delivery guard about
  3.60 seconds; other selected handlers about 0.05 to 0.13 seconds.
- [A2] 2026-07-23 local source/deployment/live digest comparison and
  `agent-hook doctor --all --format json` convergence result.
- [U1] Maintainer requirement in this discussion: timeout should warn and allow
  autonomous completion when no major risk is present, followed by explicit
  anomaly reporting and continuous-improvement retention; GitHub workflows are
  currently unavailable because the provider has classified the account or
  repository as spammy.

## Recommended Next Artifact

No L2 plan bundle is required. The next artifact is the implementation diff in
the two owning repositories, with this document read first and linked from the
local validation evidence. If the work later expands beyond this bounded
coupled fix, re-triage before creating an issue-backed or dispatch plan.
