# Cross-Repository Project-Dev Gate Implementation Handoff

- Status: implemented and retained for delivery handoff
- Date: 2026-07-22
- Source: Main Agent reproduction and converged implementation contract
Intended next step: Main Agent review, integration, deployment acceptance, and
the separately owned bounded nils-cli diagnostic enrichment.

## Purpose

Make cross-repository implementation a supported project-dev workflow without
turning missing or stale workflow metadata into a default mutation freeze. The
project-dev gate becomes advisory by default, remains explicitly enforceable,
and uses one provenance-aware command context across mutation-sensitive guards.

## Reproduced Problem

The Main Agent ran an exact `agent-docs session prepare` for a managed worktree
while the hook process remained rooted in the primary checkout. The command's
literal absolute `--project-path` named the worktree, but the pre-edit gate first
selected the hook-visible checkout and rebuilt recovery for that checkout. It
rejected the target command as `agent-docs-bootstrap-shape-mismatch`; no target
file changed. [U1]

The current gate computes shell repositories from `effective_workdir(payload)`
before parsing a trusted preparation command. Its bootstrap parser then compares
the command against an expected tuple constructed from that already-selected
repository. [F1] The shared workdir helper falls back to process cwd without
retaining where the value came from or whether it was attested. [F2]

## Evidence And Facts

- `agent-docs` activation records are already separated by session hash,
  product, and project hash; the required change does not need a storage or
  schema migration. [F4]
- Direct edits already discover every canonical repository from explicit edit
  paths and verify them independently. The current failure collection drops the
  repository identity and retains only verification codes. [F1]
- Shell work is currently repository-scoped through `effective_workdir`, which
  is also consumed by checkout lease, delivery, scope-lock, Python, and session
  coordination guards. [F2] [F3]
- Transcript lookup is tail-bounded to 4 MiB and matches Codex call ids. That
  cap remains part of the contract. [F2]
- Exact trusted preparation is already consumed inside the hook through a
  bounded subprocess and returns `prepared` plus `retry-original`. [F1]
- Checkout ownership, coordination enforcement, validation/finish-line,
  delivery/signing, provider, secrets, OS, and user-authority controls are
  separate gates. Project-dev mode must not weaken or reconfigure them. [F3]

## Decisions

1. `AGENT_RUNTIME_PROJECT_DEV_MODE` selects `advisory`, `enforce`, or `off`.
   Missing means `advisory`. Invalid values deterministically degrade to
   advisory and emit a stable warning; they never freeze all mutations.
2. `off` bypasses only the project-dev workflow gate. It does not change any
   other hook, ownership rule, delivery rule, or validation obligation.
3. Advisory mode verifies project-dev when a canonical target and trusted
   capability are available. For an unprepared target it attempts one bounded,
   exact target preparation. A successful preparation allows the original tool
   call and emits a concise advisory. Failure, unavailable capability, stale
   activation, or missing attestation also allows the original call with a
   deterministic warning and exact recovery or target-rooted fallback.
4. Enforce mode remains fail-closed. An exact trusted `session prepare` is
   parsed by its literal absolute canonical `--project-path` before ordinary
   shell target selection. The executable, docs home, session, product, state
   home, intent list, optional recognized phase, and final `--format json` must
   match exactly. Reordered, duplicated, extra, relative, dynamic, wrapped,
   shadowed, or shell-controlled forms do not execute.
5. Direct edits retain sorted `(canonical repository, failure code)` pairs.
   Each target receives independent verification and recovery. Preparing B
   never substitutes for or mutates A's activation. Multi-target edits block
   only in enforce mode and only until every target verifies.
6. `hook_common.py` exposes a provenance-aware command context with canonical
   path, source, attestation, and an optional stable diagnostic.
   `effective_workdir()` remains a compatibility wrapper over the context path.
7. V1 admits cross-repository shell work only through host-attested workdir
   metadata: Codex inline workdir, a matching bounded transcript call, the
   provider session cwd shape, or a bounded private ready `agent-session` record
   whose id, agent, runtime incarnation, owner/mode, and cwd match the hook
   process. This managed-session route was added after live Claude acceptance
   showed that Bash envelopes can omit cwd and that the current call may reach
   the hook before it is flushed to the transcript. A transcript miss still
   rejects unauthenticated payload/session cwd metadata; it cannot suppress an
   independent managed-record match for the same physical cwd. Plain process
   cwd remains un-attested and is never silently promoted to a cross-repository
   target.
8. Shell-embedded `agent-run exec --cwd` remains fail-closed in this bounded
   change. Safe admission needs a nils-cli typed command-context result that
   binds the exact same release as `agent-docs`, canonical target, wrapper
   grammar, and child argv before every mutation-sensitive guard runs. Until
   that primitive exists, the diagnostic names the target-rooted worker
   fallback; runtime-kit does not add an unsafe wrapper allowlist. [I1]
9. Manager, collaborator, borrower, claim, and checkout relationships remain
   coordination facts only. They confer no repository mutation authority.
