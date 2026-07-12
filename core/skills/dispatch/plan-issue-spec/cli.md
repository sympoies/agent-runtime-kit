# Plan Tracking Issue CLI Spec

## Status

- Status: implemented; canonical plan-issue CLI spec
- Date: 2026-05-26
- Depends on:
  - `core/skills/dispatch/plan-issue-spec/comment-taxonomy.md`
  - `core/skills/dispatch/plan-issue-spec/workflow.md`
  - `core/skills/dispatch/plan-issue-spec/run-state-controller.md`
  - `core/skills/dispatch/plan-issue-spec/skill-family.md`
- Owning implementation repos:
  - `sympoies/nils-cli`
  - `graysurf/agent-runtime-kit`

## Purpose

The plan-tracking issue workflow should become easier for agents to use and
harder for agents to format incorrectly. Prompt text alone is not enough. The
final behavior must be locked by `nils-cli` command contracts, renderer tests,
runtime-kit skill contracts, and deterministic smoke coverage.

This document defines the implementation split. The chosen architecture is
Option B: deterministic finite state machine plus typed local run state under
the `plan-issue` runtime workspace.

## Current Working Contract

The current foundation is correct:

- `plan-issue record` owns issue-backed lifecycle mutation.
- `plan-tooling` owns plan parsing and validation.
- `forge-cli` owns general PR and provider lifecycle outside the record.
- Runtime-kit skills own scope selection, implementation judgment, validation
  interpretation, and live read-back quality checks.

The current problem is UX and consistency:

- Agents still need to assemble several payload JSON files and Markdown
  summaries correctly.
- The skill body contains some workflow rules, but those rules are not yet a
  complete reusable template system.
- The CLI renderer has the core role model, but agent-facing commands do not
  yet guide "when should I post?" or "which template should I use?"
- Tests can prove hidden payload audit success without always proving that the
  visible issue timeline is useful to humans.
- Execution state is split across issue comments, local plan files, PR state,
  validation artifacts, and ad hoc agent memory. There is no typed local
  `run-state.json` that lets the CLI reconcile "what the agent just did" with
  "what the issue currently proves".

## Redesign Goals

1. Enumerate every lifecycle comment kind in one canonical taxonomy.
2. Make each role template deterministic and testable.
3. Move low-level formatting decisions into `nils-cli`.
4. Let skills call higher-level CLI surfaces instead of hand-assembling
   comments wherever practical.
5. Keep append-only lifecycle comments and dashboard repair as the record
   model.
6. Make visible comment completeness a first-class validation target.
7. Preserve compatibility with GitHub and GitLab provider paths.
8. Add a typed local execution-run state that lets the CLI recommend and apply
   safe lifecycle checkpoints.
9. Keep provider issue comments as durable truth when local run state and issue
   evidence disagree.

## Non-Goals

- Do not replace `plan-tooling` plan validation.
- Do not make issue dashboards the durable state source.
- Do not parse human prose as closeout truth.
- Do not bulk-rewrite historical issues.
- Do not make agents post comments for every local edit.
- Do not route plan-record lifecycle writes through raw `gh`, `glab`, or
  `forge-cli issue comment`.
- Do not embed a LangGraph-style dynamic orchestration runtime in `nils-cli`
  core. External agent runners may use graph orchestration, but `nils-cli`
  should expose deterministic primitives.
- Do not delete the whole `crates/plan-issue` crate, rename the binaries,
  or break released command compatibility before runtime-kit has migrated.

## Chosen Architecture

The CLI should own a deterministic controller:

1. Resolve the issue runtime root from `--state-dir`, `PLAN_ISSUE_HOME`, or the
   XDG default.
2. Read issue evidence through live provider, fixture mode, or explicit
   body/comment files.
3. Read the plan bundle and canonical execution-state Markdown.
4. Read or initialize local `runs/<run-id>/run-state.json`.
5. Evaluate the finite state machine.
6. Reconcile provider truth with local run state.
7. Return safe transitions and a recommended next action.
8. Apply explicit checkpoint commands through the existing lifecycle renderer
   and `record post`/dashboard repair primitives.

