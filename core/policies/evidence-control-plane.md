# Evidence Control Plane

## Purpose

Evidence is conditional. It exists to make a material engineering or workflow
claim durable and machine-verifiable, not to turn routine collaboration into a
recording exercise. The parent outcome decides whether a record is warranted;
the typed CLI owns schema, storage, and deterministic verification.

Create retained evidence when an explicit request, repository/delivery gate,
high-risk workflow, audit, cross-session handoff, deferred defect, or reusable
operational lesson needs it. Do not create evidence merely because a command
exists, a named skill ran, a session ended, or ordinary L0 work completed.

Records live in one workflow-owned `agent-out` directory unless the active
workflow declares another private artifact root. Never commit raw runtime
evidence, credentials, transcripts, provider objects, or local receipts.

## Ownership

| Need | Judgment owner | Deterministic owner |
| --- | --- | --- |
| Test-first proof | Implementation parent | `test-first-evidence` |
| Documentation disposition | Delivery parent when its gate requires one | `docs-impact` |
| Retained review findings | Review parent | `review-evidence` |
| Static HTTP claim | External-fact or browser parent | `web-evidence` |
| Requested second-model comparison | Requesting parent | `model-cross-check` |
| Workflow usage envelope | Outermost retained workflow | `skill-usage` |
| Archive migration | Outermost workflow with durable records | `evidence migrate` |

The parent judges relevance, semantic correctness, acceptable risk, and
residual gaps. The CLI may reject incomplete or stale records but cannot decide
whether a test proves the intended behavior, a waiver is honest, a finding is
material, or retention is useful.

## Test-First Paths

The engineering discipline applies whether or not a durable record is required:

1. **Declare the contract delta**: retained behavior, changed or removed
   behavior, added behavior, and invariants.
2. Identify materially affected tests, fixtures, snapshots, mocks, contract
   consumers, and journeys. Keep, update, remove, add, or refactor each owner
   according to the intended contract.
3. Choose the lowest stable behavioral boundary. **Capture meaningful red**
   before production edits when practical: the command or scenario, identity,
   expected failure, and observed failure must agree with the missing behavior.
   Setup, compilation, environment, unrelated, or retry-only failures do not
   qualify.
4. Implement narrowly and validate by risk across focused owners, affected
   suites, contract consumers, and integration/manual boundaries as needed.
   Coverage percentage is diagnostic, not an objective, and does not justify
   duplicate cases.
5. If meaningful red is not practical, state why and name substitute
   validation. Deferred test debt also needs a durable owner and expiry/removal
   condition.

A durable `test-first-evidence.record.v2` is required only when an active gate
or workflow says so. Initialize it before production edits, record affected
test decisions plus meaningful red or a complete waiver, append scoped final
validation, declare residual gaps, and run `verify`. Use
`test-first-evidence --help` for exact syntax; do not copy a second command
manual into prompt policy.

Repositories may declare `[path_classes]` so `test-first-evidence check` can
distinguish production, tests, docs, and generated paths. Unknown or overlapping
classes fail closed when that record gate is active. Without a configured gate,
path classification remains engineering judgment rather than invented
language-specific policy.

## Other Record Types

- `docs-impact`: use only when an active delivery workflow requires a current
  docs disposition. Record `docs-updated`, `no-docs-needed`, or `pending` after
  the complete diff exists; a later Git change makes it stale.
- `review-evidence`: retain findings or validation when another workflow,
  reviewer handoff, or audit will consume them. Ordinary inline review can
  report findings directly.
- `web-evidence`: proves a bounded static HTTP claim only. It does not prove
  rendered JavaScript, visual state, browser interaction, or desktop behavior.
- `model-cross-check`: records a comparison the parent explicitly requested.
  Provider calls happen outside the recorder.
- `skill-usage`: create at most one envelope for the outer retained outcome.
  Link verified child records instead of opening a usage record for every
  primitive.

Repeated attempts append history while the latest result for each identity
controls readiness. Serialize writes to a record directory and verify a child
before linking it.

## Closeout And Retention

Closeout is event-driven:

- If no durable record, deferred defect, tracker, plan, or archive duty exists,
  report the result and stop.
- If local evidence remains useful only for the current task, retain or clean it
  according to its owner; do not migrate it automatically.
- If evidence must survive the session, review the exact candidates, run the
  governed migration dry-run, apply only the approved set, then verify before
  any source prune.
- Route reusable runtime-kit workflow gaps to `heuristic-inbox`; route product,
  test, or CI defects to their repository owner. Creating provider state still
  requires the active tier and user authority.

- Never create a duplicate closeout-owned usage record.
- Retention excludes empty, transient, failed-setup, or unreviewed artifacts and
  any artifact containing sensitive values.

## Enforcement Boundary

- Codex and Claude hooks verify supported intent activation, checkout safety,
  and declared finish-line validation. They cannot safely discover an arbitrary
  evidence directory or judge semantic proof, so the parent invokes evidence
  checks only when required.
- `forge-cli` can require a complete v2 test-first record for feature/bug
  delivery when repository or user configuration explicitly enables that gate.
  The gate is otherwise off; see `git-delivery.md`.
- Hook timeout/effect posture remains owned by the hook rule. Evidence never
  converts an external, destructive, sensitive, transaction, or unknown effect
  into an allowed one.
- Hermes can run the same released record CLIs but has no runtime-kit
  `agent-docs` hook runner. Its record proves explicit CLI verification, not a
  product-native hook event.