10. Public output contains bounded canonical paths and stable reason codes only.
    It never includes prompt/transcript bodies, command output, tokens,
    capability contents, or session contents.
11. Agent-facing diagnostics state the stable code, what failed, whether the
    original work remains allowed, the exact next action or fallback, and what
    to retry. Runtime-kit consumes structured `error.code` when it exists and
    does not parse failure prose.
12. The companion nils-cli change is a separate bounded lane. It additively
    enriches `agent-docs session` failures with `hint`, `details.retryable`,
    `next_action`, and `recovery` without a schema-version bump. Runtime-kit
    remains compatible with older failure envelopes that provide only
    `error.code` and `error.message`.

## Goals

- Make default cross-repository implementation advisory and recoverable.
- Preserve explicit enforce-mode fail-closed behavior without the current
  preparation/recovery loop.
- Ensure every guard observes the same command target and provenance.
- Preserve direct-edit multi-target verification and isolate target state.
- Keep already-active hot paths free of newly introduced subprocesses.

## Non-Goals

- Changing `agent-docs` record schemas or activation identity.
- Implementing the separately owned nils-cli failure-diagnostic enrichment in
  this runtime-kit worktree.
- Granting authority through orchestration or coordination relationships.
- Weakening checkout leases, work-context enforcement, validation, signing,
  delivery, secrets, provider, OS, or user-consent gates.
- Inferring arbitrary shell destinations or permitting wrapper variants.
- Adding a database, retaining prompt/command output, or scanning whole
  transcripts.
- Shipping the deferred nils-cli typed `agent-run` context primitive.

## Exact File Boundaries

- `core/hooks/shared/hook_common.py`: add command-context provenance and keep
  `effective_workdir()` compatible.
- `core/hooks/shared/pre-edit-intent-gate.py`: add project-dev mode semantics,
  target-first trusted prepare parsing, advisory auto-preparation, target/code
  diagnostics, and enforce recovery.
- `tests/hooks/test_shared_hooks.py`: add mode, provenance, cross-repository,
  multi-target, bootstrap, adversarial, isolation, and latency coverage; retain
  existing strict tests under explicit enforce mode.
- `core/hooks/README.md`: document command context, mode contract, supported
  host-attested route, and deferred typed wrapper route.
- `core/policies/files-hooks-validation.md`: make advisory/enforce/off and
  target-rooted shell guidance authoritative.
- `core/policies/git-delivery.md`: clarify that project-dev mode never weakens
  delivery/signing controls.
- `docs/discussions/2026-07-22-cross-repo-project-dev-gate.md`: this
  implementation-readiness source.

No `AGENT_HOME.md` or rendered mirror change is required unless validation
shows its concise invariant is no longer truthful. Generated targets must be
changed only through repository rendering.

## Test-First Contract

Retained behavior and invariants:

- Read-only commands retain their narrow audited bypass.
- Explicit enforce preserves strict verification and exact consumed bootstrap.
- Direct edits discover canonical repositories from their target paths.
- Existing unrelated guards keep their current decisions.
- Transcript reads stay capped at 4 MiB.

Changed behavior:

- Missing mode changes from implicit fail-closed project-dev enforcement to
  advisory workflow guidance.
- Missing, stale, or unavailable project-dev state no longer blocks solely in
  advisory mode.
- A trusted target-B prepare issued from session/workdir A is parsed and
  consumed for B instead of rebuilt for A.
- Workdir resolution returns provenance and attestation, not only a path.

Added behavior:

- `off` bypasses only project-dev checks.
- Advisory mode automatically prepares safe, attested targets when possible.
- Enforce output preserves and sorts every repository/failure-code pair.
- Missing/mismatched workdir attestation and unsupported cross-repository routes
  produce stable diagnostics.
- Successful advisory auto-preparation names the exact phase-qualified preflight
  command for reading the prepared contract.
- Advisory preparation near misses execute normally and say so; enforce mode
  blocks the same shape and says it was blocked.

Meaningful red must be captured before production edits at the hook integration
boundary. The red suite must prove the default advisory contract, target-B
prepare consumption, provenance classification, and independent multi-target
behavior fail against the current implementation for the expected assertions,
not because of fixture setup or compilation errors.

## Acceptance Criteria

1. Missing and explicit `advisory` mode allow repository work with deterministic
   guidance when activation, capability, or attestation is unavailable.
2. Invalid mode values degrade to advisory with a stable warning.
3. Explicit `enforce` retains fail-closed behavior and exact executable
   recovery without repeating a successfully consumed preparation.
4. `off` bypasses project-dev only; representative checkout/delivery guards
   still make their independent decisions.
5. An exact trusted target-B prepare from workdir A is consumed once, reports
   `[reason: prepared] [action: retry-original]`, and verifies B without
   changing A.
6. A direct A+B edit verifies both targets independently in either activation
   order and reports sorted target-specific failures/recovery.