The durable truth remains the provider issue lifecycle comments. Local run
state is a resumable execution cache and checkpoint input. It must never
silently override newer issue evidence.

## Complete Rewrite Boundary

The `nils-cli` implementation should be a complete rewrite of the plan issue
workflow core inside the existing `plan-issue` crate. It should not be a
total crate deletion.

Definition:

- Keep the public shell: `plan-issue`, `plan-issue-local`, global flags,
  output envelope, exit-code conventions, provider routing, state-dir
  resolution, and existing fixture assets.
- Build a clean vNext core for lifecycle templates, visible completeness,
  run-state reconciliation, FSM decisions, checkpoint rendering, and close
  readiness.
- Add new agent-facing surfaces on the vNext core first.
- Migrate old `record` internals to the vNext registry/controller only after
  the new surfaces have deterministic fixture coverage.

Preserve:

| Existing surface | Reason |
| --- | --- |
| `plan-issue` and `plan-issue-local` binaries | Runtime-kit, Homebrew release, and shell completions already depend on the binary names. |
| Global output envelope and exit-code model | Downstream automation parses command results and errors. |
| Provider abstraction | GitHub/GitLab parity has already been paid for and must remain a regression harness. |
| Runtime layout resolution | The controller should extend the existing state-dir contract instead of inventing a second root. |
| Existing fixtures and integration tests | They become regression tests around the compatibility shell. |
| Released `record` commands during migration | Runtime-kit can migrate only after a released CLI floor exists. |

Rewrite:

| Core area | Target shape |
| --- | --- |
| Lifecycle role templates | Registry-driven templates with visible completeness metadata. |
| Lifecycle rendering | Generated from typed role data and registry rules, not ad hoc Markdown assembly. |
| Audit completeness | Machine payload audit plus human-visible section lint. |
| Tracking controller | FSM plus typed `run-state.json` and append-only `events.jsonl`. |
| Checkpoint posting | Macro over lifecycle primitives with dry-run render output. |
| Close readiness | Non-mutating probe using the same gates as `record close`. |

Recommended module boundary in `nils-cli`:

```text
crates/plan-issue/src/
  lifecycle_vnext/
    mod.rs
    registry.rs
    templates.rs
    visible_lint.rs
    payloads.rs
    render.rs
  tracking/
    mod.rs
    run_state.rs
    events.rs
    fsm.rs
    reconcile.rs
    checkpoint.rs
    close_ready.rs
```

The exact filenames may change during implementation, but the boundary should
remain: new core modules first, compatibility commands as adapters second. Do
not keep expanding a large catch-all executor with new lifecycle behavior.

## nils-cli Workstreams

### Workstream 0: vNext Core Boundary

Create the clean vNext implementation boundary before adding public behavior.

Expected behavior:

- Introduce modules for lifecycle registry/rendering and tracking controller
  behavior.
- Keep old commands compiling while new modules are built and tested.
- Add fixture tests against the new modules before wiring live provider
  mutation.
- Keep provider adapters and runtime layout as shared infrastructure.
- Do not make new `tracking` commands depend on old ad hoc renderer behavior.

Acceptance:

- `cargo test -p nils-plan-issue` can run with both old command paths and
  new vNext module tests present.
- New module tests assert visible template shape without invoking live provider
  commands.
- No runtime-kit skill needs an unreleased local binary until the focused
  skill rewrite phase.

### Workstream 1: Template Registry

Add a small template registry inside `plan-issue` for lifecycle roles.

Expected behavior:

- One registry entry per role:
  - `source`
  - `plan`
  - `state`
  - `session`
  - `validation`
  - `review`
  - `closeout`
- Each entry defines:
  - marker role
  - default heading
  - required visible sections
  - payload schema type
  - whether direct `record post` is allowed
  - whether dashboard repair is expected afterward
  - closeout requirement

Acceptance:

- Renderer tests can iterate over the registry and assert every role has a
  visible template and a payload schema.
