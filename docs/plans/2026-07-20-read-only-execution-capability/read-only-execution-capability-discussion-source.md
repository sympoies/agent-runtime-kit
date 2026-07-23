# Read-only execution capability implementation handoff

## Document control

- Status: approved and implementation-ready
- Date: 2026-07-20
- Owner tracker: <https://github.com/graysurf/agent-runtime-kit/issues/670>
- Implementation repositories: `sympoies/nils-cli` and
  `graysurf/agent-runtime-kit`
- Work tier: L2, one plan-tracking issue
- Decision owner: maintainer
- Open architecture questions: none

## Requested outcome

Replace runtime-kit's string-based shell read-only classifier with a real,
versioned `execution.read-only.v1` capability. Preserve fail-closed
`project-dev`, target-repository, finish-line, secret, memory, worktree,
commit, provider, and executable-trust gates. Make ordinary inspection usable
without repeatedly expanding an argv allowlist, and keep delivery review
bounded so implementation PRs can converge and merge. [U1] [A1]

## Source register

- [U1] The maintainer asked to graduate #670 into a complete L2 plan that a
  later implementation session can execute directly, without another design
  round.
- [A1] Issue #670 contains the original problem statement and the accepted
  design checkpoint:
  <https://github.com/graysurf/agent-runtime-kit/issues/670>.
- [A2] Issue #686 owns the single `agent-hook` runtime-kit ingress. Its current
  dashboard is in progress at Task 2.3, next Task 2.4, with no blocker:
  <https://github.com/graysurf/agent-runtime-kit/issues/686>.
- [A3] Issue #673 delivered cross-run native-review idempotency, outdated
  thread disposition, and the large-PR splitting rule, and is closed:
  <https://github.com/graysurf/agent-runtime-kit/issues/673>.
- [F1] The legacy decision path is in
  `core/hooks/shared/pre-edit-intent-gate.py`, including
  `READ_ONLY_EXECUTABLES`, `READ_ONLY_GIT_SUBCOMMANDS`,
  `GH_READ_ONLY_SUBCOMMANDS`, and `simple_shell_words`.
- [F2] `core/policies/files-hooks-validation.md` defines the current
  tri-state `read-only | mutation | unknown` classifier, the exact narrow
  read-only lane, and fail-closed handling for unknown shell effects.
- [F3] `core/policies/work-tier-levels.md` requires reviewable PR slices when
  one large review surface cannot converge.
- [W1] Current Codex hook documentation does not provide authenticated
  filesystem write-denial attestation bound to an exact tool request:
  <https://learn.chatgpt.com/docs/hooks>.
- [W2] Current Claude Code hook documentation likewise exposes tool input and
  permission context, not trusted sandbox attestation for the exact request:
  <https://code.claude.com/docs/en/hooks>.
- [W3] The nils-cli `agent-hook` v1 spec owns typed capability evaluation and
  closed capability dispatch:
  <https://github.com/sympoies/nils-cli/blob/main/crates/agent-hook/docs/specs/agent-hook-v1.md>.
- [W4] Current `agent-run exec` launches commands without the required
  read-only sandbox contract:
  <https://github.com/sympoies/nils-cli/blob/main/crates/agent-workflow-primitives/src/agent_run.rs>.

## Frozen decisions

1. `agent-hook` owns a versioned `execution.read-only.v1` capability schema,
   normalization, verification, decision trace, and receipts.
2. There are exactly two v1 producer families:
   - `os_enforced`: `agent-run inspect --cwd <path> -- <argv...>` runs the
     complete child process tree in a network-denied, durable-filesystem
     read-only sandbox with only private ephemeral state writable.
   - `tool_contract`: same-release nils-cli commands export typed
     `OperationEffectDescriptor` values from their parsed command enums for
     exact query-only operations that legitimately need provider or managed
     state reads.
3. `host_attested` is reserved for a future authenticated product signal bound
   to an exact request. Current permission mode, configured sandbox mode,
   environment variables, raw command text, comments, and user-provided JSON
   are not capability evidence.
4. Local inspection tools, pipelines, and compound reads use `agent-run
   inspect`. Managed `agent-docs` and `forge-cli` queries use tool-owned
   descriptors. General-purpose `gh`, `glab`, `curl`, plugins, passthroughs,
   and arbitrary scripts cannot self-declare read-only behavior.
5. Missing, malformed, stale, mismatched, unsupported, or forged evidence is
   `unknown`. Known mutation and unknown both require prepared `project-dev`
   for the exact target repository/worktree.
6. Linux and macOS backends are enabled independently only after the common
   adversarial conformance contract passes. An unsupported backend fails
   closed; it never falls back to ordinary `agent-run exec` while claiming
   read-only behavior.
7. Runtime-kit consumes the capability only through #686's single ingress.
   #686 is a landing dependency for runtime-kit integration, not for nils-cli
   schema, descriptor, or sandbox work. #670 remains a separate review and
   delivery stream.
8. Final cutover removes the four legacy classifier surfaces and their
   production decision path. Shadow comparison is temporary migration
   evidence, not a permanent second classifier.