7. Command context distinguishes Codex inline workdir, matching Codex
   transcript workdir, Claude session cwd, authenticated managed-session cwd,
   payload metadata, and process cwd; missing or mismatched call ids never
   attest an unauthenticated fallback as the target call. A managed record may
   independently attest the same physical cwd and must match the current
   session id, provider, ready state, runtime incarnation, and file owner/mode.
8. Relative, dynamic, duplicate, symlink-alias, reordered, extra-flag, wrapper,
   shell-control, and executable-shadow preparation/cross-repository forms fail
   closed under enforce.
9. Preparation creates no coordination claim or checkout lease and cannot
   bypass any separately registered guard.
10. Same-repository behavior and all existing shared hook tests remain green.
11. Public diagnostics use the stable reasons `project-dev-required`,
    `prepared`/`retry-original`, `project-dev-advisory-unavailable`,
    `workdir-attestation-missing`, `cross-repository-target-unsupported`, and
    `agent-docs-bootstrap-shape-mismatch` where applicable.
12. A deterministic 1,000-invocation context-resolution measurement adds less
    than 10 ms p95-equivalent aggregate regression on the local synthetic
    fixture; already-active verification introduces no additional subprocess.
13. Preparation fixtures keep activation markers in private state outside every
    fixture repository and prove preparation changes neither repository's
    working-tree content.
14. Successful advisory auto-preparation returns an exact phase-qualified
    contract preflight; near-miss diagnostics distinguish ordinary advisory
    execution from enforce-mode blocking without parsing failure prose.

## Validation

- Run the focused new `unittest` methods during red and green cycles.
- Run the complete `tests/hooks/test_shared_hooks.py` owner suite through
  `bash tests/hooks/run.sh`.
- Run `bash tests/hooks/run.sh` twice to catch retained-state/order coupling.
- Run clean-head `bash scripts/ci/all.sh`; the Main Agent owns the later
  integration acceptance rerun.
- Record test-first evidence outside the repository and verify it before the
  semantic commit.

## Rollout

Land runtime-kit source, tests, and policy together. The new environment mode
is backward-compatible at the process boundary: installations that do nothing
receive advisory behavior; operators that require the previous strict workflow
select `AGENT_RUNTIME_PROJECT_DEV_MODE=enforce`; emergency workflow-only bypass
uses `off`. Runtime surface synchronization and deployment acceptance are owned
by the Main Agent after integration. Existing nils-cli storage already isolates
session records by session hash, product, and project hash. The companion
nils-cli lane changes only failure guidance: additive `hint`,
`details.retryable`, `next_action`, and `recovery` fields, no schema bump.
Runtime-kit continues to accept the older code/message-only failure shape.

## Privacy And Latency

Command context retains only canonical path, enumerated source, attestation,
and a stable diagnostic. Advisory output retains neither command/transcript
bodies nor subprocess output. Transcript inspection remains a maximum 4 MiB
tail read. Mode parsing and context provenance are in-process only; an already
active target follows the existing capability/verification subprocess path and
adds no process. Auto-preparation is limited to targets whose verification has
already failed and runs at most once per target per hook invocation. The local
synthetic budget is 10 ms aggregate regression across 1,000 context resolutions.

## Risks And Guardrails

| Risk | Guardrail |
| --- | --- |
| Advisory is mistaken for authority | Every warning says work remains allowed; unrelated locked gates still run. |
| Target A is verified while B is mutated | One shared canonical command context; direct edits keep per-target repository/code pairs. |
| Stale prepare loops forever | Parse literal canonical target first; consume once; return `prepared` + `retry-original`. |
| Wrapper parsing admits a shadow or shell control | Defer `agent-run` route; only host-attested workdir metadata is supported in V1. |
| Auto-prepare changes unrelated state | Exact per-target project path and identity tuple; no claim/lease APIs. |
| Warnings leak session/transcript content | Stable codes and bounded paths only. |
| Default change weakens delivery controls | Project-dev mode is local to its hook; delivery/signing/ownership hooks remain independent. |

## Retention Intent

This user-requested implementation source is a durable decision and delivery
handoff record. Retain it after delivery; do not automatically remove it as
completed coordination material. Update or supersede it explicitly if the
architecture changes.

## Evidence Register

- [U1] Worker prompt: Main Agent's live target-B prepare reproduction, with no
  target edit.
- [F1] `core/hooks/shared/pre-edit-intent-gate.py`: current target selection,
  trusted bootstrap parsing, verification, and recovery behavior.
- [F2] `core/hooks/shared/hook_common.py`: current workdir resolution and 4 MiB
  transcript cap.
- [F3] `core/hooks/README.md` and `core/policies/files-hooks-validation.md`:
  current shared guard boundaries and hook behavior.
- [F4] `sympoies/nils-cli/crates/agent-docs/src/session.rs`: `new_record`,
  `validate_record_context`, and `record_path` bind session records to the
  session digest, product, and canonical-project digest under the private state
  home.
- [I1] Runtime-kit cannot safely attest a shell-embedded cross-repository
  `agent-run` route for every guard without a typed nils-cli context primitive;
  therefore V1 retains the documented target-rooted fallback.