- `source` and `plan` are marked open/attach-only.
- `closeout` is marked `record close` owned.

### Workstream 2: Visible Completeness Lint

Add a reusable visible-completeness check for rendered comments.

Expected behavior:

- Reject Profile-only bodies for every lifecycle role.
- For `state`, require visible `## Task Ledger`.
- For final `state`, require expanded Task Ledger.
- For non-final `state`, allow collapsed Task Ledger but keep the heading
  visible.
- For `validation`, require overall status and command rows or an explicit
  waiver.
- For `review`, require decision and finding disposition rows when findings
  exist.
- For `session`, require a non-empty summary.
- For `closeout`, require final status, approval, and linked PR evidence or an
  explicit no-PR note.

Potential CLI surface:

```bash
plan-issue record audit \
  --profile tracking \
  --body-file "$ISSUE_BODY" \
  --comments-json "$ISSUE_JSON" \
  --expect-visible
```

Acceptance:

- Existing audit behavior remains available without `--expect-visible`.
- `--expect-visible` returns stable error codes for each missing visible
  section.
- Runtime-kit closeout skills can use it before claiming final success.

### Workstream 3: Template Preview

Add a non-mutating template preview command so agents can inspect the expected
shape without remembering Markdown.

Potential CLI surface:

```bash
plan-issue record template \
  --profile tracking \
  --kind validation \
  --format markdown

plan-issue record template \
  --profile tracking \
  --kind validation \
  --format json
```

Expected behavior:

- `--format markdown` prints the visible template skeleton.
- `--format json` prints the payload data skeleton.
- The command does not include a real hidden payload carrier because it is a
  template, not a lifecycle record.

Acceptance:

- Templates are generated from the same registry used by renderers.
- Docs and skill examples can be derived from or checked against the CLI
  template output.

### Workstream 4: Run-State Controller

Add the controller specified in
`core/skills/dispatch/plan-issue-spec/run-state-controller.md`.

Expected behavior:

- Store typed local run state under:
  `<state-dir>/out/plan-issue-delivery/<repo-slug>/issue-<n>/runs/<run-id>/`.
- Maintain `run-state.json` plus append-only `events.jsonl`.
- Read provider issue evidence and plan bundle files before recommending or
  applying transitions.
- Treat provider issue comments as durable truth and local run state as
  secondary.
- Emit stable JSON envelopes with:
  - current FSM state
  - latest lifecycle evidence
  - local run state summary
  - reconciliation warnings
  - safe transitions
  - recommended next action

Potential CLI surface:

```bash
plan-issue tracking run init \
  --repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --bundle "$PLAN_BUNDLE" \
  --task 1.2 \
  --branch "$BRANCH" \
  --format json

plan-issue tracking status \
  --repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --run-state "$RUN_STATE" \
  --expect-visible \
  --format json

plan-issue tracking run update \
  --run-state "$RUN_STATE" \
  --phase validating \
  --validation-command "cargo test -p nils-plan-issue lifecycle_record" \
  --validation-status pass \
  --validation-evidence "$VALIDATION_LOG" \
  --format json
```

Acceptance:

- `tracking status` can report current FSM state without provider mutation.
- Stale local run state does not overwrite newer issue evidence.
- `events.jsonl` records run start, updates, reconciliation, and checkpoint
  outcomes.
- Runtime-kit skills can resume from `run-state.json` instead of rebuilding
  every payload manually.

### Workstream 5: Tracking Checkpoint Macro

Add an agent-friendly macro that posts common checkpoint bundles without making
agents assemble every JSON file manually.

Potential CLI surface:

```bash
plan-issue tracking checkpoint \
  --repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --run-state "$RUN_STATE" \
  --post state,session,validation \
  --repair-dashboard \
  --dry-run
```

Expected behavior:

- Reads the plan bundle and execution-state file named by run state.
- Updates or synthesizes role payloads from typed run state plus explicit
  command overrides.
- Posts `state` with the canonical execution-state file.
- Optionally posts `session`.
- Optionally posts `validation`.
- Repairs the dashboard when requested.
- Emits a JSON envelope listing every planned or completed lifecycle write.