## Capability contract

An admitted decision binds at least:

| Field | Required invariant |
| --- | --- |
| `producer` | Trusted producer kind, exact binary identity, release version, and package digest |
| `assurance` | `os_enforced` or `tool_contract` in v1 |
| `binding` | Product, session, and request/tool-use identity when available |
| `execution` | Effective cwd, target repository/worktree, and exact argv digest |
| `filesystem` | Every durable root read-only and the complete private ephemeral writable set |
| `network` | Denied for `os_enforced`; exact query-only effect for `tool_contract` |
| `freshness` | Request-local binding; nonce and expiry where evidence is portable |

The verifier returns no capability when any required identity, target, digest,
assurance, or freshness binding is absent or mismatched.

## Producer A: enforced local inspection

`agent-run inspect` must enforce the following for the complete process tree:

- the checkout, linked Git administration paths, user home, agent state, and
  all other durable filesystem roots are read-only;
- only newly created private `HOME`, `XDG_*`, and temporary scratch roots are
  writable, and they are removed after execution;
- network access is denied and inherited credentials are unavailable;
- inherited writable file descriptors, mounts, ptrace, nested namespaces,
  subprocesses, and background survivors cannot escape containment;
- process count, wall time, and output are bounded; and
- cleanup and backend verification fail closed.

The common conformance suite must attempt durable writes, linked-Git writes,
network access, inherited-fd writes, mount/namespace/ptrace escape, background
survival, scratch persistence, and resource exhaustion on every enabled
platform.

## Producer B: managed operation contracts

Each participating nils-cli command owns a typed descriptor beside its parsed
command enum. The descriptor binds the exact executable and release, parsed
variant and arguments, provider effect, and allowed managed-state reads.

The initial descriptor set is intentionally narrow:

- `agent-docs`: preflight, explain, list, audit, integration resolve, session
  status, and session verify; preparation/activation and other state writers
  remain mutations.
- `forge-cli`: typed repository, issue, PR/MR, review, thread, task, check, and
  label query operations that do not create, edit, submit, resolve, merge, or
  delete provider state. The owning typed enum is authoritative; this document
  does not become a second argv allowlist.

Unknown flags, output paths, state-changing cache modes, passthroughs, and
unclassified command variants produce no read-only descriptor.

## Acceptance boundaries

Positive cases:

- compound local reads and pipelines succeed through `agent-run inspect`
  without `project-dev`;
- exact managed queries succeed through tool-owned descriptors; and
- equivalent Codex and Claude requests normalize to the same policy decision.

Adversarial cases:

- reject PATH shadows, out-of-release symlinks, owner/mode drift, stale
  versions, forged descriptors, environment overrides, cwd/argv mismatch,
  expired evidence, and copied receipts;
- reject durable writes, network use by the inspection runner, process-tree
  escape, background survivors, and scratch persistence;
- reject general provider clients and unknown managed flags; and
- prove a command targeting another repository cannot inherit activation or
  evidence from the hook-visible checkout.

Regression cases:

- direct edits, shell writes, formatters, generators, installs, and repo-owned
  scripts remain blocked until exact preparation;
- finish-line validation or waiver enforcement is unchanged; and
- secret, memory, worktree, commit, provider, executable-trust, session,
  product, repository, state-home, quoting, and shell-control protections stay
  equal or stronger.

## Review stopping rule

Each implementation PR gets one pre-merge specialist gate scoped to that PR's
owner boundary. Testing and maintainability are always included; security is
required for the capability, sandbox, and cutover slices. A violated invariant,
unmet acceptance criterion, unimplementable contract, or P0/P1 security defect
blocks. P2 hardening and implementation preferences become follow-ups and do
not restart broad review.

A blocking repair receives one affected-only re-review by the relevant lens,
bound to the new head and finding fingerprint. If that targeted re-review still
fails, the tracker records one concrete blocker and stops. An unchanged head or
equivalent finding must use the delivered #673 idempotency path and must not
create another review or thread.

## Approval and deployment boundaries

The maintainer has approved the design and creation of this L2 tracker. No
architecture decision remains. Implementing code, opening reviewable PRs, and
updating the tracker are internal L2 phases once implementation is requested.

A nils-cli public release/publish and any apply to live Codex/Claude runtime
homes remain explicit external-state boundaries. The plan may prepare and
validate those steps, but the executing session must obtain the then-current
maintainer authorization required by their owning release/deployment workflow.

## Out of scope

- Reopening #686 architecture or folding #670 into #686's current PRs.
- Growing or permanently retaining a second heuristic allowlist.
- Trusting current product permission/sandbox configuration as attestation.
- Granting arbitrary network access to local inspection commands.
- Weakening pre-edit, finish-line, secret, memory, Git, provider, or delivery
  review gates.
- Live runtime activation without fresh authorization.

## Execution

- Plan: `docs/plans/2026-07-20-read-only-execution-capability/read-only-execution-capability-plan.md`
- State: `docs/plans/2026-07-20-read-only-execution-capability/read-only-execution-capability-execution-state.md`
