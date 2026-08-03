# Engineering Work Contract

## Purpose

This is the compact required `project-dev` edit contract. It defines the
engineering outcome an agent must prove while leaving routine planning, tool
selection, and iteration strategy to the agent. Exact hook internals, evidence
schemas, delivery state machines, and recovery commands belong to their owning
runbooks and CLIs.

## Before Editing

- Read the closest repository instructions and only the intent documents
  relevant to the work. Inspect the target plus material callers, loading paths,
  tests, generated surfaces, and local conventions.
- Preserve unrelated and pre-existing work. If a checkout is dirty, ownership
  is unclear, or another session overlaps the same files, remain read-only until
  isolation or explicit ownership is established.
- State a concise contract delta for behavior changes: what stays true, what
  changes or is removed, what is added, and which invariants must remain.
  Refactors with no intended behavior delta say so.

## Proof Strategy

- Treat materially affected tests as part of the change: add or update the
  lowest stable behavioral owner, and merge, refactor, or remove affected cases
  that no longer protect a distinct still-valid risk. Prefer observable
  assertions over implementation shape.
- For testable behavior, normally capture a meaningful regression failure
  before production edits. The failure must come from the intended missing or
  changed behavior, not setup, compilation, environment, fixture, retry, or an
  unrelated failure.
- When meaningful red is impractical, record a concise reason and substitute
  validation. This is expected for docs-only, generated-only, mechanical
  refactors, or behavior with no stable local harness; it is not permission to
  skip an available behavioral test.
- A durable `test-first-evidence` record is conditional. Create and verify one
  only when the repository, delivery gate, high-risk workflow, or user requires
  retained proof. The engineering judgment above applies even when no record is
  warranted; record mechanics live in `evidence-control-plane.md` and CLI help.
- Flaky tests are defects. Quarantine needs an owner, expiry/removal condition,
  and substitute validation.

## Files And Sensitive Output

- Follow project conventions for durable files and generated output. Do not
  create a discussion, plan, decision record, or broad index entry unless asked
  or clearly reusable.
- Put temporary/debug artifacts in a project-owned output path or an
  `agent-out project --topic <topic> --mkdir` directory outside the repository.
  Never commit runtime evidence, receipts, credentials, logs, or caches.
- Inspect provider, container, stack, and environment objects with narrow field
  projections. Treat auth, token, password, key, secret, config, and environment
  fields as sensitive; prefer presence, count, length, or shape checks over
  values. If a secret reaches the transcript, stop using it and route rotation
  through its owner.

## Hooks And Cross-Repository Work

- Hooks enforce mechanical boundaries but do not grant authority or replace
  judgment. Do not bypass a hook because its check seems redundant. A block
  names the owning policy or recovery route; fix the precondition or report the
  blocker.
- Use the tool call's top-level working directory for ordinary mutation and
  cross-repository staging. Stage each repository separately. A repo-scoped
  `semantic-commit --repo` commit is the sole target-aware commit exception and
  must be its command's sole mutation. Do not hide other cross-repository
  mutation behind shell `cd`, raw `git -C`, dynamic paths, or a nested wrapper
  when the host cannot attest the target.
- Advisory preparation or coordination warnings do not deny work. Explicit
  enforcement, checkout ownership, secrets, destructive actions, provider
  mutations, and unknown-effect failures remain fail-closed according to their
  owner.
- When an authorized local operation cannot run in the current environment,
  load `core/policies/execution-capsules.md` from the selected docs home and use
  its private, supervised handoff. Host access is operator-authorized access
  expansion only; it never waives repository rules, hooks, signing, or
  concurrency guards.
- Hook source, timeout/effect classification, setup, sync, and recovery details
  live in `core/hooks/README.md`. Git and provider boundaries live in
  `core/policies/git-delivery.md`.

## Parent Workflow Routing

`agent-docs` preflight and `agent-out` allocation are parent workflow
responsibilities, not user-selected outcomes. Keep both CLIs callable for
diagnostics, explicit cleanup, and workflows that require retained artifacts.

## Validation And Completion

- During iteration, run the smallest focused checks that answer the current
  question. Expand by risk to affected suites, contract consumers, render/
  generated checks, integration, or manual acceptance.
- Before declaring completion, run every command in the active intent's
  declared validation exactly once against the final change. A canonical gate
  may already include focused suites; do not redeclare or rerun them unless the
  final change invalidated their result.
- Report the commands run, outcomes, and material residual gaps. An explicit
  waiver states why a declared command could not run, what substitute evidence
  exists, and whether the result remains incomplete.
- If code changed after a successful gate, the result is stale. Rerun the
  smallest affected checks and the canonical completion gate required by the
  repository.

### Recovery When The Shell Itself Is Blocked

A capability that fails closed can leave a session unable to run the very
validation the finish-line gate is waiting on, and unable to set the waiver
environment variable because that also needs the blocked shell
(`sympoies/nils-cli#1409`). `scripts/validation-recovery.py` is the out-of-band
lane for that state. It is invoked by an operator or controller, never through a
provider hook, and exposes no general shell escape:

- `status --repo <path>` — the declared contract, what is outstanding for the
  current edit generation, and any recorded waiver.
- `run --repo <path> [--command <declared>]` — executes only a command shape the
  repository declared in `AGENT_DOCS.toml`; anything else is refused. A pass
  records the command outcome, so the gate is satisfied for real.
- `--session <id>` on any verb targets the marker namespace that session's
  hooks actually read. The gate namespaces validation state by the session
  identity, so a managed session needs this (or an ambient `AGENT_SESSION_ID`);
  without it the controller addresses the shared namespace an unidentified
  delivery reads. `status` reports which namespace it addressed.
- `waive --repo <path> --reason <text>` — records an
  `agent-runtime-validation.waiver.v1` record. The reason is required, and the
  record binds to the repository, contract, product, session, and the current
  edit generation, so it expires the moment another edit lands. Prefer it over
  `AGENT_RUNTIME_VALIDATION_WAIVER`, which stays true for every later Stop in the
  process and has leaked across turns.
- `revoke --repo <path>` — withdraws a waiver.

A structured waiver still takes the one-shot discovered-defect routing review
before the gate releases, exactly as the environment route does.