Design constraints:

- The macro must be an adapter over `record post`, not a second lifecycle
  engine.
- It must expose dry-run output with rendered comment bodies.
- It must avoid posting empty session or validation comments.
- It must leave source/plan snapshots to `record open` or `record attach`.
- It must never call `record close`.
- It must reconcile local run state against issue evidence before live posting.

Acceptance:

- A common tracking-outcome progress update can be expressed as one macro call.
- The macro refuses to post if the generated visible bodies fail the visible
  completeness lint.
- The macro refuses to post when issue evidence is newer than run state unless a
  sync/repair path has reconciled the difference.
- Runtime-kit can still call lower-level `record post` when custom control is
  needed.

### Workstream 6: Closeout Readiness Probe

Add a closeout readiness probe that audits without mutating.

Potential CLI surface:

```bash
plan-issue tracking close-ready \
  --repo "$OWNER_REPO" \
  --issue "$ISSUE" \
  --run-state "$RUN_STATE" \
  --linked-pr "$OWNER_REPO#$PR_NUMBER" \
  --approval "$APPROVAL" \
  --expect-visible \
  --format json
```

Expected behavior:

- Runs the same strict gate as `record close`.
- Verifies visible completeness when requested.
- Reconciles linked PRs from issue state, run state, and explicit flags.
- Does not post closeout, repair dashboard, or close the issue.
- Returns exact blocked codes and suggested unblock actions.

Acceptance:

- Parent outcomes can run close readiness before merge, final state, or approval
  handoff.
- `record close` remains the only command that posts closeout and closes the
  issue.

## runtime-kit Outcome Contract

The two active plan outcomes are defined in
`core/skills/dispatch/plan-issue-spec/skill-family.md`. Each parent owns the
complete lifecycle and routes open/resume, implementation, review, PR, and
closeout as internal phases.

Acceptance:

- Outcome bodies remain concise.
- Each parent names the exact lifecycle roles its internal phases may write.
- Every state example uses `--execution-state-file`.
- Parent outcomes initialize or resume `run-state.json` before posting
  progress checkpoints.
- Neither outcome suggests raw closeout comments.
- Codex, Claude, and Hermes targets plus goldens are regenerated after source
  changes.

### Workstream 2: Deterministic Smoke Coverage

Runtime smoke should assert user-visible bodies, not only hidden payload audit.

Required assertions:

- Source and plan comments have snapshot metadata and collapsed document
  details.
- State comments contain `## Execution State` and `## Task Ledger`.
- Intermediate state comments collapse Task Ledger rows.
- Final state comments expand Task Ledger rows.
- Session comments contain `## Execution Session` and a non-empty summary.
- Validation comments contain `## Validation Evidence`, overall status, and
  command rows.
- Review comments contain `## Review Evidence` and decision.
- Closeout comments contain `## Tracking Issue Closeout`, approval, linked PR,
  merge SHA, and check status evidence.
- No lifecycle comment is Profile-only.
- Stale run state cannot overwrite newer issue lifecycle evidence.
- `tracking checkpoint --dry-run` emits rendered comment bodies and planned
  dashboard repair without provider mutation.

Acceptance:

- Fixture mode can run without live provider mutation.
- Failing visible completeness fails the smoke test.
- Hidden payload parsing remains covered.

### Workstream 3: Surface And Floor Management

When `nils-cli` adds the new surfaces, runtime-kit must consume them only after
the released floor is available.

Expected changes:

- Update `docs/source/nils-cli-surface.md` with the release version and command
  surface.
- Update `required_clis` floors when needed.
- Render Codex and Claude skill output.
- Refresh goldens.
- Run focused smoke and then the full repo gate.

Acceptance:

- Runtime-kit does not require an unreleased local debug binary for final
  validation.
- Skills and goldens agree with the released CLI help.

## Implementation Sequence

1. Land these design documents in runtime-kit.
2. In `nils-cli`, create the vNext module boundary inside
   `crates/plan-issue` while preserving binaries, global envelope,
   provider abstraction, runtime layout, and old command compatibility.
3. Implement the lifecycle template registry and visible completeness lint in
   the vNext core.
4. Add `record template` preview backed by the vNext registry.
5. Add run-state schema, parser, event journal, and runtime-layout helpers.
6. Add `tracking run init`, `tracking run update`, and `tracking status` on
   the vNext controller.
7. Add `tracking checkpoint --dry-run`, then live checkpoint posting.
8. Add `tracking close-ready`.
9. Migrate `record open/post/audit/close` internals toward the vNext
   registry/controller without changing their public command contract unless
   the release notes and runtime-kit floor update say so.
10. Build a local `nils-cli` binary from the implementation branch.
11. Validate the local binary output against these design documents.
12. Rewrite runtime-kit plan issue skill sources from
    `core/skills/dispatch/plan-issue-spec/skill-family.md`.
13. Add runtime smoke assertions for visible comments and stale run-state
    reconciliation.
14. Render products and refresh goldens using the local binary for focused
    smoke.
15. Release `nils-cli`.
16. Update runtime-kit required CLI floors and docs to consume the released
    binary.
17. Run the final repo gate against the released CLI floor.

## Open Design Questions

1. Should `tracking checkpoint` update the execution-state Markdown file, or
   should it only read it and require the agent to update the file first?

   Recommendation: require the agent to update the file first in v1. Let the
   macro synthesize payload from explicit flags plus the file, but do not edit
   the file until there is a stronger Markdown writer contract.

2. Should `record template` be part of `plan-issue record` or a separate
   `plan-issue template` namespace?

   Recommendation: keep it under `record` because templates are tied to the
   record lifecycle roles.

3. Should visible-completeness lint be mandatory in default `record audit`?

   Recommendation: make it opt-in first with `--expect-visible`, then promote
   to default after runtime-kit and nils-cli fixtures prove compatibility.

4. Should `review` be mandatory for all lightweight tracking closeouts?

   Recommendation: keep the closeout gate strict for workflows that require
   review evidence, but let policy decide when a small docs-only issue may use
   `comments-only` review evidence instead of specialist review.

5. Should run state live under `plan-issue` state-dir or `agent-out`?

   Recommendation: use `plan-issue` state-dir for controller-owned
   `run-state.json` and `events.jsonl`; link to `agent-out` for larger retained
   validation or review artifacts.

## Contract Boundaries

| Owner | Owns | Must not own |
| --- | --- | --- |
| `plan-tooling` | Plan parsing, plan validation, task decomposition validity. | Provider issue comments or dashboards. |
| `plan-issue record` | Lifecycle comments, templates, payload schema, audit, dashboard repair, closeout gates. | Code implementation, PR creation, review judgment. |
| `plan-issue tracking` | Run-state controller, FSM status, reconciliation, checkpoint macros, close readiness probes. | Provider mutation outside lifecycle comments, code implementation, merge decisions. |
| `forge-cli` | PR creation, PR delivery, provider label/PR operations outside the plan record. | Plan-record lifecycle comment composition. |
| Runtime-kit skills | Agent workflow, scope selection, when to post, validation interpretation, read-back quality. | Low-level comment rendering and payload schema drift. |
| Tests | Visible body assertions, hidden payload assertions, fixture parity. | Live provider-only assumptions without deterministic coverage. |

## Acceptance For This Redesign

The redesign is ready for implementation when:

- The taxonomy document lists every comment type and role template.
- The workflow document explains every state transition and when comments are
  written.
- The run-state controller document defines local state schema, event journal,
  reconciliation rules, and checkpoint commands.
- The CLI redesign document identifies the nils-cli workstreams needed to make
  the templates enforceable.
- The CLI redesign document defines "complete rewrite" as a vNext core rewrite
  inside the existing crate, not deletion of the whole CLI surface.
- The skill family redesign document assigns every plan issue skill a function,
  boundary, rewrite rule, and CLI-first implementation order.
- No runtime-kit skill needs to invent a new lifecycle comment shape not listed
  in the taxonomy.
